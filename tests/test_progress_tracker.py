"""Tests for Progress Tracker."""

import pytest
import time

from cc.utils.progress_tracker import (
    ProgressState,
    ProgressStep,
    ProgressConfig,
    ProgressResult,
    ProgressTracker,
    create_tracker,
    track_steps,
)


class TestProgressState:
    """Test ProgressState enum."""

    def test_all_states(self):
        """Test all progress states."""
        assert ProgressState.PENDING.value == "pending"
        assert ProgressState.RUNNING.value == "running"
        assert ProgressState.COMPLETED.value == "completed"
        assert ProgressState.FAILED.value == "failed"
        assert ProgressState.CANCELLED.value == "cancelled"
        assert ProgressState.PAUSED.value == "paused"


class TestProgressStep:
    """Test ProgressStep."""

    def test_create(self):
        """Test creating step."""
        step = ProgressStep(name="test")
        assert step.name == "test"
        assert step.state == ProgressState.PENDING
        assert step.progress == 0.0

    def test_duration_not_started(self):
        """Test duration when not started."""
        step = ProgressStep(name="test")
        assert step.duration() is None

    def test_duration_running(self):
        """Test duration when running."""
        step = ProgressStep(name="test")
        step.start_time = time.time()
        duration = step.duration()
        assert duration is not None
        assert duration >= 0

    def test_duration_completed(self):
        """Test duration when completed."""
        step = ProgressStep(name="test")
        step.start_time = time.time()
        step.end_time = time.time() + 1.0
        assert step.duration() == 1.0

    def test_is_complete(self):
        """Test is_complete."""
        step = ProgressStep(name="test")
        assert step.is_complete() is False

        step.state = ProgressState.COMPLETED
        assert step.is_complete() is True

        step.state = ProgressState.FAILED
        assert step.is_complete() is True


class TestProgressConfig:
    """Test ProgressConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = ProgressConfig()
        assert config.name == "Task"
        assert config.auto_estimate is True

    def test_custom(self):
        """Test custom configuration."""
        config = ProgressConfig(name="MyTask", total_steps=5)
        assert config.name == "MyTask"
        assert config.total_steps == 5


class TestProgressResult:
    """Test ProgressResult."""

    def test_create(self):
        """Test creating result."""
        result = ProgressResult(
            name="test",
            state=ProgressState.RUNNING,
            total_progress=50.0,
            steps_completed=1,
            steps_total=2,
            duration=10.0,
        )
        assert result.name == "test"
        assert result.total_progress == 50.0


class TestProgressTracker:
    """Test ProgressTracker."""

    def test_init(self):
        """Test initialization."""
        tracker = ProgressTracker()
        assert tracker.config is not None
        assert tracker._state == ProgressState.PENDING

    def test_start(self):
        """Test starting."""
        tracker = ProgressTracker()
        tracker.start()
        assert tracker._state == ProgressState.RUNNING
        assert tracker._start_time is not None

    def test_add_step(self):
        """Test adding step."""
        tracker = ProgressTracker()
        step = tracker.add_step("step1", "First step")
        assert len(tracker._steps) == 1
        assert step.name == "step1"

    def test_begin_step(self):
        """Test beginning step."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")
        tracker.start()

        step = tracker.begin_step()
        assert step.state == ProgressState.RUNNING
        assert step.start_time is not None

    def test_update_step(self):
        """Test updating step."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.start()
        tracker.begin_step()

        tracker.update_step(50.0)
        assert tracker._steps[0].progress == 50.0

    def test_complete_step(self):
        """Test completing step."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.start()
        tracker.begin_step()

        step = tracker.complete_step()
        assert step.state == ProgressState.COMPLETED
        assert step.progress == 100.0
        assert tracker._current_step == 1

    def test_complete_step_with_error(self):
        """Test completing step with error."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.start()
        tracker.begin_step()

        step = tracker.complete_step(error="Something failed")
        assert step.state == ProgressState.FAILED
        assert step.error == "Something failed"

    def test_fail(self):
        """Test failing progress."""
        tracker = ProgressTracker()
        tracker.start()
        tracker.fail("Fatal error")

        assert tracker._state == ProgressState.FAILED
        assert tracker._error == "Fatal error"

    def test_complete(self):
        """Test completing progress."""
        tracker = ProgressTracker()
        tracker.start()
        tracker.complete()

        assert tracker._state == ProgressState.COMPLETED

    def test_cancel(self):
        """Test cancelling progress."""
        tracker = ProgressTracker()
        tracker.start()
        tracker.cancel()

        assert tracker._state == ProgressState.CANCELLED

    def test_pause_resume(self):
        """Test pause and resume."""
        tracker = ProgressTracker()
        tracker.start()
        tracker.pause()

        assert tracker._state == ProgressState.PAUSED

        tracker.resume()
        assert tracker._state == ProgressState.RUNNING

    def test_get_progress(self):
        """Test getting progress."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")

        tracker._steps[0].progress = 50.0
        tracker._steps[1].progress = 25.0

        progress = tracker.get_progress()
        assert progress == 37.5

    def test_get_progress_empty(self):
        """Test getting progress with no steps."""
        tracker = ProgressTracker()
        assert tracker.get_progress() == 0.0

    def test_get_result(self):
        """Test getting result."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")
        tracker.start()

        tracker._steps[0].state = ProgressState.COMPLETED

        result = tracker.get_result()
        assert result.steps_completed == 1
        assert result.steps_total == 2

    def test_get_steps(self):
        """Test getting steps."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")

        steps = tracker.get_steps()
        assert len(steps) == 2

    def test_get_current_step(self):
        """Test getting current step."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")
        tracker.start()

        tracker.begin_step()
        current = tracker.get_current_step()
        assert current.name == "step1"

        tracker.complete_step()
        current = tracker.get_current_step()
        assert current.name == "step2"

    def test_callback(self):
        """Test callback."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.start()

        callbacks = []

        def callback(result):
            callbacks.append(result)

        tracker.add_callback(callback)
        tracker.complete()

        assert len(callbacks) == 1
        assert callbacks[0].state == ProgressState.COMPLETED

    def test_format_progress(self):
        """Test formatting progress."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")
        tracker.start()

        tracker._steps[0].progress = 50.0
        tracker._steps[1].progress = 50.0

        formatted = tracker.format_progress()
        assert "running" in formatted.lower()
        assert "50.0%" in formatted

    def test_format_steps(self):
        """Test formatting steps."""
        tracker = ProgressTracker()
        tracker.add_step("step1", "First")
        tracker.add_step("step2", "Second")

        formatted = tracker.format_steps()
        assert "step1" in formatted
        assert "step2" in formatted

    def test_estimate_remaining(self):
        """Test estimating remaining time."""
        tracker = ProgressTracker()
        tracker.add_step("step1")
        tracker.add_step("step2")
        tracker.add_step("step3")
        tracker.start()

        # Complete two steps with known durations
        tracker.begin_step()
        tracker._steps[0].start_time = time.time()
        tracker._steps[0].end_time = time.time() + 1.0
        tracker._steps[0].state = ProgressState.COMPLETED
        tracker._current_step = 1

        tracker.begin_step()
        tracker._steps[1].start_time = time.time()
        tracker._steps[1].end_time = time.time() + 1.0
        tracker._steps[1].state = ProgressState.COMPLETED
        tracker._current_step = 2

        estimate = tracker.estimate_remaining()
        assert estimate is not None
        assert estimate >= 0

    def test_estimate_remaining_insufficient(self):
        """Test estimating with insufficient data."""
        tracker = ProgressTracker()
        tracker.add_step("step1")

        estimate = tracker.estimate_remaining()
        assert estimate is None


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_tracker(self):
        """Test create_tracker."""
        tracker = create_tracker("MyTask", total_steps=5)
        assert tracker.config.name == "MyTask"
        assert tracker.config.total_steps == 5

    def test_track_steps(self):
        """Test track_steps."""
        tracker = track_steps(["step1", "step2", "step3"])
        assert len(tracker._steps) == 3
        assert tracker._steps[0].name == "step1"

    def test_track_steps_with_callback(self):
        """Test track_steps with callback."""
        callbacks = []

        def callback(result):
            callbacks.append(result)

        tracker = track_steps(["step1"], callback=callback)
        tracker.start()
        tracker.complete()

        assert len(callbacks) == 1