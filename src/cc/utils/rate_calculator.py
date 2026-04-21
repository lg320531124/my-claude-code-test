"""Rate Calculator - Calculate rates and statistics."""

from __future__ import annotations
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class RateType(Enum):
    """Rate calculation type."""
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    AVERAGE = "average"
    MOVING_AVERAGE = "moving_average"


@dataclass
class RatePoint:
    """A rate data point."""
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateConfig:
    """Rate calculator configuration."""
    rate_type: RateType = RateType.PER_SECOND
    window_size: int = 100  # For moving average
    sample_interval: float = 1.0  # Minimum interval between samples
    min_samples: int = 2


@dataclass
class RateResult:
    """Rate calculation result."""
    rate: float
    total: float
    count: int
    duration: float
    min: Optional[float] = None
    max: Optional[float] = None
    average: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RateCalculator:
    """Calculate rates and statistics."""

    def __init__(self, config: Optional[RateConfig] = None):
        self.config = config or RateConfig()
        self._points: List[RatePoint] = []
        self._start_time: Optional[float] = None
        self._callbacks: List[Callable[[RateResult], None]] = []

    def start(self) -> None:
        """Start rate collection."""
        self._start_time = time.time()
        self._points = []

    def add_point(self, value: float, **metadata) -> RatePoint:
        """Add a rate point."""
        point = RatePoint(value=value, metadata=metadata)

        # Check minimum interval
        if self._points:
            last_time = self._points[-1].timestamp
            if point.timestamp - last_time < self.config.sample_interval:
                # Update last point instead
                self._points[-1] = point
                return point

        self._points.append(point)

        # Trim to window size
        if len(self._points) > self.config.window_size:
            self._points.pop(0)

        return point

    def stop(self) -> RateResult:
        """Stop and calculate final rate."""
        return self.calculate()

    def calculate(self) -> RateResult:
        """Calculate current rate."""
        if len(self._points) < self.config.min_samples:
            return RateResult(
                rate=0.0,
                total=0.0,
                count=len(self._points),
                duration=0.0,
            )

        total = sum(p.value for p in self._points)
        count = len(self._points)

        duration = 0.0
        if self._start_time:
            duration = time.time() - self._start_time
        elif len(self._points) >= 2:
            duration = self._points[-1].timestamp - self._points[0].timestamp

        # Calculate rate based on type
        if self.config.rate_type == RateType.PER_SECOND:
            rate = total / duration if duration > 0 else 0.0
        elif self.config.rate_type == RateType.PER_MINUTE:
            rate = total / (duration / 60) if duration > 0 else 0.0
        elif self.config.rate_type == RateType.PER_HOUR:
            rate = total / (duration / 3600) if duration > 0 else 0.0
        elif self.config.rate_type == RateType.MOVING_AVERAGE:
            window = self._points[-min(count, self.config.window_size):]
            rate = sum(p.value for p in window) / len(window)
        else:  # AVERAGE
            rate = total / count

        # Calculate statistics
        values = [p.value for p in self._points]
        min_val = min(values)
        max_val = max(values)
        avg = total / count

        return RateResult(
            rate=rate,
            total=total,
            count=count,
            duration=duration,
            min=min_val,
            max=max_val,
            average=avg,
        )

    def get_current_rate(self) -> float:
        """Get current rate."""
        result = self.calculate()
        return result.rate

    def get_statistics(self) -> Dict[str, float]:
        """Get statistics."""
        result = self.calculate()
        return {
            "rate": result.rate,
            "total": result.total,
            "count": result.count,
            "min": result.min or 0.0,
            "max": result.max or 0.0,
            "average": result.average or 0.0,
        }

    def get_points(self) -> List[RatePoint]:
        """Get all points."""
        return self._points.copy()

    def reset(self) -> None:
        """Reset calculator."""
        self._start_time = None
        self._points = []

    def add_callback(self, callback: Callable[[RateResult], None]) -> None:
        """Add callback for rate updates."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[RateResult], None]) -> None:
        """Remove callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, result: RateResult) -> None:
        """Notify callbacks."""
        for callback in self._callbacks:
            callback(result)


class ThroughputMeter:
    """Measure throughput over time."""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._samples: List[Tuple[float, int]] = []  # (timestamp, count)
        self._total: int = 0

    def add_sample(self, count: int) -> None:
        """Add a sample."""
        self._samples.append((time.time(), count))
        self._total += count

        # Trim window
        while len(self._samples) > self.window_size:
            self._samples.pop(0)

    def get_throughput(self) -> float:
        """Get throughput (items per second)."""
        if len(self._samples) < 2:
            return 0.0

        first_time, first_count = self._samples[0]
        last_time, last_count = self._samples[-1]

        duration = last_time - first_time
        if duration <= 0:
            return 0.0

        total = sum(c for _, c in self._samples)
        return total / duration

    def get_total(self) -> int:
        """Get total count."""
        return self._total

    def reset(self) -> None:
        """Reset meter."""
        self._samples = []
        self._total = 0


class LatencyTracker:
    """Track latency measurements."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._latencies: List[float] = []
        self._timestamps: List[float] = []

    def record(self, latency: float) -> None:
        """Record latency."""
        self._latencies.append(latency)
        self._timestamps.append(time.time())

        # Trim window
        while len(self._latencies) > self.window_size:
            self._latencies.pop(0)
            self._timestamps.pop(0)

    def get_average(self) -> float:
        """Get average latency."""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    def get_min(self) -> float:
        """Get minimum latency."""
        if not self._latencies:
            return 0.0
        return min(self._latencies)

    def get_max(self) -> float:
        """Get maximum latency."""
        if not self._latencies:
            return 0.0
        return max(self._latencies)

    def get_p50(self) -> float:
        """Get 50th percentile."""
        return self._get_percentile(50)

    def get_p95(self) -> float:
        """Get 95th percentile."""
        return self._get_percentile(95)

    def get_p99(self) -> float:
        """Get 99th percentile."""
        return self._get_percentile(99)

    def _get_percentile(self, percentile: float) -> float:
        """Get percentile value."""
        if not self._latencies:
            return 0.0

        sorted_latencies = sorted(self._latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        index = min(index, len(sorted_latencies) - 1)
        return sorted_latencies[index]

    def reset(self) -> None:
        """Reset tracker."""
        self._latencies = []
        self._timestamps = []


def create_rate_calculator(rate_type: RateType = RateType.PER_SECOND) -> RateCalculator:
    """Create rate calculator."""
    config = RateConfig(rate_type=rate_type)
    return RateCalculator(config)


def create_throughput_meter(window_size: int = 10) -> ThroughputMeter:
    """Create throughput meter."""
    return ThroughputMeter(window_size)


def create_latency_tracker(window_size: int = 100) -> LatencyTracker:
    """Create latency tracker."""
    return LatencyTracker(window_size)


from typing import Tuple  # Import at top for clarity


__all__ = [
    "RateType",
    "RatePoint",
    "RateConfig",
    "RateResult",
    "RateCalculator",
    "ThroughputMeter",
    "LatencyTracker",
    "create_rate_calculator",
    "create_throughput_meter",
    "create_latency_tracker",
]