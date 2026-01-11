from aiohttp import ClientSession
from django.conf import settings


class TMDB:
    base_url = 'https://api.themoviedb.org/3'
    poster_base_url = 'https://image.tmdb.org/t/p/w600_and_h900_bestv2'

    @classmethod
    async def get_movie_by_id(cls, tmdb_id: int, session: ClientSession):
        endpoint = f'{cls.base_url}/movie/{tmdb_id}'
        params = {'api_key': settings.TMDB_TOKEN_V3}

        async with session.get(endpoint, params=params) as response:
            if not response.ok:
                text = await response.text()
                raise Exception(f'TMDB API error: {response.status} {text}')

            return await response.json()

    @classmethod
    async def search_by_title(cls, title: str, session: ClientSession):
        endpoint = f'{cls.base_url}/search/movie'
        params = {
            'api_key': settings.TMDB_TOKEN_V3,
            'query': title
        }

        async with session.get(endpoint, params=params) as response:
            if not response.ok:
                text = await response.text()
                raise Exception(f'TMDB API error: {response.status} {text}')

            data = await response.json()
            print(data)
            return data

    @classmethod
    def get_poster_full_path(cls, poster_path) -> str:
        return f'{cls.poster_base_url}{poster_path}'
