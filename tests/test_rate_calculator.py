"""Tests for Rate Calculator."""

import pytest
import time

from cc.utils.rate_calculator import (
    RateType,
    RatePoint,
    RateConfig,
    RateResult,
    RateCalculator,
    ThroughputMeter,
    LatencyTracker,
    create_rate_calculator,
    create_throughput_meter,
    create_latency_tracker,
)


class TestRateType:
    """Test RateType enum."""

    def test_all_types(self):
        """Test all rate types."""
        assert RateType.PER_SECOND.value == "per_second"
        assert RateType.PER_MINUTE.value == "per_minute"
        assert RateType.PER_HOUR.value == "per_hour"
        assert RateType.AVERAGE.value == "average"
        assert RateType.MOVING_AVERAGE.value == "moving_average"


class TestRatePoint:
    """Test RatePoint."""

    def test_create(self):
        """Test creating rate point."""
        point = RatePoint(value=10.0)
        assert point.value == 10.0
        assert point.timestamp > 0


class TestRateConfig:
    """Test RateConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = RateConfig()
        assert config.rate_type == RateType.PER_SECOND
        assert config.window_size == 100

    def test_custom(self):
        """Test custom configuration."""
        config = RateConfig(rate_type=RateType.PER_MINUTE, window_size=50)
        assert config.rate_type == RateType.PER_MINUTE
        assert config.window_size == 50


class TestRateResult:
    """Test RateResult."""

    def test_create(self):
        """Test creating rate result."""
        result = RateResult(rate=10.0, total=100.0, count=10, duration=10.0)
        assert result.rate == 10.0
        assert result.total == 100.0


class TestRateCalculator:
    """Test RateCalculator."""

    def test_init(self):
        """Test initialization."""
        calc = RateCalculator()
        assert calc.config is not None

    def test_start(self):
        """Test starting."""
        calc = RateCalculator()
        calc.start()
        assert calc._start_time is not None

    def test_add_point(self):
        """Test adding point."""
        calc = RateCalculator()
        calc.start()
        point = calc.add_point(10.0)
        assert len(calc._points) == 1
        assert point.value == 10.0

    def test_add_multiple_points(self):
        """Test adding multiple points."""
        config = RateConfig(sample_interval=0.0)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        time.sleep(0.1)
        calc.add_point(20.0)
        assert len(calc._points) == 2

    def test_stop(self):
        """Test stopping."""
        config = RateConfig(sample_interval=0.0, min_samples=1)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        calc.add_point(20.0)
        result = calc.stop()
        assert result.count == 2

    def test_calculate(self):
        """Test calculating rate."""
        config = RateConfig(sample_interval=0.0, min_samples=1)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        calc.add_point(20.0)
        result = calc.calculate()
        assert result.total == 30.0
        assert result.count == 2

    def test_calculate_insufficient_samples(self):
        """Test calculating with insufficient samples."""
        config = RateConfig(min_samples=2)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        result = calc.calculate()
        assert result.rate == 0.0

    def test_get_current_rate(self):
        """Test getting current rate."""
        calc = RateCalculator()
        calc.start()
        calc.add_point(10.0)
        calc.add_point(20.0)
        rate = calc.get_current_rate()
        assert rate >= 0

    def test_get_statistics(self):
        """Test getting statistics."""
        config = RateConfig(sample_interval=0.0, min_samples=1)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        calc.add_point(20.0)
        calc.add_point(30.0)
        stats = calc.get_statistics()
        assert stats["total"] == 60.0
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0

    def test_get_points(self):
        """Test getting points."""
        config = RateConfig(sample_interval=0.0)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        calc.add_point(20.0)
        points = calc.get_points()
        assert len(points) == 2

    def test_reset(self):
        """Test resetting."""
        calc = RateCalculator()
        calc.start()
        calc.add_point(10.0)
        calc.reset()
        assert len(calc._points) == 0
        assert calc._start_time is None

    def test_window_size(self):
        """Test window size limit."""
        config = RateConfig(window_size=5)
        calc = RateCalculator(config)
        calc.start()
        for i in range(10):
            calc.add_point(float(i))
        assert len(calc._points) <= 5

    def test_per_minute_rate(self):
        """Test per minute rate."""
        config = RateConfig(rate_type=RateType.PER_MINUTE)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(60.0)
        calc.add_point(60.0)
        result = calc.calculate()
        assert result.rate >= 0

    def test_average_rate(self):
        """Test average rate."""
        config = RateConfig(rate_type=RateType.AVERAGE, sample_interval=0.0, min_samples=1)
        calc = RateCalculator(config)
        calc.start()
        calc.add_point(10.0)
        calc.add_point(20.0)
        calc.add_point(30.0)
        result = calc.calculate()
        assert result.average == 20.0


class TestThroughputMeter:
    """Test ThroughputMeter."""

    def test_init(self):
        """Test initialization."""
        meter = ThroughputMeter()
        assert meter.window_size == 10

    def test_add_sample(self):
        """Test adding sample."""
        meter = ThroughputMeter()
        meter.add_sample(100)
        assert meter.get_total() == 100

    def test_get_throughput(self):
        """Test getting throughput."""
        meter = ThroughputMeter()
        meter.add_sample(100)
        time.sleep(0.1)
        meter.add_sample(200)
        throughput = meter.get_throughput()
        assert throughput > 0

    def test_get_throughput_insufficient(self):
        """Test getting throughput with insufficient samples."""
        meter = ThroughputMeter()
        meter.add_sample(100)
        throughput = meter.get_throughput()
        assert throughput == 0.0

    def test_reset(self):
        """Test resetting."""
        meter = ThroughputMeter()
        meter.add_sample(100)
        meter.reset()
        assert meter.get_total() == 0


class TestLatencyTracker:
    """Test LatencyTracker."""

    def test_init(self):
        """Test initialization."""
        tracker = LatencyTracker()
        assert tracker.window_size == 100

    def test_record(self):
        """Test recording latency."""
        tracker = LatencyTracker()
        tracker.record(10.0)
        tracker.record(20.0)
        assert len(tracker._latencies) == 2

    def test_get_average(self):
        """Test getting average."""
        tracker = LatencyTracker()
        tracker.record(10.0)
        tracker.record(20.0)
        tracker.record(30.0)
        assert tracker.get_average() == 20.0

    def test_get_min(self):
        """Test getting min."""
        tracker = LatencyTracker()
        tracker.record(10.0)
        tracker.record(20.0)
        assert tracker.get_min() == 10.0

    def test_get_max(self):
        """Test getting max."""
        tracker = LatencyTracker()
        tracker.record(10.0)
        tracker.record(20.0)
        assert tracker.get_max() == 20.0

    def test_get_p50(self):
        """Test getting p50."""
        tracker = LatencyTracker()
        for i in range(100):
            tracker.record(float(i))
        p50 = tracker.get_p50()
        assert p50 >= 50.0

    def test_get_p95(self):
        """Test getting p95."""
        tracker = LatencyTracker()
        for i in range(100):
            tracker.record(float(i))
        p95 = tracker.get_p95()
        assert p95 >= 95.0

    def test_get_p99(self):
        """Test getting p99."""
        tracker = LatencyTracker()
        for i in range(100):
            tracker.record(float(i))
        p99 = tracker.get_p99()
        assert p99 >= 99.0

    def test_empty_stats(self):
        """Test stats with no data."""
        tracker = LatencyTracker()
        assert tracker.get_average() == 0.0
        assert tracker.get_min() == 0.0
        assert tracker.get_max() == 0.0

    def test_reset(self):
        """Test resetting."""
        tracker = LatencyTracker()
        tracker.record(10.0)
        tracker.reset()
        assert len(tracker._latencies) == 0


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_rate_calculator(self):
        """Test create_rate_calculator."""
        calc = create_rate_calculator(RateType.PER_MINUTE)
        assert calc.config.rate_type == RateType.PER_MINUTE

    def test_create_throughput_meter(self):
        """Test create_throughput_meter."""
        meter = create_throughput_meter(20)
        assert meter.window_size == 20

    def test_create_latency_tracker(self):
        """Test create_latency_tracker."""
        tracker = create_latency_tracker(200)
        assert tracker.window_size == 200