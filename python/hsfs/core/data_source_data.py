#
#   Copyright 2025 Hopsworks AB
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from __future__ import annotations

from typing import (
    Any,
    Dict,
    Optional,
)

import humps
from hsfs import feature


class DataSourceData:
    """
    Metadata object used to provide Data source data information for a feature group.
    """

    def __init__(
        self,
        limit: Optional[int] = None,
        features: Optional[list[feature.Feature]] = None,
        preview: Optional[list[dict]] = None,
        schema_fetch_failed: Optional[bool] = False,
        schema_fetch_in_progress: Optional[bool] = False,
        schema_fetch_logs: Optional[str] = None,
        **kwargs,
    ):
        self._limit = limit
        self._features = features
        self._preview = preview
        self._schema_fetch_failed = schema_fetch_failed
        self._schema_fetch_in_progress = schema_fetch_in_progress
        self._schema_fetch_logs = schema_fetch_logs

    @classmethod
    def from_response_json(cls, json_dict: Dict[str, Any]) -> DataSourceData:
        if json_dict is None:
            return None

        json_decamelized: dict = humps.decamelize(json_dict)

        return cls(**json_decamelized)

    @property
    def limit(self) -> Optional[int]:
        return self._limit

    @property
    def features(self) -> Optional[list[feature.Feature]]:
        return self._features

    @property
    def preview(self) -> Optional[list[dict]]:
        return self._preview
    
    @property
    def schema_fetch_failed(self) -> Optional[bool]:
        return self._schema_fetch_failed
    
    @property
    def schema_fetch_in_progress(self) -> Optional[bool]:
        return self._schema_fetch_in_progress
    
    @property
    def schema_fetch_logs(self) -> Optional[str]:
        return self._schema_fetch_logs
