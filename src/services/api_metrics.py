# -*- coding: utf-8 -*-
"""API metrics tracking service.

This module provides a service for tracking API call counts and latencies.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, UTC
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class EndpointMetrics:
    """Metrics for a single endpoint."""

    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.error_count / self.total_calls) * 100


class ApiMetricsService:
    """Service for tracking API metrics.

    Thread-safe metrics tracking for API calls including:
    - Call counts per endpoint
    - Success/error rates
    - Average latencies

    Example:
        ```python
        metrics = ApiMetricsService()

        start = time.time()
        # ... perform API call ...
        latency = (time.time() - start) * 1000

        metrics.record_call("/api/v1/channels", success=True, latency_ms=latency)

        stats = metrics.get_stats()
        ```
    """

    def __init__(self):
        """Initialize the metrics service."""
        self._lock = Lock()
        self._endpoints: dict[str, EndpointMetrics] = defaultdict(EndpointMetrics)
        self._started_at = datetime.now(UTC)
        self._gemini_api_calls = 0

    def record_call(
        self,
        endpoint: str,
        success: bool = True,
        latency_ms: float = 0.0,
    ):
        """Record an API call.

        Args:
            endpoint: The endpoint path (e.g., "/api/v1/channels")
            success: Whether the call was successful
            latency_ms: Latency in milliseconds
        """
        with self._lock:
            metrics = self._endpoints[endpoint]
            metrics.total_calls += 1
            metrics.total_latency_ms += latency_ms

            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1

    def record_gemini_call(self):
        """Record a Gemini API call."""
        with self._lock:
            self._gemini_api_calls += 1

    def get_endpoint_metrics(self, endpoint: str) -> EndpointMetrics:
        """Get metrics for a specific endpoint.

        Args:
            endpoint: The endpoint path

        Returns:
            EndpointMetrics for the specified endpoint
        """
        with self._lock:
            return self._endpoints.get(endpoint, EndpointMetrics())

    def get_stats(self) -> dict:
        """Get aggregated statistics.

        Returns:
            Dictionary with overall API statistics
        """
        with self._lock:
            total_calls = sum(m.total_calls for m in self._endpoints.values())
            total_errors = sum(m.error_count for m in self._endpoints.values())
            total_latency = sum(m.total_latency_ms for m in self._endpoints.values())

            # Get top endpoints by call count
            sorted_endpoints = sorted(
                self._endpoints.items(),
                key=lambda x: x[1].total_calls,
                reverse=True,
            )

            top_endpoints = [
                {
                    "endpoint": endpoint,
                    "calls": metrics.total_calls,
                    "errors": metrics.error_count,
                    "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                }
                for endpoint, metrics in sorted_endpoints[:10]
            ]

            return {
                "uptime_seconds": int((datetime.now(UTC) - self._started_at).total_seconds()),
                "started_at": self._started_at.isoformat(),
                "total_api_calls": total_calls,
                "total_errors": total_errors,
                "error_rate_percent": round((total_errors / total_calls * 100) if total_calls > 0 else 0, 2),
                "avg_latency_ms": round(total_latency / total_calls if total_calls > 0 else 0, 2),
                "gemini_api_calls": self._gemini_api_calls,
                "top_endpoints": top_endpoints,
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._endpoints.clear()
            self._gemini_api_calls = 0
            self._started_at = datetime.now(UTC)


# Singleton instance
_metrics_instance: ApiMetricsService | None = None


def get_api_metrics() -> ApiMetricsService:
    """Get the global API metrics instance.

    Returns:
        The singleton ApiMetricsService
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = ApiMetricsService()
    return _metrics_instance
