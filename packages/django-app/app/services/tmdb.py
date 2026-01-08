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
    def get_movie_cast(cls, tmdb_id: int) -> list:
        """
        Fetch cast list from TMDB for a given movie ID.
        Returns a list of actor names.
        """
        try:
            movie = tmdb.Movies(tmdb_id)
            response = movie.info(append_to_response='credits')
            
            cast = response.get('credits', {}).get('cast', [])
            actor_names = [actor['name'] for actor in cast]
            return actor_names
        except Exception as e:
            # If TMDB call fails, return empty list (graceful fallback)
            return []

    @classmethod
    def search_by_title(cls, title: str):
        search = tmdb.Search()
        response = search.movie(query=title)
        print(response)
        return response

    @classmethod
    def get_poster_full_path(cls, poster_path) -> str:
        return f'{cls.poster_base_url}{poster_path}'
