import requests
import tmdbsimple as tmdb
from django.conf import settings

tmdb.API_KEY = settings.TMDB_TOKEN_V3
tmdb.REQUESTS_SESSION = requests.Session()


class TMDB:
    poster_base_url = 'https://image.tmdb.org/t/p/w600_and_h900_bestv2'

    @classmethod
    def get_movie_by_id(cls, tmdb_id: int):
        movie = tmdb.Movies(tmdb_id)
        response = movie.info()
        return response

    @classmethod
    def search_by_title(cls, title: str):
        search = tmdb.Search()
        response = search.movie(query=title)
        print(response)
        return response

    @classmethod
    def search_by_title_and_year(cls, title: str, year: int):
        """Search for a movie by title and year, returning the best match."""
        search = tmdb.Search()
        response = search.movie(query=title, year=year)
        results = response.get('results', [])
        if results:
            return results[0]
        return None

    @classmethod
    def get_movie_credits(cls, tmdb_id: int, cast_limit: int = 20):
        """
        Fetch movie credits (cast) from TMDB.
        Returns a list of actor names, limited to cast_limit.
        """
        movie = tmdb.Movies(tmdb_id)
        credits = movie.credits()
        cast = credits.get('cast', [])
        actor_names = [actor['name'] for actor in cast[:cast_limit]]
        return actor_names

    @classmethod
    def get_poster_full_path(cls, poster_path) -> str:
        return f'{cls.poster_base_url}{poster_path}'
