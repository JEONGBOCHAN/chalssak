# -*- coding: utf-8 -*-
"""Gemini File Search API service."""

from functools import lru_cache
from typing import Any

import requests
from google import genai
from google.genai import types

from src.core.config import get_settings


class GeminiService:
    """Service for interacting with Gemini File Search API."""

    def __init__(self):
        """Initialize the Gemini client."""
        settings = get_settings()
        self._api_key = settings.google_api_key
        self._client = genai.Client(api_key=self._api_key)

    @property
    def client(self) -> genai.Client:
        """Get the Gemini client."""
        return self._client

    # ========== File Search Store (Channel) Operations ==========

    def create_store(self, display_name: str) -> dict[str, Any]:
        """Create a new File Search Store.

        Args:
            display_name: Human-readable name for the store

        Returns:
            Store information including name (ID)
        """
        store = self._client.file_search_stores.create(
            config={"display_name": display_name}
        )
        return {
            "name": store.name,
            "display_name": display_name,
        }

    def get_store(self, store_name: str) -> dict[str, Any] | None:
        """Get a File Search Store by name.

        Args:
            store_name: The store name/ID (e.g., "fileSearchStores/xxx")

        Returns:
            Store information or None if not found
        """
        try:
            store = self._client.file_search_stores.get(name=store_name)
            return {
                "name": store.name,
                "display_name": getattr(store, "display_name", ""),
            }
        except Exception:
            return None

    def list_stores(self) -> list[dict[str, Any]]:
        """List all File Search Stores.

        Returns:
            List of store information
        """
        stores = []
        for store in self._client.file_search_stores.list():
            stores.append({
                "name": store.name,
                "display_name": getattr(store, "display_name", ""),
            })
        return stores

    def delete_store(self, store_name: str, force: bool = True) -> bool:
        """Delete a File Search Store.

        Uses REST API directly because SDK doesn't support force delete.

        Args:
            store_name: The store name/ID
            force: Whether to force delete (removes all files first)

        Returns:
            True if deleted successfully
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}"
        if force:
            url += "?force=true"
        url += f"&key={self._api_key}" if force else f"?key={self._api_key}"

        response = requests.delete(url)
        return response.status_code == 200

    # ========== Document Operations ==========

    def upload_file(
        self,
        store_name: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Upload a file to a File Search Store.

        Args:
            store_name: The store name/ID
            file_path: Path to the file to upload

        Returns:
            Operation information
        """
        operation = self._client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
        )
        return {
            "name": operation.name,
            "done": operation.done,
        }

    def get_operation_status(self, operation_name: str) -> dict[str, Any]:
        """Get the status of an upload operation.

        Args:
            operation_name: The operation name/ID

        Returns:
            Operation status
        """
        try:
            operation = self._client.operations.get(operation_name)
            return {
                "name": operation.name,
                "done": operation.done,
            }
        except Exception:
            return {"name": operation_name, "done": False, "error": "Not found"}

    def list_store_files(self, store_name: str) -> list[dict[str, Any]]:
        """List all files in a File Search Store.

        Args:
            store_name: The store name/ID

        Returns:
            List of file information
        """
        files = []
        try:
            # Use REST API to list files in store
            url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}/files"
            url += f"?key={self._api_key}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for file_data in data.get("files", []):
                    files.append({
                        "name": file_data.get("name", ""),
                        "display_name": file_data.get("displayName", ""),
                        "size_bytes": file_data.get("sizeBytes", 0),
                        "state": file_data.get("state", ""),
                    })
        except Exception:
            pass
        return files

    def delete_file(self, file_name: str) -> bool:
        """Delete a file from File Search Store.

        Args:
            file_name: The file name/ID

        Returns:
            True if deleted successfully
        """
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
            url += f"?key={self._api_key}"
            response = requests.delete(url)
            return response.status_code == 200
        except Exception:
            return False


@lru_cache
def get_gemini_service() -> GeminiService:
    """Get cached GeminiService instance."""
    return GeminiService()
