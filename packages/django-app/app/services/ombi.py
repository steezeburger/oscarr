import json
import logging

from aiohttp import BasicAuth, ClientSession
from django.conf import settings

logger = logging.getLogger(__name__)


class Ombi:
    base_url = settings.OMBI_API_URL

    @classmethod
    async def create_request(cls, data: dict, session: ClientSession) -> dict:
        """
        Creates a request in Ombi.
        `addOptions.searchForMovie` must be True so Radarr will immediately search for the torrent file.
        """
        endpoint = f'{cls.base_url}/Request/movie'
        headers = {
            'content-type': 'application/json',
            'ApiKey': settings.OMBI_API_KEY,
        }
        params = {'apiKey': settings.RADARR_API_KEY}
        auth = BasicAuth(settings.SEEDBOX_UN, settings.SEEDBOX_PW)

        async with session.post(
            endpoint,
            # FIXME - this auth is specific to a singular seedbox.
            #  how to make this configurable? plugin system? webhook?
            auth=auth,
            params=params,
            data=json.dumps(data),
            headers=headers
        ) as response:
            if not response.ok:
                text = await response.text()
                logger.error(f'status: {response.status}')
                logger.error(text)
                raise Exception(f'status: {response.status} {text}')

            data = await response.json()
            return data
