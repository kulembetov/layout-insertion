import requests

from typing import Any, Optional
from api_v1.services.filter_service import FilterConfig


class FigmaAPI:
    def __init__(self, *, file_id: Optional[str] = None, token: Optional[str] = None) -> None:
        self._file_id = file_id
        self._token = token

    @property
    def file_id(self) -> Optional[str]:
        return self._file_id

    @file_id.setter
    def file_id(self, file_id: str):
        if isinstance(file_id, str):
            self._file_id = file_id
        else:
            raise TypeError("'file_id' must be str.")

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, token: str):
        if isinstance(token, str):
            self._token = token
        else:
            raise TypeError("'token' must be str.")

    @property
    def headers(self) -> dict[str, Any]:
        return {'X-Figma-Token': f'{self._token}'}


    def fetch(self) -> dict[str, Any]:
        """
        Returns JSON response from Figma by 'file_id'.
        """
        response = requests.get(
            f'https://api.figma.com/v1/files/{self.file_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['document']['children']

    def extract(self, filter_config: Optional[FilterConfig] = None) -> dict[str, Any]:
        ...
