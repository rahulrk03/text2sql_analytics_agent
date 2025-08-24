"""
Unit tests for the FastAPI endpoints in app.api module.
Tests all 4 API endpoints with streaming support and improved error handling.
"""

import json
import uuid
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.api import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "<sql>SELECT * FROM public.customers LIMIT 10</sql>"
    return mock_response


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_ok(self, client):
        """Test that health endpoint returns {"ok": True}."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestQueryEndpoint:
    """Tests for the /query endpoint."""

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.run_page")
    def test_query_success(
        self,
        mock_run_page,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
        mock_openai_response,
    ):
        """Test successful query execution."""
        # Setup mocks
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_run_page.return_value = (
            ["id", "name"],  # columns
            [[1, "John"], [2, "Jane"]],  # rows
            2,  # total
        )

        # Make request
        response = client.post(
            "/query",
            json={"question": "Show me all customers", "page": 1, "page_size": 10, "stream": False},
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "columns" in data
        assert "rows" in data
        assert "pagination" in data
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == [[1, "John"], [2, "Jane"]]
        assert data["pagination"]["total_rows"] == 2
        assert data["pagination"]["total_pages"] == 1

    def test_query_no_llm_configured(self, client):
        """Test query endpoint when LLM is not configured."""
        with patch("app.api.client", None):
            response = client.post(
                "/query",
                json={"question": "Show me all customers"},
            )
            assert response.status_code == 503
            assert "LLM service not configured" in response.json()["detail"]

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_query_unsafe_sql(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with unsafe SQL."""
        # Setup mocks to return unsafe SQL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>DELETE FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"

        # Make request
        response = client.post(
            "/query",
            json={"question": "Delete all customers"},
        )

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsafe or invalid SQL generated"

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_query_invalid_sql_format(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with non-SELECT SQL."""
        # Setup mocks to return non-SELECT SQL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>UPDATE customers SET name = 'test'</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"

        # Make request
        response = client.post(
            "/query",
            json={"question": "Update customer names"},
        )

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsafe or invalid SQL generated"

    def test_query_missing_question(self, client):
        """Test query endpoint with missing question field."""
        response = client.post("/query", json={})
        assert response.status_code == 422  # Validation error

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_query_llm_api_error(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with LLM API error."""
        # Setup mocks
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_client.chat.completions.create.side_effect = Exception("API error")

        # Make request
        response = client.post(
            "/query",
            json={"question": "What are the customers?"},
        )

        # Assertions
        assert response.status_code == 502
        assert "LLM service error" in response.json()["detail"]

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.run_page")
    def test_query_non_streaming_success(
        self,
        mock_run_page,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test successful non-streaming query."""
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT * FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_run_page.return_value = (
            ["id", "name"],
            [[1, "John"], [2, "Jane"]],
            2
        )

        # Make request with stream=False
        response = client.post(
            "/query",
            json={"question": "Show me customers", "stream": False},
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["sql"] == "SELECT * FROM customers"
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == [[1, "John"], [2, "Jane"]]
        assert data["pagination"]["total_rows"] == 2

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.stream_query_results")
    def test_query_streaming_success(
        self,
        mock_stream_query_results,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test successful streaming query."""
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT * FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        
        # Mock streaming response
        def mock_generator():
            yield '{"sql": "SELECT * FROM customers", "columns": ["id", "name"], "rows": ['
            yield '[1, "John"]'
            yield ', [2, "Jane"]'
            yield '], "pagination": {"page": 1, "page_size": 50, "total_rows": 2, "total_pages": 1}}'
        
        mock_stream_query_results.return_value = mock_generator()

        # Make request with stream=True (default)
        response = client.post(
            "/query",
            json={"question": "Show me customers"},
        )

        # Assertions
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        # Read streaming content
        content = b"".join(response.iter_bytes()).decode()
        data = json.loads(content)
        assert data["sql"] == "SELECT * FROM customers"
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == [[1, "John"], [2, "Jane"]]

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.run_page")
    def test_query_database_connection_error(
        self,
        mock_run_page,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with database connection error."""
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT * FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_run_page.side_effect = Exception("connection timeout")

        # Make request with stream=False
        response = client.post(
            "/query",
            json={"question": "Show me customers", "stream": False},
        )

        # Assertions
        assert response.status_code == 503
        assert "Database error" in response.json()["detail"]
        assert "connection timeout" in response.json()["detail"]


class TestExportStartEndpoint:
    """Tests for the /export/start endpoint."""

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.insert_job")
    @patch("app.api.get_sqs")
    @patch("app.api._queue_url")
    def test_export_start_success(
        self,
        mock_queue_url,
        mock_get_sqs,
        mock_insert_job,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
        mock_openai_response,
    ):
        """Test successful export job start."""
        # Setup mocks
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_queue_url.return_value = "https://sqs.amazonaws.com/queue"
        mock_sqs = Mock()
        mock_get_sqs.return_value = mock_sqs

        # Make request
        response = client.post(
            "/export/start",
            json={"question": "Export all customers"},
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "PENDING"
        assert isinstance(data["job_id"], str)

        # Verify job was inserted and SQS message was sent
        mock_insert_job.assert_called_once()
        mock_sqs.send_message.assert_called_once()

    def test_export_start_no_llm_configured(self, client):
        """Test export start endpoint when LLM is not configured."""
        with patch("app.api.client", None):
            response = client.post(
                "/export/start",
                json={"question": "Export all customers"},
            )
            assert response.status_code == 500
            assert response.json()["detail"] == "LLM not configured"

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_export_start_unsafe_sql(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test export start endpoint with unsafe SQL."""
        # Setup mocks to return unsafe SQL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>DROP TABLE customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"

        # Make request
        response = client.post(
            "/export/start",
            json={"question": "Drop customers table"},
        )

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsafe or invalid SQL generated"

    def test_export_start_missing_question(self, client):
        """Test export start endpoint with missing question field."""
        response = client.post("/export/start", json={})
        assert response.status_code == 422  # Validation error


class TestExportStatusEndpoint:
    """Tests for the /export/status/{job_id} endpoint."""

    @patch("app.api.get_job")
    @patch("app.api.get_s3")
    @patch.dict("os.environ", {"EXPORT_BUCKET": "test-bucket"})
    def test_export_status_success(self, mock_get_s3, mock_get_job, client):
        """Test export status endpoint for successful job."""
        job_id = str(uuid.uuid4())
        
        # Setup mocks
        mock_get_job.return_value = {
            "job_id": job_id,
            "status": "SUCCESS",
            "s3_key": f"exports/{job_id}.csv",
            "row_count": 1000,
            "error": None,
        }
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/exports/test.csv"
        mock_get_s3.return_value = mock_s3

        # Make request
        response = client.get(f"/export/status/{job_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "SUCCESS"
        assert "download_url" in data
        assert data["row_count"] == 1000

    @patch("app.api.get_job")
    def test_export_status_failed(self, mock_get_job, client):
        """Test export status endpoint for failed job."""
        job_id = str(uuid.uuid4())
        
        # Setup mocks
        mock_get_job.return_value = {
            "job_id": job_id,
            "status": "FAILED",
            "s3_key": f"exports/{job_id}.csv",
            "row_count": None,
            "error": "Database connection failed",
        }

        # Make request
        response = client.get(f"/export/status/{job_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "FAILED"
        assert data["error"] == "Database connection failed"
        assert "download_url" not in data

    @patch("app.api.get_job")
    def test_export_status_pending(self, mock_get_job, client):
        """Test export status endpoint for pending job."""
        job_id = str(uuid.uuid4())
        
        # Setup mocks
        mock_get_job.return_value = {
            "job_id": job_id,
            "status": "PENDING",
            "s3_key": f"exports/{job_id}.csv",
            "row_count": None,
            "error": None,
        }

        # Make request
        response = client.get(f"/export/status/{job_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "PENDING"
        assert "download_url" not in data
        assert "error" not in data

    @patch("app.api.get_job")
    def test_export_status_job_not_found(self, mock_get_job, client):
        """Test export status endpoint for non-existent job."""
        job_id = str(uuid.uuid4())
        
        # Setup mocks
        mock_get_job.return_value = None

        # Make request
        response = client.get(f"/export/status/{job_id}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "job not found"