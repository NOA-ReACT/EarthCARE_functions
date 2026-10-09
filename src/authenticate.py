
"""ESA MAAP authentication utilities."""

import os
from pathlib import Path
import fsspec
import requests


TOKEN_URL = ("https://iam.maap.eo.esa.int/realms/esa-maap/protocol/openid-connect/token")
CLIENT_ID="offline-token"
CLIENT_SECRET="p1eL7uonXs6MDxtGbgKdPVRAmnGxHpVE"


def get_access_token(
    credentials_path="credentials.txt",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    url=TOKEN_URL,
):
    if Path(credentials_path).exists():
        with open(credentials_path,"rt") as f:
            OFFLINE_TOKEN = f.read().strip().replace("\n","")
            url = url
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": OFFLINE_TOKEN,
                "scope": "offline_access openid"
            }

            response = requests.post(url, data=data)
            response.raise_for_status()

            response_json = response.json()
            access_token = response_json.get('access_token')
            print("Access token retrieved successfully.")

            if not access_token:
                raise RuntimeError("Failed to retrieve access token from IAM response")
    return access_token


def get_filesystem(access_token):

    fs = fsspec.filesystem(
        "https",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        cache_type="blockcache",
        block_size=8 * 1024 * 1024,
    )

    return fs
