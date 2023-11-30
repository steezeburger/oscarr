import json
import logging

import requests
import tmdbsimple as tmdb
from django.conf import settings
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

tmdb.API_KEY = settings.TMDB_TOKEN_V3
tmdb.REQUESTS_SESSION = requests.Session()


class Ombi:
    base_url = settings.OMBI_API_URL

    @classmethod
    def create_request(cls, data: dict) -> dict:
        """
        Creates a request in Ombi.
        `addOptions.searchForMovie` must be True so Radarr will immediately search for the torrent file.
        """
        endpoint = f'{cls.base_url}/Request/movie'
        headers = {
            'content-type': 'application/json',
            'ApiKey': settings.OMBI_API_KEY,
        }

        res = requests.post(
            endpoint,
            # FIXME - this auth is specific to a singular seedbox.
            #  how to make this configurable? plugin system? webhook?
            auth=HTTPBasicAuth(settings.SEEDBOX_UN, settings.SEEDBOX_PW),
            params={'apiKey': settings.RADARR_API_KEY},
            data=json.dumps(data),
            headers=headers)

        if not res.ok:
            print(f'status: {res.status_code}')
            print(res.text)
            raise Exception(f'status: {res.status_code} '
                            f'{res.text}')

        data = res.json()
        return data
