# -*- coding: utf-8 -*-
"""Tests for Channel CRUD API."""

from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.gemini import get_gemini_service
from src.core.database import get_db
from src.models.db_models import ChannelMetadata


class TestCreateChannel:
    """Tests for POST /api/v1/channels."""

    def test_create_channel_success(self, client_with_db: TestClient, test_db):
        """Test successful channel creation."""
        mock_gemini = MagicMock()
        mock_gemini.create_store.return_value = {
            "name": "fileSearchStores/test-store-123",
            "display_name": "Test Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.post(
            "/api/v1/channels",
            json={"name": "Test Channel"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "fileSearchStores/test-store-123"
        assert data["name"] == "Test Channel"
        assert data["file_count"] == 0
        assert "created_at" in data

        # Cleanup
        app.dependency_overrides.pop(get_gemini_service, None)

    def test_create_channel_empty_name(self, client_with_db: TestClient, test_db):
        """Test channel creation with empty name fails."""
        response = client_with_db.post(
            "/api/v1/channels",
            json={"name": ""},
        )

        assert response.status_code == 422  # Validation error

    def test_create_channel_api_error(self, client_with_db: TestClient, test_db):
        """Test channel creation handles API errors."""
        mock_gemini = MagicMock()
        mock_gemini.create_store.side_effect = Exception("API Error")

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.post(
            "/api/v1/channels",
            json={"name": "Test Channel"},
        )

        assert response.status_code == 500
        assert "Failed to create channel" in response.json()["detail"]

        app.dependency_overrides.pop(get_gemini_service, None)


class TestListChannels:
    """Tests for GET /api/v1/channels."""

    def test_list_channels_success(self, client_with_db: TestClient, test_db):
        """Test listing channels."""
        mock_gemini = MagicMock()
        mock_gemini.list_stores.return_value = [
            {"name": "fileSearchStores/store-1", "display_name": "Channel 1"},
            {"name": "fileSearchStores/store-2", "display_name": "Channel 2"},
        ]

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.get("/api/v1/channels")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["channels"]) == 2
        assert data["channels"][0]["name"] == "Channel 1"
        assert data["channels"][1]["name"] == "Channel 2"

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_list_channels_empty(self, client_with_db: TestClient, test_db):
        """Test listing when no channels exist."""
        mock_gemini = MagicMock()
        mock_gemini.list_stores.return_value = []

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.get("/api/v1/channels")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["channels"] == []

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_list_channels_api_error(self, client_with_db: TestClient, test_db):
        """Test listing channels handles API errors."""
        mock_gemini = MagicMock()
        mock_gemini.list_stores.side_effect = Exception("API Error")

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.get("/api/v1/channels")

        assert response.status_code == 500
        assert "Failed to list channels" in response.json()["detail"]

        app.dependency_overrides.pop(get_gemini_service, None)


class TestGetChannel:
    """Tests for GET /api/v1/channels/{channel_id}."""

    def test_get_channel_success(self, client_with_db: TestClient, test_db):
        """Test getting a specific channel."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/store-123",
            "display_name": "My Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.get("/api/v1/channels/fileSearchStores/store-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "fileSearchStores/store-123"
        assert data["name"] == "My Channel"

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_get_channel_not_found(self, client_with_db: TestClient, test_db):
        """Test getting non-existent channel returns 404."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = None

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.get("/api/v1/channels/fileSearchStores/not-exists")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

        app.dependency_overrides.pop(get_gemini_service, None)


class TestDeleteChannel:
    """Tests for DELETE /api/v1/channels/{channel_id}."""

    def test_delete_channel_success(self, client_with_db: TestClient, test_db):
        """Test successful channel deletion (soft delete)."""
        channel_id = "fileSearchStores/store-123"

        # Create channel metadata first (required for soft delete)
        channel = ChannelMetadata(
            gemini_store_id=channel_id,
            name="My Channel",
            created_at=datetime.now(UTC),
            last_accessed_at=datetime.now(UTC),
        )
        test_db.add(channel)
        test_db.commit()

        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": channel_id,
            "display_name": "My Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.delete(f"/api/v1/channels/{channel_id}")

        assert response.status_code == 204

        # Verify channel is soft-deleted
        test_db.refresh(channel)
        assert channel.deleted_at is not None

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_delete_channel_not_found(self, client_with_db: TestClient, test_db):
        """Test deleting non-existent channel returns 404."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = None

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.delete("/api/v1/channels/fileSearchStores/not-exists")

        assert response.status_code == 404

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_delete_channel_metadata_not_found(self, client_with_db: TestClient, test_db):
        """Test delete returns 404 when channel metadata is not in database."""
        channel_id = "fileSearchStores/store-123"

        # Gemini store exists but no local metadata
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": channel_id,
            "display_name": "My Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.delete(f"/api/v1/channels/{channel_id}")

        assert response.status_code == 404
        assert "metadata not found" in response.json()["detail"]

        app.dependency_overrides.pop(get_gemini_service, None)


class TestUpdateChannel:
    """Tests for PUT /api/v1/channels/{channel_id}."""

    def test_update_channel_name_success(self, client_with_db: TestClient, test_db):
        """Test updating channel name."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/store-123",
            "display_name": "Old Name",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.put(
            "/api/v1/channels/fileSearchStores/store-123",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "fileSearchStores/store-123"
        assert data["name"] == "New Name"

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_update_channel_description_success(self, client_with_db: TestClient, test_db):
        """Test updating channel description."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/store-123",
            "display_name": "My Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.put(
            "/api/v1/channels/fileSearchStores/store-123",
            json={"description": "New description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_update_channel_both_fields(self, client_with_db: TestClient, test_db):
        """Test updating both name and description."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/store-123",
            "display_name": "Old Name",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.put(
            "/api/v1/channels/fileSearchStores/store-123",
            json={"name": "New Name", "description": "New description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_update_channel_not_found(self, client_with_db: TestClient, test_db):
        """Test updating non-existent channel returns 404."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = None

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.put(
            "/api/v1/channels/fileSearchStores/not-exists",
            json={"name": "New Name"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

        app.dependency_overrides.pop(get_gemini_service, None)

    def test_update_channel_empty_body(self, client_with_db: TestClient, test_db):
        """Test updating with no fields returns 400."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/store-123",
            "display_name": "My Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client_with_db.put(
            "/api/v1/channels/fileSearchStores/store-123",
            json={},
        )

        assert response.status_code == 400
        assert "At least one" in response.json()["detail"]

        app.dependency_overrides.pop(get_gemini_service, None)
