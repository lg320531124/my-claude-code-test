"""Tests for Timer Manager."""

import pytest
import asyncio
import time

from cc.utils.timer_manager import (
    TimerState,
    TimerInfo,
    TimerConfig,
    TimerManager,
    Stopwatch,
    Countdown,
    create_timer_manager,
    create_stopwatch,
    create_countdown,
)


class TestTimerState:
    """Test TimerState enum."""

    def test_all_states(self):
        """Test all timer states."""
        assert TimerState.STOPPED.value == "stopped"
        assert TimerState.RUNNING.value == "running"
        assert TimerState.PAUSED.value == "paused"
        assert TimerState.COMPLETED.value == "completed"
        assert TimerState.EXPIRED.value == "expired"


class TestTimerInfo:
    """Test TimerInfo."""

    def test_create(self):
        """Test creating timer info."""
        timer = TimerInfo(name="test", duration=10.0)
        assert timer.name == "test"
        assert timer.duration == 10.0
        assert timer.state == TimerState.STOPPED

    def test_progress(self):
        """Test progress calculation."""
        timer = TimerInfo(name="test", duration=10.0, elapsed=5.0)
        assert timer.progress == 50.0

        timer.elapsed = 10.0
        assert timer.progress == 100.0

    def test_progress_zero_duration(self):
        """Test progress with zero duration."""
        timer = TimerInfo(name="test", duration=0.0)
        assert timer.progress == 100.0


class TestTimerConfig:
    """Test TimerConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = TimerConfig()
        assert config.default_timeout == 30.0
        assert config.auto_cleanup is True
        assert config.max_timers == 100

    def test_custom(self):
        """Test custom configuration."""
        config = TimerConfig(
            default_timeout=60.0,
            max_timers=50,
        )
        assert config.default_timeout == 60.0
        assert config.max_timers == 50


class TestTimerManager:
    """Test TimerManager."""

    def test_init(self):
        """Test initialization."""
        manager = TimerManager()
        assert manager.config is not None
        assert len(manager._timers) == 0

    def test_create_timer(self):
        """Test creating timer."""
        manager = TimerManager()
        timer = manager.create_timer("test", 10.0)
        assert len(manager._timers) == 1
        assert timer.name == "test"

    @pytest.mark.asyncio
    async def test_start_timer(self):
        """Test starting timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        result = manager.start_timer("test")
        assert result is True
        timer = manager.get_timer("test")
        assert timer.state == TimerState.RUNNING

    def test_start_timer_nonexistent(self):
        """Test starting nonexistent timer."""
        manager = TimerManager()
        result = manager.start_timer("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_timer(self):
        """Test stopping timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.start_timer("test")
        timer = manager.stop_timer("test")
        assert timer.state == TimerState.STOPPED

    def test_stop_timer_nonexistent(self):
        """Test stopping nonexistent timer."""
        manager = TimerManager()
        with pytest.raises(ValueError):
            manager.stop_timer("test")

    @pytest.mark.asyncio
    async def test_pause_timer(self):
        """Test pausing timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.start_timer("test")
        result = manager.pause_timer("test")
        assert result is True
        timer = manager.get_timer("test")
        assert timer.state == TimerState.PAUSED

    def test_pause_timer_nonexistent(self):
        """Test pausing nonexistent timer."""
        manager = TimerManager()
        result = manager.pause_timer("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_timer(self):
        """Test resuming timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.start_timer("test")
        manager.pause_timer("test")
        result = manager.resume_timer("test")
        assert result is True
        timer = manager.get_timer("test")
        assert timer.state == TimerState.RUNNING

    @pytest.mark.asyncio
    async def test_reset_timer(self):
        """Test resetting timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.start_timer("test")
        timer = manager.reset_timer("test")
        assert timer.state == TimerState.STOPPED
        assert timer.elapsed == 0.0

    def test_delete_timer(self):
        """Test deleting timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.delete_timer("test")
        assert len(manager._timers) == 0

    def test_get_timer(self):
        """Test getting timer."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        timer = manager.get_timer("test")
        assert timer is not None
        assert timer.name == "test"

    def test_get_timer_nonexistent(self):
        """Test getting nonexistent timer."""
        manager = TimerManager()
        timer = manager.get_timer("test")
        assert timer is None

    def test_get_all_timers(self):
        """Test getting all timers."""
        manager = TimerManager()
        manager.create_timer("test1", 10.0)
        manager.create_timer("test2", 20.0)
        timers = manager.get_all_timers()
        assert len(timers) == 2

    @pytest.mark.asyncio
    async def test_get_running_timers(self):
        """Test getting running timers."""
        manager = TimerManager()
        manager.create_timer("test1", 10.0)
        manager.create_timer("test2", 20.0)
        manager.start_timer("test1")
        running = manager.get_running_timers()
        assert len(running) == 1

    @pytest.mark.asyncio
    async def test_get_elapsed(self):
        """Test getting elapsed time."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.start_timer("test")
        elapsed = manager.get_elapsed("test")
        assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_get_remaining(self):
        """Test getting remaining time."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        manager.start_timer("test")
        remaining = manager.get_remaining("test")
        assert remaining > 0
        assert remaining <= 10.0

    def test_is_expired(self):
        """Test checking if expired."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        assert manager.is_expired("test") is False

        timer = manager.get_timer("test")
        timer.state = TimerState.EXPIRED
        assert manager.is_expired("test") is True

    @pytest.mark.asyncio
    async def test_is_running(self):
        """Test checking if running."""
        manager = TimerManager()
        manager.create_timer("test", 10.0)
        assert manager.is_running("test") is False

        manager.start_timer("test")
        assert manager.is_running("test") is True

    @pytest.mark.asyncio
    async def test_wait_for_timer(self):
        """Test waiting for timer."""
        manager = TimerManager()
        manager.create_timer("test", 0.1)
        manager.start_timer("test")
        timer = await manager.wait_for_timer("test")
        assert timer.state == TimerState.EXPIRED


class TestStopwatch:
    """Test Stopwatch."""

    def test_init(self):
        """Test initialization."""
        watch = Stopwatch("test")
        assert watch.name == "test"

    def test_start(self):
        """Test starting."""
        watch = Stopwatch()
        watch.start()
        assert watch._start_time is not None

    def test_stop(self):
        """Test stopping."""
        watch = Stopwatch()
        watch.start()
        elapsed = watch.stop()
        assert elapsed >= 0
        assert watch._stop_time is not None

    def test_reset(self):
        """Test resetting."""
        watch = Stopwatch()
        watch.start()
        watch.stop()
        watch.reset()
        assert watch._elapsed == 0.0
        assert watch._start_time is None

    def test_lap(self):
        """Test lap recording."""
        watch = Stopwatch()
        watch.start()
        time.sleep(0.01)
        lap_time = watch.lap()
        assert lap_time >= 0
        assert len(watch._lap_times) == 1

    def test_get_elapsed(self):
        """Test getting elapsed."""
        watch = Stopwatch()
        watch.start()
        elapsed = watch.get_elapsed()
        assert elapsed >= 0

    def test_get_laps(self):
        """Test getting lap times."""
        watch = Stopwatch()
        watch.start()
        watch.lap()
        watch.lap()
        laps = watch.get_laps()
        assert len(laps) == 2


class TestCountdown:
    """Test Countdown."""

    def test_init(self):
        """Test initialization."""
        countdown = Countdown(10.0)
        assert countdown.duration == 10.0

    def test_start(self):
        """Test starting."""
        countdown = Countdown(10.0)
        countdown.start()
        assert countdown._running is True

    def test_stop(self):
        """Test stopping."""
        countdown = Countdown(10.0)
        countdown.start()
        remaining = countdown.stop()
        assert remaining >= 0
        assert countdown._running is False

    def test_reset(self):
        """Test resetting."""
        countdown = Countdown(10.0)
        countdown.start()
        countdown.reset()
        assert countdown._remaining == 10.0
        assert countdown._running is False

    def test_get_remaining(self):
        """Test getting remaining."""
        countdown = Countdown(10.0)
        countdown.start()
        remaining = countdown.get_remaining()
        assert remaining > 0
        assert remaining <= 10.0

    def test_is_expired(self):
        """Test checking if expired."""
        countdown = Countdown(0.0)
        countdown.start()
        assert countdown.is_expired() is True


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_timer_manager(self):
        """Test create_timer_manager."""
        manager = create_timer_manager(50)
        assert manager.config.max_timers == 50

    def test_create_stopwatch(self):
        """Test create_stopwatch."""
        watch = create_stopwatch("test")
        assert watch.name == "test"

    def test_create_countdown(self):
        """Test create_countdown."""
        countdown = create_countdown(10.0)
        assert countdown.duration == 10.0