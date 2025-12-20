# -*- coding: utf-8 -*-
"""Tests for API metrics service."""

import pytest
from unittest.mock import patch

from src.services.api_metrics import (
    ApiMetricsService,
    EndpointMetrics,
    get_api_metrics,
)


class TestEndpointMetrics:
    """Tests for EndpointMetrics."""

    def test_default_values(self):
        """Test default metric values."""
        metrics = EndpointMetrics()
        assert metrics.total_calls == 0
        assert metrics.success_count == 0
        assert metrics.error_count == 0
        assert metrics.total_latency_ms == 0.0

    def test_avg_latency_empty(self):
        """Test average latency with no calls."""
        metrics = EndpointMetrics()
        assert metrics.avg_latency_ms == 0.0

    def test_avg_latency_calculation(self):
        """Test average latency calculation."""
        metrics = EndpointMetrics(
            total_calls=4,
            total_latency_ms=100.0,
        )
        assert metrics.avg_latency_ms == 25.0

    def test_error_rate_empty(self):
        """Test error rate with no calls."""
        metrics = EndpointMetrics()
        assert metrics.error_rate == 0.0

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        metrics = EndpointMetrics(
            total_calls=10,
            error_count=2,
        )
        assert metrics.error_rate == 20.0


class TestApiMetricsService:
    """Tests for ApiMetricsService."""

    def test_record_successful_call(self):
        """Test recording a successful API call."""
        service = ApiMetricsService()
        service.record_call("/api/v1/test", success=True, latency_ms=50.0)

        metrics = service.get_endpoint_metrics("/api/v1/test")
        assert metrics.total_calls == 1
        assert metrics.success_count == 1
        assert metrics.error_count == 0
        assert metrics.total_latency_ms == 50.0

    def test_record_failed_call(self):
        """Test recording a failed API call."""
        service = ApiMetricsService()
        service.record_call("/api/v1/test", success=False, latency_ms=100.0)

        metrics = service.get_endpoint_metrics("/api/v1/test")
        assert metrics.total_calls == 1
        assert metrics.success_count == 0
        assert metrics.error_count == 1

    def test_record_multiple_calls(self):
        """Test recording multiple calls to same endpoint."""
        service = ApiMetricsService()
        service.record_call("/api/v1/test", success=True, latency_ms=10.0)
        service.record_call("/api/v1/test", success=True, latency_ms=20.0)
        service.record_call("/api/v1/test", success=False, latency_ms=30.0)

        metrics = service.get_endpoint_metrics("/api/v1/test")
        assert metrics.total_calls == 3
        assert metrics.success_count == 2
        assert metrics.error_count == 1
        assert metrics.total_latency_ms == 60.0
        assert metrics.avg_latency_ms == 20.0

    def test_record_gemini_call(self):
        """Test recording Gemini API calls."""
        service = ApiMetricsService()
        service.record_gemini_call()
        service.record_gemini_call()

        stats = service.get_stats()
        assert stats["gemini_api_calls"] == 2

    def test_get_stats_empty(self):
        """Test getting stats with no recorded calls."""
        service = ApiMetricsService()
        stats = service.get_stats()

        assert stats["total_api_calls"] == 0
        assert stats["total_errors"] == 0
        assert stats["error_rate_percent"] == 0
        assert stats["gemini_api_calls"] == 0
        assert stats["top_endpoints"] == []

    def test_get_stats_with_calls(self):
        """Test getting stats with recorded calls."""
        service = ApiMetricsService()
        service.record_call("/api/v1/a", success=True, latency_ms=10.0)
        service.record_call("/api/v1/a", success=True, latency_ms=20.0)
        service.record_call("/api/v1/b", success=False, latency_ms=30.0)

        stats = service.get_stats()

        assert stats["total_api_calls"] == 3
        assert stats["total_errors"] == 1
        assert stats["error_rate_percent"] == pytest.approx(33.33, rel=0.01)
        assert len(stats["top_endpoints"]) == 2

    def test_top_endpoints_sorted(self):
        """Test that top endpoints are sorted by call count."""
        service = ApiMetricsService()
        service.record_call("/api/v1/less", success=True)
        service.record_call("/api/v1/more", success=True)
        service.record_call("/api/v1/more", success=True)

        stats = service.get_stats()
        top = stats["top_endpoints"]

        assert top[0]["endpoint"] == "/api/v1/more"
        assert top[0]["calls"] == 2
        assert top[1]["endpoint"] == "/api/v1/less"
        assert top[1]["calls"] == 1

    def test_reset(self):
        """Test resetting all metrics."""
        service = ApiMetricsService()
        service.record_call("/api/v1/test", success=True, latency_ms=50.0)
        service.record_gemini_call()

        service.reset()

        stats = service.get_stats()
        assert stats["total_api_calls"] == 0
        assert stats["gemini_api_calls"] == 0

    def test_uptime_tracking(self):
        """Test that uptime is tracked."""
        service = ApiMetricsService()
        stats = service.get_stats()

        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] >= 0
        assert "started_at" in stats


class TestGetApiMetrics:
    """Tests for get_api_metrics singleton."""

    def test_returns_singleton(self):
        """Test that get_api_metrics returns singleton."""
        # Reset singleton for test
        import src.services.api_metrics as api_metrics_module
        api_metrics_module._metrics_instance = None

        metrics1 = get_api_metrics()
        metrics2 = get_api_metrics()

        assert metrics1 is metrics2
