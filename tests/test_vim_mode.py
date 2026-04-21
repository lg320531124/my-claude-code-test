"""Test Vim mode implementation."""

from __future__ import annotations
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc.ui.vim_mode import VimMode, VimState, VimModeHandler, NormalMode, InsertMode
from cc.ui.vim_mode.motions import VimMotions, MotionType
from cc.ui.vim_mode.text_objects import VimTextObjects, TextObjectKind


class TestVimModes:
    """Test Vim mode transitions."""

    def test_mode_enum(self):
        """Test mode enum."""
        assert VimMode.NORMAL.value == "normal"
        assert VimMode.INSERT.value == "insert"
        assert VimMode.VISUAL.value == "visual"

    def test_state_defaults(self):
        """Test state defaults."""
        state = VimState()
        assert state.mode == VimMode.NORMAL
        assert state.cursor_line == 0
        assert state.cursor_col == 0

    def test_mode_handler(self):
        """Test mode handler."""
        handler = VimModeHandler()
        handler.set_mode(VimMode.INSERT)

        assert handler.get_state().mode == VimMode.INSERT


class TestNormalMode:
    """Test normal mode handler."""

    def test_mode_switch_to_insert(self):
        """Test switching to insert mode."""
        normal = NormalMode()
        state = VimState()

        result = normal.handle("i", state)
        assert result is not None
        assert result.mode_change == VimMode.INSERT

    def test_mode_switch_to_visual(self):
        """Test switching to visual mode."""
        normal = NormalMode()
        state = VimState()

        result = normal.handle("v", state)
        assert result is not None
        assert result.mode_change == VimMode.VISUAL

    def test_count_prefix(self):
        """Test count prefix."""
        normal = NormalMode()
        state = VimState()

        normal.handle("3", state)
        assert state.count == 3

        normal.handle("0", state)
        assert state.count == 30  # 3 * 10 + 0

    def test_motion_command(self):
        """Test motion command."""
        normal = NormalMode()
        state = VimState()

        result = normal.handle("w", state)
        assert result is not None
        assert result.action == "move_w"

    def test_operator_pending(self):
        """Test operator pending state."""
        normal = NormalMode()
        state = VimState()

        result = normal.handle("d", state)
        assert result is None  # Pending
        assert state.pending_operator == "d"


class TestInsertMode:
    """Test insert mode handler."""

    def test_exit_on_escape(self):
        """Test exit on escape."""
        insert = InsertMode()
        state = VimState(mode=VimMode.INSERT)

        result = insert.handle("escape", state)
        assert result is not None
        assert result.mode_change == VimMode.NORMAL

    def test_character_insert(self):
        """Test character insertion."""
        insert = InsertMode()
        state = VimState(mode=VimMode.INSERT)

        result = insert.handle("a", state)
        assert result is not None
        assert result.action == "insert_char"
        assert result.text == "a"


class TestVimMotions:
    """Test Vim motions."""

    def test_motion_h(self):
        """Test h motion (left)."""
        motions = VimMotions()
        state = {"line": 0, "col": 5, "line_text": "hello world"}

        result = motions.execute("h", state)
        assert result.col == 4

    def test_motion_l(self):
        """Test l motion (right)."""
        motions = VimMotions()
        state = {"line": 0, "col": 0, "line_text": "hello"}

        result = motions.execute("l", state)
        assert result.col == 1

    def test_motion_w(self):
        """Test w motion (word forward)."""
        motions = VimMotions()
        state = {"line": 0, "col": 0, "line_text": "hello world"}

        result = motions.execute("w", state)
        assert result.col == 6  # Skip to "world"

    def test_motion_0(self):
        """Test 0 motion (line start)."""
        motions = VimMotions()
        state = {"line": 0, "col": 5, "line_text": "hello"}

        result = motions.execute("0", state)
        assert result.col == 0

    def test_motion_dollar(self):
        """Test $ motion (line end)."""
        motions = VimMotions()
        state = {"line": 0, "col": 0, "line_text": "hello"}

        result = motions.execute("$", state)
        assert result.col == 4  # Last char index


class TestTextObjects:
    """Test text objects."""

    def test_word_object(self):
        """Test word object."""
        objects = VimTextObjects()
        text = "hello world"
        position = 0  # 'h' position

        result = objects.get_object("aw", text, position)
        assert result is not None
        assert result.kind == TextObjectKind.WORD
        assert "hello" in result.content

    def test_inner_word(self):
        """Test inner word."""
        objects = VimTextObjects()
        text = "hello world"
        position = 0

        result = objects.get_object("iw", text, position)
        assert result is not None
        assert result.start == 0
        assert result.end == 5

    def test_block_paren(self):
        """Test parentheses block."""
        objects = VimTextObjects()
        text = "(hello world)"
        position = 1  # Inside parens

        result = objects.get_object("a(", text, position)
        assert result is not None
        assert result.kind == TextObjectKind.BLOCK

    def test_quote_object(self):
        """Test quote object."""
        objects = VimTextObjects()
        text = "say 'hello'"
        position = 5  # Inside quote

        result = objects.get_object("i'", text, position)
        assert result is not None
        assert result.kind == TextObjectKind.QUOTE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
