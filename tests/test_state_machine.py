"""Tests for State Machine."""

import pytest
import asyncio

from cc.utils.state_machine import (
    StateType,
    TransitionType,
    State,
    Transition,
    StateConfig,
    StateHistoryEntry,
    StateMachine,
    create_machine,
)


class TestStateType:
    """Test StateType enum."""

    def test_all_types(self):
        """Test all state types."""
        assert StateType.INITIAL.value == "initial"
        assert StateType.NORMAL.value == "normal"
        assert StateType.FINAL.value == "final"
        assert StateType.ERROR.value == "error"


class TestTransitionType:
    """Test TransitionType enum."""

    def test_all_types(self):
        """Test all transition types."""
        assert TransitionType.NORMAL.value == "normal"
        assert TransitionType.TIMEOUT.value == "timeout"
        assert TransitionType.ERROR.value == "error"
        assert TransitionType.AUTO.value == "auto"


class TestState:
    """Test State."""

    def test_create(self):
        """Test creating state."""
        state = State(name="test")
        assert state.name == "test"
        assert state.type == StateType.NORMAL

    def test_with_transitions(self):
        """Test state with transitions."""
        state = State(
            name="test",
            transitions={"next": "target"},
        )
        assert state.transitions["next"] == "target"


class TestTransition:
    """Test Transition."""

    def test_create(self):
        """Test creating transition."""
        trans = Transition(
            from_state="a",
            to_state="b",
            event="move",
        )
        assert trans.from_state == "a"
        assert trans.to_state == "b"


class TestStateConfig:
    """Test StateConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = StateConfig()
        assert config.initial_state == "initial"
        assert config.allow_self_transitions is True

    def test_custom(self):
        """Test custom configuration."""
        config = StateConfig(
            initial_state="start",
            strict_transitions=True,
        )
        assert config.initial_state == "start"
        assert config.strict_transitions is True


class TestStateMachine:
    """Test StateMachine."""

    def test_init(self):
        """Test initialization."""
        machine = StateMachine()
        assert machine.config is not None
        assert len(machine._states) == 0

    def test_add_state(self):
        """Test adding state."""
        machine = StateMachine()
        state = machine.add_state("test")
        assert len(machine._states) == 1
        assert "test" in machine._states

    def test_add_transition(self):
        """Test adding transition."""
        machine = StateMachine()
        machine.add_state("a")
        machine.add_state("b")
        trans = machine.add_transition("a", "b", "next")
        assert trans.from_state == "a"

    def test_add_transition_invalid_from(self):
        """Test adding transition with invalid from state."""
        machine = StateMachine()
        machine.add_state("b")
        with pytest.raises(ValueError):
            machine.add_transition("a", "b", "next")

    def test_add_transition_invalid_to(self):
        """Test adding transition with invalid to state."""
        machine = StateMachine()
        machine.add_state("a")
        with pytest.raises(ValueError):
            machine.add_transition("a", "b", "next")

    def test_add_auto_transition(self):
        """Test adding auto transition."""
        machine = StateMachine()
        machine.add_state("a")
        machine.add_state("b")
        machine.add_auto_transition("a", "b")
        assert machine._states["a"].auto_transition == "b"

    def test_add_timeout(self):
        """Test adding timeout."""
        machine = StateMachine()
        machine.add_state("a")
        machine.add_state("b")
        machine.add_timeout("a", 5.0, "b")
        assert machine._states["a"].timeout == 5.0

    def test_start(self):
        """Test starting machine."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start()
        assert machine._current_state == "start"
        assert machine._running is True

    def test_start_invalid_initial(self):
        """Test starting with invalid initial state."""
        machine = StateMachine()
        machine.add_state("other")
        with pytest.raises(ValueError):
            machine.start()

    def test_stop(self):
        """Test stopping machine."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start()
        machine.stop()
        assert machine._running is False

    @pytest.mark.asyncio
    async def test_transition(self):
        """Test executing transition."""
        config = StateConfig(initial_state="a")
        machine = StateMachine(config)
        machine.add_state("a")
        machine.add_state("b")
        machine.add_transition("a", "b", "next")

        machine.start()
        result = await machine.transition("next")
        assert result is True
        assert machine._current_state == "b"

    @pytest.mark.asyncio
    async def test_transition_invalid_event(self):
        """Test transition with invalid event."""
        config = StateConfig(initial_state="a", strict_transitions=False)
        machine = StateMachine(config)
        machine.add_state("a")
        machine.add_state("b")
        machine.start()
        result = await machine.transition("invalid")
        assert result is False

    def test_can_transition(self):
        """Test checking if transition is possible."""
        config = StateConfig(initial_state="a")
        machine = StateMachine(config)
        machine.add_state("a")
        machine.add_state("b")
        machine.add_transition("a", "b", "next")
        machine.start()

        assert machine.can_transition("next") is True
        assert machine.can_transition("invalid") is False

    def test_get_current_state(self):
        """Test getting current state."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start()
        assert machine.get_current_state() == "start"

    def test_get_data(self):
        """Test getting data."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start(initial_data={"key": "value"})
        data = machine.get_data()
        assert data["key"] == "value"

    def test_set_data(self):
        """Test setting data."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start()
        machine.set_data("key", "value")
        assert machine._data["key"] == "value"

    def test_get_history(self):
        """Test getting history."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start()
        history = machine.get_history()
        assert len(history) == 0

    def test_get_available_events(self):
        """Test getting available events."""
        config = StateConfig(initial_state="a")
        machine = StateMachine(config)
        machine.add_state("a")
        machine.add_state("b")
        machine.add_transition("a", "b", "next")
        machine.start()

        events = machine.get_available_events()
        assert "next" in events

    def test_is_final(self):
        """Test checking final state."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.add_state("end", type=StateType.FINAL)
        machine.start()
        assert machine.is_final() is False

        machine._current_state = "end"
        assert machine.is_final() is True

    def test_is_error(self):
        """Test checking error state."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.add_state("error", type=StateType.ERROR)
        machine.start()
        assert machine.is_error() is False

        machine._current_state = "error"
        assert machine.is_error() is True

    def test_add_callback(self):
        """Test adding callback."""
        machine = StateMachine()
        callbacks = []

        def callback(data):
            callbacks.append(data)

        machine.add_callback("transition", callback)
        assert len(machine._callbacks["transition"]) == 1

    def test_reset(self):
        """Test resetting machine."""
        config = StateConfig(initial_state="start")
        machine = StateMachine(config)
        machine.add_state("start")
        machine.start()
        machine.reset()
        assert machine._current_state is None
        assert machine._running is False

    def test_visualize(self):
        """Test visualizing machine."""
        config = StateConfig(initial_state="a")
        machine = StateMachine(config)
        machine.add_state("a")
        machine.add_state("b")
        machine.add_transition("a", "b", "next")
        machine.start()

        output = machine.visualize()
        assert "a" in output
        assert "b" in output
        assert "next" in output


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_machine(self):
        """Test create_machine."""
        machine = create_machine(
            initial="start",
            states=["start", "middle", "end"],
            transitions=[
                ("start", "middle", "go"),
                ("middle", "end", "finish"),
            ],
        )
        assert len(machine._states) == 3
        assert "start" in machine._states
        assert "middle" in machine._states
        assert "end" in machine._states

    @pytest.mark.asyncio
    async def test_create_machine_and_run(self):
        """Test running created machine."""
        machine = create_machine(
            initial="a",
            states=["a", "b"],
            transitions=[("a", "b", "move")],
        )
        machine.start()
        await machine.transition("move")
        assert machine.get_current_state() == "b"