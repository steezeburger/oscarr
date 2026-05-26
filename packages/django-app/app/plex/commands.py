import asyncio
import logging

import networkx as nx
from aiohttp import ClientSession
from asgiref.sync import sync_to_async
from common.commands.abstract_base_command import AbstractBaseCommand
from services.plex import Plex
from services.tmdb import TMDB

from plex.forms import EnrichMovieActorsForm
from plex.repositories import CachedGraphRepository, PlexMovieRepository

logger = logging.getLogger(__name__)


class SyncWithPlexCommand(AbstractBaseCommand):
    """
    Sync Oscarr's database with the movies on the Plex.
    Stops syncing when we get to a movie that was added
    before the latest movie in the database.

    Unfortunately the Plex API doesn't allow us to filter
    by addedAt, so we have to get a page of movies.
    """

    def execute(self) -> None:
        super().execute()

        latest_movie = PlexMovieRepository.get_latest()
        synced_count = 0

        for movie in Plex.fetch_movies(sort="addedAt:desc", container_start=0, container_size=5):
            added_at = Plex.normalize_added_at(movie.addedAt)
            if latest_movie and added_at <= latest_movie.created_at:
                # break out of loop if we start to get a movie
                # added before the latest movie in the database
                break

            try:
                movie_details = Plex.extract_movie_details(movie)
                plex_movie = PlexMovieRepository.get_or_create(movie_details)

                plex_movie.created_at = added_at

                # Enrich actors with TMDB data
                try:
                    form = EnrichMovieActorsForm({"movie": plex_movie.id, "max_actors": 30})
                    if form.is_valid():
                        command = EnrichMovieActorsCommand(form)
                        asyncio.run(command.execute())
                    else:
                        logger.warning(
                            f"Invalid form for enriching {plex_movie.title}: {form.errors}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to enrich actors for {plex_movie.title}: {e}")
                    plex_movie.save()
                else:
                    # Only save if enrichment didn't happen (it saves itself via repository)
                    if not plex_movie.actors_enriched_at:
                        plex_movie.save()

                print(f"Created PlexMovie: {plex_movie}")
                synced_count += 1
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)

        # Rebuild actor graph cache after syncing
        if synced_count > 0:
            logger.info(f"Synced {synced_count} movies, rebuilding actor graph cache...")
            try:
                command = BuildActorGraphCommand()
                graph = asyncio.run(command.execute())
                CachedGraphRepository.save_actor_graph(graph)
                logger.info("Actor graph cache rebuilt successfully")
            except Exception as e:
                logger.exception(f"Failed to rebuild actor graph cache: {e}")


class EnrichMovieActorsCommand(AbstractBaseCommand):
    """
    Command to enrich a movie's actor list with data from TMDB.
    """

    def __init__(self, form: EnrichMovieActorsForm):
        self.form = form

    async def execute(self):
        """
        Execute the enrichment asynchronously.
        Updates the movie instance with enriched actors and TMDB ID.
        """
        super().execute()

        movie = self.form.cleaned_data["movie"]
        max_actors = self.form.cleaned_data["max_actors"]

        async with ClientSession() as session:
            plex_actors = list(movie.actors) if movie.actors else []
            tmdb_id = movie.tmdb_id

            # If we don't have a TMDB ID, search by title and year
            if not tmdb_id:
                logger.info(f"Searching TMDB for {movie.title} ({movie.year})...")
                tmdb_id = await TMDB.find_movie_id(
                    str(movie.title),
                    movie.year,
                    session,  # type: ignore[arg-type]
                )
                if not tmdb_id:
                    logger.warning(f"Could not find TMDB ID for {movie.title}")
                    return

            # Fetch credits from TMDB
            try:
                credits = await TMDB.get_movie_credits(tmdb_id, session)
                tmdb_actors = [actor["name"] for actor in credits.get("cast", [])]

                # Merge actors: Plex actors first, then TMDB actors not in the list
                enriched_actors = plex_actors.copy()
                plex_actors_lower = {actor.lower() for actor in enriched_actors}

                for tmdb_actor in tmdb_actors:
                    if tmdb_actor.lower() not in plex_actors_lower:
                        enriched_actors.append(tmdb_actor)

                # Limit to max_actors
                enriched_actors = enriched_actors[:max_actors]

                # Update the movie via repository
                await PlexMovieRepository.update_movie_actors_async(
                    movie=movie, actors=enriched_actors, tmdb_id=tmdb_id
                )

                logger.info(
                    f"Enriched {movie.title}: {len(plex_actors)} Plex + "
                    f"{len(tmdb_actors)} TMDB = {len(enriched_actors)} total"
                )

            except Exception as e:
                logger.exception(f"Error enriching actors for {movie.title}: {e}")
                raise


class BuildActorGraphCommand(AbstractBaseCommand):
    """
    Command to build a NetworkX graph of all movies and their associated people.
    Includes actors, directors, producers, and writers.
    """

    async def execute(self) -> nx.Graph:
        """
        Build and return a NetworkX graph of movie-person relationships.

        Returns:
            nx.Graph: Complete graph of all movie-person relationships
        """
        super().execute()

        logger.info("Building actor graph from database...")

        movies = await sync_to_async(list)(PlexMovieRepository.model.objects.all().values())

        graph = nx.Graph()
        added_people = set()

        for movie_dict in movies:
            # Add movie node
            year = movie_dict.get("year")
            year = int(year) if year and year > 0 else None
            year_string = f" ({year})" if year else ""
            movie_title = f"{movie_dict['title']}{year_string}"
            graph.add_node(movie_title, type="movie")

            # Add all people (actors, directors, producers, writers)
            for person_type in ["actors", "directors", "producers", "writers"]:
                people = movie_dict.get(person_type) or []
                for person in people:
                    person_lower = person.lower()
                    if person_lower not in added_people:
                        graph.add_node(person_lower, type="person")
                        added_people.add(person_lower)
                    graph.add_edge(movie_title, person_lower)

        logger.info(
            f"Built graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges"
        )

        return graph


class GetActorGraphCommand(AbstractBaseCommand):
    """
    Command to get the actor graph, either from cache or by building it.
    """

    async def execute(self) -> nx.Graph:
        """
        Get the actor graph from cache, or build and cache it if not available.

        Returns:
            nx.Graph: Complete graph of all movie-person relationships
        """
        super().execute()

        # Try to load from cache
        graph = await CachedGraphRepository.load_actor_graph_async()

        if graph is None:
            logger.info("Actor graph not in cache, building...")
            # Build graph if not cached
            command = BuildActorGraphCommand()
            graph = await command.execute()
            # Cache it for next time
            await sync_to_async(CachedGraphRepository.save_actor_graph)(graph)
            logger.info("Actor graph cached successfully")
        else:
            logger.info("Loaded actor graph from cache")

        return graph
