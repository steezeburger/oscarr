from aiohttp import ClientSession
from django.conf import settings


class TMDB:
    base_url = "https://api.themoviedb.org/3"
    poster_base_url = "https://image.tmdb.org/t/p/w600_and_h900_bestv2"

    @classmethod
    async def get_movie_by_id(cls, tmdb_id: int, session: ClientSession):
        endpoint = f"{cls.base_url}/movie/{tmdb_id}"
        params = {"api_key": settings.TMDB_TOKEN_V3}

        async with session.get(endpoint, params=params) as response:
            if not response.ok:
                text = await response.text()
                raise Exception(f"TMDB API error: {response.status} {text}")

            return await response.json()

    @classmethod
    async def search_by_title(cls, title: str, session: ClientSession, year: int | None = None):
        endpoint = f"{cls.base_url}/search/movie"
        params = {"api_key": settings.TMDB_TOKEN_V3, "query": title}

        if year:
            params["year"] = year

        async with session.get(endpoint, params=params) as response:
            if not response.ok:
                text = await response.text()
                raise Exception(f"TMDB API error: {response.status} {text}")

            data = await response.json()
            print(data)
            return data

    @classmethod
    async def find_movie_id_by_title_and_year(
        cls, title: str, year: int | None, session: ClientSession
    ) -> int | None:
        """
        Search for a movie by title and year, and return the TMDB ID of the best match.

        Args:
            title: Movie title
            year: Release year (optional)
            session: aiohttp ClientSession

        Returns:
            TMDB ID of the best match, or None if no match found
        """
        try:
            results = await cls.search_by_title(title, session, year)
            if results and results.get("results"):
                # Return the first result (best match)
                return results["results"][0].get("id")
        except Exception as e:
            print(f"Error searching TMDB for {title} ({year}): {e}")
        return None

    @classmethod
    async def get_movie_credits(cls, tmdb_id: int, session: ClientSession):
        """
        Get the cast and crew for a movie.

        Args:
            tmdb_id: TMDB movie ID
            session: aiohttp ClientSession

        Returns:
            Dictionary containing cast and crew information
        """
        endpoint = f"{cls.base_url}/movie/{tmdb_id}/credits"
        params = {"api_key": settings.TMDB_TOKEN_V3}

        async with session.get(endpoint, params=params) as response:
            if not response.ok:
                text = await response.text()
                raise Exception(f"TMDB API error: {response.status} {text}")

            return await response.json()

    @classmethod
    def get_poster_full_path(cls, poster_path) -> str:
        return f"{cls.poster_base_url}{poster_path}"
