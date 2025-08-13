# pyright: strict
from __future__ import annotations

from .filters import FilterConfig


class FigmaSession:
    def __init__(self, *, file_id: str = "", token: str = "", filter_config: FilterConfig | None = None):
        self._file_id = file_id
        self._token = token
        self._filter_config: FilterConfig = filter_config or FilterConfig()

    @property
    def file_id(self) -> str:
        return self._file_id

    @property
    def token(self) -> str:
        return self._token

    @property
    def filter_config(self) -> FilterConfig:
        return self._filter_config

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Figma-Token": self._token}

    @file_id.setter  # type: ignore[no-redef, attr-defined]
    def file_id(self, file_id: str):
        if isinstance(file_id, str):
            self._file_id = file_id
        else:
            raise TypeError("'file_id' must be str")

    @token.setter  # type: ignore[no-redef, attr-defined]
    def token(self, token: str):
        if isinstance(token, str):
            self._token = token
        else:
            raise TypeError("'token' must be str")

    @filter_config.setter  # type: ignore[no-redef, attr-defined]
    def filter_config(self, filter_config: FilterConfig):
        if isinstance(filter_config, FilterConfig):
            self._filter_config = filter_config
        else:
            raise TypeError("'filter_config' must be FilterConfig")
