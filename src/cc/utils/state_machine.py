"""State Machine - State machine implementation for complex workflows."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class StateType(Enum):
    """State types."""
    INITIAL = "initial"
    NORMAL = "normal"
    FINAL = "final"
    ERROR = "error"


class TransitionType(Enum):
    """Transition types."""
    NORMAL = "normal"
    TIMEOUT = "timeout"
    ERROR = "error"
    AUTO = "auto"


@dataclass
class State:
    """A state in the machine."""
    name: str
    type: StateType = StateType.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None
    transitions: Dict[str, str] = field(default_factory=dict)  # event -> target_state
    auto_transition: Optional[str] = None  # Auto transition target
    timeout: Optional[float] = None  # Timeout in seconds
    timeout_transition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transition:
    """A transition between states."""
    from_state: str
    to_state: str
    event: str
    type: TransitionType = TransitionType.NORMAL
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    action: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateConfig:
    """State machine configuration."""
    initial_state: str = "initial"
    allow_self_transitions: bool = True
    strict_transitions: bool = False
    log_transitions: bool = True
    max_history: int = 100


@dataclass
class StateHistoryEntry:
    """History entry."""
    from_state: str
    to_state: str
    event: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)


class StateMachine:
    """State machine for managing complex workflows."""

    def __init__(self, config: Optional[StateConfig] = None):
        self.config = config or StateConfig()
        self._states: Dict[str, State] = {}
        self._current_state: Optional[str] = None
        self._data: Dict[str, Any] = {}
        self._history: List[StateHistoryEntry] = []
        self._callbacks: Dict[str, List[Callable]] = {}
        self._timeout_task: Optional[asyncio.Task] = None
        self._running = False

    def add_state(
        self,
        name: str,
        type: StateType = StateType.NORMAL,
        on_enter: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
        **metadata,
    ) -> State:
        """Add a state."""
        state = State(
            name=name,
            type=type,
            on_enter=on_enter,
            on_exit=on_exit,
            metadata=metadata,
        )
        self._states[name] = state
        return state

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        event: str,
        condition: Optional[Callable] = None,
        action: Optional[Callable] = None,
    ) -> Transition:
        """Add a transition."""
        if from_state not in self._states:
            raise ValueError(f"State '{from_state}' not found")
        if to_state not in self._states:
            raise ValueError(f"State '{to_state}' not found")

        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            event=event,
            condition=condition,
            action=action,
        )

        self._states[from_state].transitions[event] = to_state
        return transition

    def add_auto_transition(self, from_state: str, to_state: str) -> None:
        """Add auto transition."""
        if from_state in self._states:
            self._states[from_state].auto_transition = to_state

    def add_timeout(
        self,
        state: str,
        timeout: float,
        target: str,
    ) -> None:
        """Add timeout transition."""
        if state in self._states:
            self._states[state].timeout = timeout
            self._states[state].timeout_transition = target

    def start(self, initial_data: Optional[Dict[str, Any]] = None) -> None:
        """Start the state machine."""
        if not self._states:
            raise ValueError("No states defined")

        initial_state = self.config.initial_state
        if initial_state not in self._states:
            raise ValueError(f"Initial state '{initial_state}' not found")

        self._data = initial_data or {}
        self._current_state = initial_state
        self._running = True

        # Execute on_enter for initial state
        state = self._states[initial_state]
        if state.on_enter:
            state.on_enter(self._data)

        # Start timeout timer if needed
        self._start_timeout_timer()

    def stop(self) -> None:
        """Stop the state machine."""
        self._running = False
        self._cancel_timeout_timer()

    async def transition(self, event: str) -> bool:
        """Execute a transition."""
        if not self._running or self._current_state is None:
            return False

        current = self._states[self._current_state]

        # Check if event is valid
        if event not in current.transitions:
            if self.config.strict_transitions:
                raise ValueError(f"Event '{event}' not valid for state '{self._current_state}'")
            return False

        target = current.transitions[event]

        # Check self transition
        if target == self._current_state and not self.config.allow_self_transitions:
            return False

        # Execute transition
        return await self._execute_transition(target, event)

    async def _execute_transition(self, target: str, event: str) -> bool:
        """Execute transition to target state."""
        import time

        current_name = self._current_state
        current = self._states[current_name]
        target_state = self._states[target]

        # Execute on_exit for current state
        if current.on_exit:
            if asyncio.iscoroutinefunction(current.on_exit):
                await current.on_exit(self._data)
            else:
                current.on_exit(self._data)

        # Record history
        entry = StateHistoryEntry(
            from_state=current_name,
            to_state=target,
            event=event,
            timestamp=time.time(),
            data=self._data.copy(),
        )
        self._history.append(entry)
        if len(self._history) > self.config.max_history:
            self._history.pop(0)

        # Update state
        self._current_state = target

        # Execute on_enter for new state
        if target_state.on_enter:
            if asyncio.iscoroutinefunction(target_state.on_enter):
                await target_state.on_enter(self._data)
            else:
                target_state.on_enter(self._data)

        # Notify callbacks
        self._notify_callbacks("transition", {
            "from": current_name,
            "to": target,
            "event": event,
        })

        # Handle auto transition
        if target_state.auto_transition:
            await self._execute_transition(target_state.auto_transition, "auto")

        # Start timeout timer
        self._start_timeout_timer()

        return True

    def _start_timeout_timer(self) -> None:
        """Start timeout timer for current state."""
        self._cancel_timeout_timer()

        if self._current_state is None:
            return

        state = self._states[self._current_state]
        if state.timeout and state.timeout_transition:
            self._timeout_task = asyncio.create_task(
                self._timeout_handler(state.timeout, state.timeout_transition)
            )

    def _cancel_timeout_timer(self) -> None:
        """Cancel timeout timer."""
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

    async def _timeout_handler(self, timeout: float, target: str) -> None:
        """Handle timeout."""
        await asyncio.sleep(timeout)
        await self._execute_transition(target, "timeout")

    def can_transition(self, event: str) -> bool:
        """Check if transition is possible."""
        if not self._running or self._current_state is None:
            return False

        current = self._states[self._current_state]
        return event in current.transitions

    def get_current_state(self) -> Optional[str]:
        """Get current state name."""
        return self._current_state

    def get_state_data(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get state data."""
        state_name = name or self._current_state
        if state_name and state_name in self._states:
            return self._states[state_name].data
        return {}

    def get_data(self) -> Dict[str, Any]:
        """Get machine data."""
        return self._data.copy()

    def set_data(self, key: str, value: Any) -> None:
        """Set machine data."""
        self._data[key] = value

    def get_history(self) -> List[StateHistoryEntry]:
        """Get transition history."""
        return self._history.copy()

    def get_available_events(self) -> List[str]:
        """Get available events for current state."""
        if not self._current_state:
            return []

        state = self._states[self._current_state]
        return list(state.transitions.keys())

    def is_final(self) -> bool:
        """Check if in final state."""
        if not self._current_state:
            return False

        state = self._states[self._current_state]
        return state.type == StateType.FINAL

    def is_error(self) -> bool:
        """Check if in error state."""
        if not self._current_state:
            return False

        state = self._states[self._current_state]
        return state.type == StateType.ERROR

    def add_callback(self, event: str, callback: Callable) -> None:
        """Add callback for events."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def remove_callback(self, event: str, callback: Callable) -> None:
        """Remove callback."""
        if event in self._callbacks:
            if callback in self._callbacks[event]:
                self._callbacks[event].remove(callback)

    def _notify_callbacks(self, event: str, data: Dict[str, Any]) -> None:
        """Notify callbacks."""
        callbacks = self._callbacks.get(event, [])
        for callback in callbacks:
            callback(data)

    def reset(self) -> None:
        """Reset to initial state."""
        self._cancel_timeout_timer()
        self._current_state = None
        self._data = {}
        self._history = []
        self._running = False

    def visualize(self) -> str:
        """Visualize state machine as text."""
        lines = ["State Machine:"]
        for name, state in self._states.items():
            state_type = state.type.value
            current_marker = " (*)" if name == self._current_state else ""
            lines.append(f"  [{state_type}] {name}{current_marker}")

            for event, target in state.transitions.items():
                lines.append(f"    {event} -> {target}")

        return "\n".join(lines)


def create_machine(
    initial: str,
    states: Optional[List[str]] = None,
    transitions: Optional[List[Tuple[str, str, str]]] = None,
) -> StateMachine:
    """Create a simple state machine."""
    config = StateConfig(initial_state=initial)
    machine = StateMachine(config)

    # Add states
    if states:
        for state_name in states:
            machine.add_state(state_name)

    # Add transitions
    if transitions:
        for from_state, to_state, event in transitions:
            machine.add_transition(from_state, to_state, event)

    return machine


__all__ = [
    "StateType",
    "TransitionType",
    "State",
    "Transition",
    "StateConfig",
    "StateHistoryEntry",
    "StateMachine",
    "create_machine",
]