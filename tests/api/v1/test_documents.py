# -*- coding: utf-8 -*-
"""Tests for Document upload API."""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.gemini import get_gemini_service


class TestUploadDocument:
    """Tests for POST /api/v1/documents."""

    def test_upload_document_success(self, client: TestClient):
        """Test successful document upload."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/test-store",
            "display_name": "Test Channel",
        }
        mock_gemini.upload_file.return_value = {
            "name": "operations/upload-123",
            "done": False,
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.post(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/test-store"},
            files={"file": ("test.pdf", b"PDF content here", "application/pdf")},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["id"] == "operations/upload-123"
        assert data["filename"] == "test.pdf"
        assert data["status"] == "processing"

        app.dependency_overrides.clear()

    def test_upload_document_channel_not_found(self, client: TestClient):
        """Test upload to non-existent channel."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = None

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.post(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/not-exists"},
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_upload_document_invalid_extension(self, client: TestClient):
        """Test upload with invalid file extension."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/test-store",
            "display_name": "Test Channel",
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.post(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/test-store"},
            files={"file": ("test.exe", b"Binary content", "application/octet-stream")},
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

        app.dependency_overrides.clear()


class TestListDocuments:
    """Tests for GET /api/v1/documents."""

    def test_list_documents_success(self, client: TestClient):
        """Test listing documents in channel."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/test-store",
            "display_name": "Test Channel",
        }
        mock_gemini.list_store_files.return_value = [
            {"name": "files/file-1", "display_name": "doc1.pdf", "size_bytes": 1024, "state": "ACTIVE"},
            {"name": "files/file-2", "display_name": "doc2.pdf", "size_bytes": 2048, "state": "ACTIVE"},
        ]

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.get(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/test-store"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2
        assert data["documents"][0]["filename"] == "doc1.pdf"
        assert data["documents"][0]["file_size"] == 1024

        app.dependency_overrides.clear()

    def test_list_documents_empty(self, client: TestClient):
        """Test listing when no documents exist."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/test-store",
            "display_name": "Test Channel",
        }
        mock_gemini.list_store_files.return_value = []

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.get(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/test-store"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []

        app.dependency_overrides.clear()

    def test_list_documents_channel_not_found(self, client: TestClient):
        """Test listing documents in non-existent channel."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = None

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.get(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/not-exists"},
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_list_documents_api_error(self, client: TestClient):
        """Test listing documents handles API errors."""
        mock_gemini = MagicMock()
        mock_gemini.get_store.return_value = {
            "name": "fileSearchStores/test-store",
            "display_name": "Test Channel",
        }
        mock_gemini.list_store_files.side_effect = Exception("API Error")

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.get(
            "/api/v1/documents",
            params={"channel_id": "fileSearchStores/test-store"},
        )

        assert response.status_code == 500
        assert "Failed to list documents" in response.json()["detail"]

        app.dependency_overrides.clear()


class TestGetDocumentStatus:
    """Tests for GET /api/v1/documents/{document_id}/status."""

    def test_get_document_status_processing(self, client: TestClient):
        """Test getting status of processing document."""
        mock_gemini = MagicMock()
        mock_gemini.get_operation_status.return_value = {
            "name": "operations/upload-123",
            "done": False,
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.get("/api/v1/documents/operations/upload-123/status")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "operations/upload-123"
        assert data["done"] is False

        app.dependency_overrides.clear()

    def test_get_document_status_completed(self, client: TestClient):
        """Test getting status of completed upload."""
        mock_gemini = MagicMock()
        mock_gemini.get_operation_status.return_value = {
            "name": "operations/upload-123",
            "done": True,
        }

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.get("/api/v1/documents/operations/upload-123/status")

        assert response.status_code == 200
        data = response.json()
        assert data["done"] is True

        app.dependency_overrides.clear()


class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{document_id}."""

    def test_delete_document_success(self, client: TestClient):
        """Test successful document deletion."""
        mock_gemini = MagicMock()
        mock_gemini.delete_file.return_value = True

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.delete("/api/v1/documents/files/file-123")

        assert response.status_code == 204

        app.dependency_overrides.clear()

    def test_delete_document_api_error(self, client: TestClient):
        """Test delete handles API errors."""
        mock_gemini = MagicMock()
        mock_gemini.delete_file.return_value = False

        app.dependency_overrides[get_gemini_service] = lambda: mock_gemini

        response = client.delete("/api/v1/documents/files/file-123")

        assert response.status_code == 500

        app.dependency_overrides.clear()
