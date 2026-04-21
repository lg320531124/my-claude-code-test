"""AskUserQuestionTool - Interactive user questions."""

from __future__ import annotations
from typing import List, Optional, ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class QuestionOption(ToolInput):
    """Option for a question."""

    label: str
    description: Optional[str] = None


class Question(ToolInput):
    """A single question."""

    question: str
    header: str = "Question"
    options: Optional[List[QuestionOption]] = None
    multiSelect: bool = False


class AskUserQuestionInput(ToolInput):
    """Input for AskUserQuestionTool."""

    questions: List[Question]


class AskUserQuestionTool(ToolDef):
    """Ask user questions during execution."""

    name: ClassVar[str] = "AskUserQuestion"
    description: ClassVar[str] = "Ask user questions to clarify requirements or get decisions"
    input_schema: ClassVar[type] = AskUserQuestionInput

    async def execute(self, input: AskUserQuestionInput, ctx: ToolUseContext) -> ToolResult:
        """Execute the question tool."""
        from rich.console import Console
        from rich.prompt import Prompt
        from rich.table import Table

        console = Console()
        answers = {}

        for q in input.questions:
            console.print(f"\n[bold cyan]{q.header}[/bold cyan]")
            console.print(f"[bold]{q.question}[/bold]")

            if q.options:
                # Show options
                table = Table(show_header=False)
                table.add_column("Key", style="cyan")
                table.add_column("Option")
                table.add_column("Description", style="dim")

                for i, opt in enumerate(q.options):
                    key = str(i + 1)
                    table.add_row(key, opt.label, opt.description or "")

                console.print(table)

                # Get answer
                if q.multiSelect:
                    console.print("[dim]Enter multiple numbers separated by comma[/dim]")
                    response = Prompt.ask("Select")
                    selected = [int(x.strip()) - 1 for x in response.split(",")]
                    answers[q.question] = [
                        q.options[i].label if 0 <= i < len(q.options) else "Unknown"
                        for i in selected
                    ]
                else:
                    response = Prompt.ask("Select", choices=[str(i + 1) for i in range(len(q.options))])
                    idx = int(response) - 1
                    answers[q.question] = q.options[idx].label if 0 <= idx < len(q.options) else "Unknown"
            else:
                # Free text
                response = Prompt.ask("Answer")
                answers[q.question] = response

        import json
        return ToolResult(
            content=json.dumps(answers, indent=2),
            metadata={"questions_asked": len(input.questions)},
        )
