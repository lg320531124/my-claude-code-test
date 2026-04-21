"""Enhanced Context System - Complete async context collection."""

from __future__ import annotations
import asyncio
import json
import os
import platform
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class EnvironmentInfo:
    """Environment information."""
    python_version: str
    platform: str
    os_name: str
    architecture: str
    cwd: str
    home: str
    shell: Optional[str] = None
    editor: Optional[str] = None
    terminal: Optional[str] = None


@dataclass
class GitInfo:
    """Git repository information."""
    in_repo: bool = False
    branch: Optional[str] = None
    remote: Optional[str] = None
    remote_name: Optional[str] = None
    status: Optional[str] = None
    staged_files: List[str] = field(default_factory=list)
    unstaged_files: List[str] = field(default_factory=list)
    recent_commits: List[str] = field(default_factory=list)
    ahead_behind: tuple[int, int] = (0, 0)
    stash_count: int = 0
    last_commit_hash: Optional[str] = None
    last_commit_time: Optional[float] = None


@dataclass
class ProjectInfo:
    """Project information."""
    type: str = "unknown"
    name: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    source_dirs: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    version: Optional[str] = None


@dataclass
class ContextInfo:
    """Complete context information."""
    environment: EnvironmentInfo
    git: GitInfo
    project: ProjectInfo
    cwd: Optional[Path] = None
    timestamp: float = field(default_factory=time.time)


async def run_command_async(cmd: List[str], cwd: Path, timeout: float = 5.0) -> tuple[str, str, int]:
    """Run command asynchronously."""
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=timeout,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode(), stderr.decode(), proc.returncode
    except asyncio.TimeoutError:
        return "", "Timeout", -1
    except Exception:
        return "", "Error", -1


class AsyncContextCollector:
    """Async context collector."""

    def __init__(self, cwd: Path):
        self.cwd = cwd

    async def collect_all(self) -> ContextInfo:
        """Collect all context asynchronously."""
        # Run all collection tasks in parallel
        env_task = asyncio.create_task(self._collect_environment())
        git_task = asyncio.create_task(self._collect_git())
        project_task = asyncio.create_task(self._collect_project())

        env, git, project = await asyncio.gather(env_task, git_task, project_task)

        return ContextInfo(
            environment=env,
            git=git,
            project=project,
        )

    async def _collect_environment(self) -> EnvironmentInfo:
        """Collect environment info."""
        return EnvironmentInfo(
            python_version=platform.python_version(),
            platform=platform.platform(),
            os_name=platform.system(),
            architecture=platform.machine(),
            cwd=str(self.cwd),
            home=str(Path.home()),
            shell=os.environ.get("SHELL"),
            editor=os.environ.get("EDITOR") or os.environ.get("VISUAL"),
            terminal=os.environ.get("TERM"),
        )

    async def _collect_git(self) -> GitInfo:
        """Collect git info asynchronously."""
        info = GitInfo()

        # Check if in repo
        stdout, _, code = await run_command_async(
            ["git", "rev-parse", "--git-dir"],
            self.cwd,
        )
        if code != 0:
            return info

        info.in_repo = True

        # Collect in parallel
        branch_task = asyncio.create_task(self._get_branch())
        remote_task = asyncio.create_task(self._get_remote())
        status_task = asyncio.create_task(self._get_status())
        commits_task = asyncio.create_task(self._get_recent_commits())
        ahead_task = asyncio.create_task(self._get_ahead_behind())
        stash_task = asyncio.create_task(self._get_stash_count())
        last_commit_task = asyncio.create_task(self._get_last_commit())

        results = await asyncio.gather(
            branch_task, remote_task, status_task,
            commits_task, ahead_task, stash_task, last_commit_task,
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            if i == 0:
                info.branch = result
            elif i == 1:
                info.remote = result.get("url")
                info.remote_name = result.get("name")
            elif i == 2:
                info.status = result.get("status")
                info.staged_files = result.get("staged", [])
                info.unstaged_files = result.get("unstaged", [])
            elif i == 3:
                info.recent_commits = result
            elif i == 4:
                info.ahead_behind = result
            elif i == 5:
                info.stash_count = result
            elif i == 6:
                info.last_commit_hash = result.get("hash")
                info.last_commit_time = result.get("time")

        return info

    async def _get_branch(self) -> Optional[str]:
        """Get current branch."""
        stdout, _, code = await run_command_async(
            ["git", "branch", "--show-current"],
            self.cwd,
        )
        return stdout.strip() if code == 0 else None

    async def _get_remote(self) -> dict:
        """Get remote info."""
        stdout, _, code = await run_command_async(
            ["git", "remote", "get-url", "origin"],
            self.cwd,
        )
        if code == 0:
            return {"name": "origin", "url": stdout.strip()}
        return {}

    async def _get_status(self) -> dict:
        """Get status info."""
        # Short status
        stdout, _, _ = await run_command_async(
            ["git", "status", "--short"],
            self.cwd,
        )
        status = stdout.strip()

        # Staged files
        stdout2, _, _ = await run_command_async(
            ["git", "diff", "--cached", "--name-only"],
            self.cwd,
        )
        staged = stdout2.strip().split("\n") if stdout2.strip() else []

        # Unstaged files
        stdout3, _, _ = await run_command_async(
            ["git", "diff", "--name-only"],
            self.cwd,
        )
        unstaged = stdout3.strip().split("\n") if stdout3.strip() else []

        return {
            "status": status,
            "staged": staged,
            "unstaged": unstaged,
        }

    async def _get_recent_commits(self, limit: int = 5) -> List[str]:
        """Get recent commits."""
        stdout, _, code = await run_command_async(
            ["git", "log", f"-{limit}", "--oneline"],
            self.cwd,
        )
        if code == 0:
            return stdout.strip().split("\n")
        return []

    async def _get_ahead_behind(self) -> tuple[int, int]:
        """Get ahead/behind count."""
        stdout, _, code = await run_command_async(
            ["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"],
            self.cwd,
        )
        if code == 0 and stdout.strip():
            parts = stdout.strip().split()
            return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        return (0, 0)

    async def _get_stash_count(self) -> int:
        """Get stash count."""
        stdout, _, code = await run_command_async(
            ["git", "stash", "list"],
            self.cwd,
        )
        return len(stdout.strip().split("\n")) if stdout.strip() else 0

    async def _get_last_commit(self) -> dict:
        """Get last commit info."""
        stdout, _, code = await run_command_async(
            ["git", "log", "-1", "--format=%H|%ct"],
            self.cwd,
        )
        if code == 0 and stdout.strip():
            parts = stdout.strip().split("|")
            return {
                "hash": parts[0] if parts else None,
                "time": float(parts[1]) if len(parts) > 1 else None,
            }
        return {}

    async def _collect_project(self) -> ProjectInfo:
        """Collect project info."""
        info = ProjectInfo()

        # Detect project type
        info.type = await self._detect_project_type()
        info.config_files = await self._find_config_files()

        # Collect based on type
        if info.type == "python":
            py_info = await self._collect_python_project()
            info.name = py_info.get("name")
            info.version = py_info.get("version")
            info.dependencies = py_info.get("dependencies", [])
            info.dev_dependencies = py_info.get("dev_dependencies", [])

        elif info.type == "javascript":
            js_info = await self._collect_javascript_project()
            info.name = js_info.get("name")
            info.version = js_info.get("version")
            info.dependencies = js_info.get("dependencies", [])
            info.dev_dependencies = js_info.get("devDependencies", [])

        # Find entry points
        info.entry_points = await self._find_entry_points()

        # Find test files
        info.test_files = await self._find_test_files()

        # Find source dirs
        info.source_dirs = await self._find_source_dirs()

        return info

    async def _detect_project_type(self) -> str:
        """Detect project type."""
        checks = [
            ("pyproject.toml", "python"),
            ("setup.py", "python"),
            ("requirements.txt", "python"),
            ("package.json", "javascript"),
            ("Cargo.toml", "rust"),
            ("go.mod", "go"),
            ("pom.xml", "java"),
            ("Makefile", "make"),
        ]

        loop = asyncio.get_event_loop()

        for file, type in checks:
            exists = await loop.run_in_executor(None, lambda f=file: (self.cwd / f).exists())
            if exists:
                return type

        return "unknown"

    async def _find_config_files(self) -> List[str]:
        """Find config files."""
        patterns = [
            "*.toml", "*.json", "*.yaml", "*.yml",
            "*.ini", "*.cfg", ".env*", "Dockerfile",
        ]

        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(
            None,
            lambda: [f.name for p in patterns for f in self.cwd.glob(p) if f.is_file()],
        )
        return files[:20]  # Limit

    async def _collect_python_project(self) -> dict:
        """Collect Python project info."""
        pyproject = self.cwd / "pyproject.toml"

        loop = asyncio.get_event_loop()

        if pyproject.exists():
            try:
                content = await loop.run_in_executor(None, pyproject.read_text)
                # Simple parsing (no toml library needed for basic info)
                info = {}

                # Extract name
                for line in content.split("\n"):
                    if line.startswith("name ="):
                        info["name"] = line.split("=")[1].strip().strip('"')
                    elif line.startswith("version ="):
                        info["version"] = line.split("=")[1].strip().strip('"')
                    elif line.startswith("dependencies ="):
                        # Parse list
                        deps = []
                        in_list = False
                        for dep_line in content.split("\n"):
                            if "[" in dep_line and "dependencies" in dep_line:
                                in_list = True
                            elif in_list and dep_line.strip().startswith('"'):
                                deps.append(dep_line.strip().strip('"'))
                            elif in_list and "]" in dep_line:
                                break
                        info["dependencies"] = deps

                return info
            except Exception:
                pass

        return {}

    async def _collect_javascript_project(self) -> dict:
        """Collect JavaScript project info."""
        package_json = self.cwd / "package.json"

        loop = asyncio.get_event_loop()

        if package_json.exists():
            try:
                content = await loop.run_in_executor(None, package_json.read_text)
                data = json.loads(content)
                return {
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "dependencies": list(data.get("dependencies", {}).keys()),
                    "devDependencies": list(data.get("devDependencies", {}).keys()),
                }
            except Exception:
                pass

        return {}

    async def _find_entry_points(self) -> List[str]:
        """Find entry point files."""
        candidates = [
            "main.py", "app.py", "__main__.py", "cli.py", "run.py",
            "index.js", "index.ts", "app.js", "server.js", "main.js",
            "main.go", "cmd.go",
            "main.rs", "lib.rs",
        ]

        loop = asyncio.get_event_loop()
        entries = await loop.run_in_executor(
            None,
            lambda: [c for c in candidates if (self.cwd / c).exists()],
        )
        return entries

    async def _find_test_files(self) -> List[str]:
        """Find test files."""
        patterns = ["test_*.py", "*_test.py", "tests/**/*.py", "*.test.js", "*.spec.js"]

        loop = asyncio.get_event_loop()

        files = []
        for pattern in patterns:
            matches = await loop.run_in_executor(
                None,
                lambda p=pattern: [str(f.relative_to(self.cwd)) for f in self.cwd.glob(p) if f.is_file()],
            )
            files.extend(matches)

        return files[:50]  # Limit

    async def _find_source_dirs(self) -> List[str]:
        """Find source directories."""
        candidates = ["src", "lib", "app", "source", "srcs", "pkg", "internal"]

        loop = asyncio.get_event_loop()
        dirs = await loop.run_in_executor(
            None,
            lambda: [d for d in candidates if (self.cwd / d).is_dir()],
        )
        return dirs


def build_system_prompt_from_context(context: ContextInfo, scenario: str = "developer") -> str:
    """Build system prompt from context."""
    # Base prompt
    base = """You are Claude Code, an AI-powered coding assistant for the terminal.

## Environment
- Platform: {platform}
- Python: {python_version}
- Working Directory: {cwd}

## Git Context
- Branch: {branch}
- Status: {status}
- Recent commits: {commits}

## Project
- Type: {project_type}
- Name: {project_name}

## Instructions
1. Understand before acting
2. Make targeted changes
3. Verify results
4. Be concise and helpful"""

    # Fill in context
    branch = context.git.branch or "unknown"
    status_summary = "clean" if not context.git.status else f"{len(context.git.staged_files)} staged, {len(context.git.unstaged_files)} unstaged"
    commits = ", ".join(context.git.recent_commits[:3]) if context.git.recent_commits else "none"
    project_name = context.project.name or (context.cwd.name if context.cwd else "project")

    prompt = base.format(
        platform=context.environment.platform,
        python_version=context.environment.python_version,
        cwd=context.environment.cwd,
        branch=branch,
        status=status_summary,
        commits=commits,
        project_type=context.project.type,
        project_name=project_name,
    )

    # Add scenario-specific additions
    if scenario == "review":
        prompt += """

## Review Guidelines
- Check for security issues
- Check for code quality
- Suggest improvements"""
    elif scenario == "security":
        prompt += """

## Security Focus
- Look for vulnerabilities
- Check authentication
- Verify input validation"""
    elif scenario == "refactor":
        prompt += """

## Refactor Focus
- Identify duplicate code
- Find opportunities to simplify
- Maintain functionality"""

    return prompt


async def get_full_context(cwd: Path) -> ContextInfo:
    """Get complete context asynchronously."""
    collector = AsyncContextCollector(cwd)
    return await collector.collect_all()


def get_context_sync(cwd: Path) -> ContextInfo:
    """Sync wrapper for context collection."""
    return asyncio.run(get_full_context(cwd))
