import json
import logging

from aiohttp import BasicAuth, ClientSession
from django.conf import settings

logger = logging.getLogger(__name__)


class Radarr:
    base_url = settings.RADARR_API_URL

    @classmethod
    async def get_movie(cls, *, tmdb_id: str, session: ClientSession):
        endpoint = f"{cls.base_url}/movie"
        params = {"apiKey": settings.RADARR_API_KEY, "tmdbId": tmdb_id}
        auth = BasicAuth(settings.SEEDBOX_UN, settings.SEEDBOX_PW)

        async with session.get(endpoint, auth=auth, params=params) as response:
            if not response.ok:
                text = await response.text()
                logger.exception(f"status: {response.status}")
                logger.exception(text)
                raise Exception(f"status: {response.status} {text}")

            data = await response.json()

            if len(data) > 0:
                return data[0]

            return data

    @classmethod
    async def create_movie(cls, data: dict, session: ClientSession) -> dict:
        """
        Creates a Movie in Radarr.
        `addOptions.searchForMovie` must be True so Radarr will immediately search for the torrent file.
        """
        endpoint = f"{cls.base_url}/movie"
        headers = {"content-type": "application/json"}
        body = {
            "monitored": True,
            "minimumAvailability": "announced",
            "addOptions": {
                "monitor": "movieOnly",
                "searchForMovie": True,
                "addMethod": "manual",
            },
            "qualityProfileId": settings.RADARR_QUALITY_PROFILE_ID,
            "rootFolderPath": settings.RADARR_ROOT_FOLDER_PATH,
            "tmdbid": data["tmdb_id"],
            "title": data["title"],
            "titleslug": data["title_slug"],
            "images": [
                {
                    "coverType": "poster",
                    "url": data["full_poster_path"],
                }
            ],
        }
        params = {"apiKey": settings.RADARR_API_KEY}
        auth = BasicAuth(settings.SEEDBOX_UN, settings.SEEDBOX_PW)

        async with session.post(
            endpoint,
            # FIXME - this auth is specific to a singular seedbox.
            #  how to make this configurable? plugin system? webhook?
            auth=auth,
            params=params,
            data=json.dumps(body),
            headers=headers,
        ) as response:
            if not response.ok:
                text = await response.text()
                raise Exception(f"status: {response.status} {text}")

            data = await response.json()
            return data
