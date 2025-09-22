"""
Utility module for signing API requests to Smart Tyre
"""

import hashlib
from typing import Dict, List, Optional

class SignUtil:
    """
    Utility class to generate request signatures required by Smart Tyre API.
    """

    @staticmethod
    def sign(
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        params: Optional[Dict[str, List[str]]] = None,
        paths: Optional[List[str]] = None,
        sign_key: str = ""
    ) -> str:
        """
        Generate a signature by concatenating and hashing request components.

        Args:
            headers: HTTP request headers
            body: Raw request body as a string
            params: URL query parameters, with each param key mapped to a list of values
            paths: URL path segments (if any)
            sign_key: Secret signing key provided by Smart Tyre

        Returns:
            MD5 hex digest of the concatenated string
        """
        components = []

        if headers:
            for key in sorted(headers.keys()):
                components.append(f"{key}={headers[key]}&")

        if body:
            components.append(f"{body}&")

        if params:
            for key in sorted(params.keys()):
                sorted_values = sorted(params[key])
                param_value = ",".join(sorted_values)
                components.append(f"{key}={param_value}&")

        if paths:
            sorted_paths = sorted(paths)
            path_string = ",".join(sorted_paths)
            components.append(f"{path_string}&")

        components.append(sign_key)

        raw_string = "".join(components)
        return hashlib.md5(raw_string.encode("utf-8")).hexdigest()
