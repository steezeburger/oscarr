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
        
    @classmethod
    def create_user(cls, username: str, email: str = None, password: str = None) -> dict:
        """
        Creates a user in Ombi and returns the created user data including the user ID.
        
        Args:
            username: The username for the new Ombi user
            email: Optional email for the user
            password: Optional password for the user
        
        Returns:
            dict: The created user data containing the Ombi user ID
        """
        endpoint = f'{cls.base_url}/Identity'
        logger.info(f"Ombi create user endpoint: {endpoint}")
        headers = {
            'content-type': 'application/json',
            'ApiKey': settings.OMBI_API_KEY,
        }
        
        # Create user data
        user_data = {
            "userName": username,
            "userType": 1,
            "movieRequestLimit": 0,
            "episodeRequestLimit": 0,
            "musicRequestLimit": 0,
            "streamingCountry": "us",
            "movieRequestLimitType": 0,
            "musicRequestLimitType": 0,
            "episodeRequestLimitType": 0,
            "hasLoggedIn": False,
            "source": "local"
        }
        
        # Add optional fields if provided
        if email:
            user_data["emailAddress"] = email
        if password:
            user_data["password"] = password
        
        logger.info(f"Creating Ombi user: {username}")
        logger.info(f"Request data: {json.dumps(user_data, indent=2)}")
        logger.info(f"Request headers: {headers}")
        
        res = requests.post(
            endpoint,
            auth=HTTPBasicAuth(settings.SEEDBOX_UN, settings.SEEDBOX_PW),
            data=json.dumps(user_data),
            headers=headers)
            
        if not res.ok:
            logger.error(f"Failed to create Ombi user: {res.status_code} - {res.text}")
            raise Exception(f"Failed to create Ombi user: {res.status_code} - {res.text}")
            
        data = res.json()
        logger.info(f"Successfully created Ombi user: {data}")
        return data
