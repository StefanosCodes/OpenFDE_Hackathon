from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.core.settings import PROJECT_ROOT, Settings, settings
from app.integrations.github.client import GitHubClient
from app.integrations.github.repository import GitHubConnectionRepository
from app.schemas.codebase import (
    CodebaseEvidencePacket,
    CodexInspectionOutput,
)


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


class CodebaseInspectionError(RuntimeError):
    pass


async def inspect_connected_codebase(
    *,
    owner_user_id: UUID,
    question: str,
    github: GitHubClient,
    repository_store: GitHubConnectionRepository,
    config: Settings = settings,
) -> CodebaseEvidencePacket:
    question = question.strip()
    if not question:
        raise CodebaseInspectionError("A codebase question is required")
    if not config.openai_api_key:
        raise CodebaseInspectionError("OPENAI_API_KEY is not configured")

    connection = await repository_store.get(owner_user_id)
    if (
        connection is None
        or connection.status != "connected"
        or connection.installation_id is None
        or connection.repository is None
    ):
        raise CodebaseInspectionError("Connect GitHub and select a repository first")

    selected = connection.repository
    _validate_repository_name(selected.full_name)
    _validate_branch_name(selected.default_branch)
    token = await github.create_repository_token(
        installation_id=connection.installation_id,
        repository_id=selected.id,
    )

    with tempfile.TemporaryDirectory(prefix="openfde-codex-") as temporary_root:
        checkout = Path(temporary_root) / "repository"
        await _clone_repository(
            repository=selected.full_name,
            branch=selected.default_branch,
            token=token,
            destination=checkout,
            timeout_seconds=config.codex_clone_timeout_seconds,
        )
        commit_sha = await _git_output(checkout, "rev-parse", "HEAD")
        repository_bytes = _repository_size(checkout)
        if repository_bytes > config.codex_max_repository_bytes:
            raise CodebaseInspectionError(
                "The selected repository is too large for a temporary inspection"
            )

        output = await _run_codex_sdk(
            checkout=checkout,
            repository=selected.full_name,
            commit_sha=commit_sha,
            question=question,
            config=config,
        )
        dirty = await _git_output(
            checkout,
            "status",
            "--porcelain",
            "--untracked-files=all",
        )
        if dirty:
            raise CodebaseInspectionError("The read-only runner changed the checkout")
        output = _verify_evidence(output, checkout)

    return CodebaseEvidencePacket(
        repository=selected.full_name,
        commit_sha=commit_sha,
        summary=output.summary,
        findings=output.findings,
        references=output.references,
        files_inspected=output.files_inspected,
        limitations=output.limitations,
        generated_at=datetime.now(timezone.utc),
    )


def _validate_repository_name(value: str) -> None:
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise CodebaseInspectionError("GitHub returned an invalid repository name")


def _validate_branch_name(value: str) -> None:
    if (
        not BRANCH_PATTERN.fullmatch(value)
        or value.startswith(("-", "/"))
        or value.endswith("/")
        or ".." in value
        or "//" in value
    ):
        raise CodebaseInspectionError("GitHub returned an invalid default branch")


async def _clone_repository(
    *,
    repository: str,
    branch: str,
    token: str,
    destination: Path,
    timeout_seconds: int,
) -> None:
    askpass = destination.parent / "git-askpass.sh"
    askpass.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *Username*) printf '%s\\n' 'x-access-token' ;;\n"
        "  *) printf '%s\\n' \"$OPENFDE_GITHUB_TOKEN\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    askpass.chmod(0o700)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(destination.parent),
        "TMPDIR": os.environ.get("TMPDIR", tempfile.gettempdir()),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ASKPASS": str(askpass),
        "GIT_TERMINAL_PROMPT": "0",
        "OPENFDE_GITHUB_TOKEN": token,
    }
    process = await asyncio.create_subprocess_exec(
        "git",
        "-c",
        "credential.helper=",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--no-tags",
        "--branch",
        branch,
        f"https://github.com/{repository}.git",
        str(destination),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
        env=environment,
    )
    try:
        _stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise CodebaseInspectionError("GitHub clone timed out") from exc
    finally:
        askpass.unlink(missing_ok=True)
    if process.returncode != 0:
        reason = stderr.decode("utf-8", errors="replace").strip()
        raise CodebaseInspectionError(
            f"Could not clone the selected GitHub repository: {reason[-500:]}"
        )


async def _run_codex_sdk(
    *,
    checkout: Path,
    repository: str,
    commit_sha: str,
    question: str,
    config: Settings,
) -> CodexInspectionOutput:
    node = shutil.which("node")
    if node is None:
        raise CodebaseInspectionError("Node.js is required for the Codex SDK runner")
    runner = PROJECT_ROOT / "scripts" / "codex_inspect.mjs"
    payload = json.dumps(
        {
            "working_directory": str(checkout),
            "repository": repository,
            "commit_sha": commit_sha,
            "question": question,
            "model": config.codex_model,
            "reasoning_effort": config.codex_reasoning_effort,
            "timeout_ms": config.codex_runner_timeout_seconds * 1000,
        }
    ).encode("utf-8")
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "OPENAI_API_KEY": config.openai_api_key or "",
        "TMPDIR": os.environ.get("TMPDIR", tempfile.gettempdir()),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }
    process = await asyncio.create_subprocess_exec(
        node,
        str(runner),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=environment,
    )
    try:
        stdout, _stderr = await asyncio.wait_for(
            process.communicate(payload),
            timeout=config.codex_runner_timeout_seconds + 10,
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise CodebaseInspectionError("Codex inspection timed out") from exc
    if process.returncode != 0:
        raise CodebaseInspectionError("Codex could not inspect the repository")
    if len(stdout) > 1_000_000:
        raise CodebaseInspectionError("Codex returned an oversized evidence packet")
    decoded = stdout.decode("utf-8", errors="strict")
    if config.openai_api_key and config.openai_api_key in decoded:
        raise CodebaseInspectionError("Codex returned sensitive configuration")
    try:
        return CodexInspectionOutput.model_validate_json(decoded)
    except ValueError as exc:
        raise CodebaseInspectionError("Codex returned an invalid evidence packet") from exc


async def _git_output(checkout: Path, *arguments: str) -> str:
    process = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(checkout),
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={"PATH": os.environ.get("PATH", "")},
    )
    stdout, _stderr = await process.communicate()
    if process.returncode != 0:
        raise CodebaseInspectionError("Could not verify the temporary checkout")
    return stdout.decode("utf-8", errors="replace").strip()


def _repository_size(checkout: Path) -> int:
    total = 0
    for root, directories, files in os.walk(checkout):
        directories[:] = [name for name in directories if name != ".git"]
        for filename in files:
            path = Path(root) / filename
            if not path.is_symlink():
                total += path.stat().st_size
    return total


def _verify_evidence(
    output: CodexInspectionOutput, checkout: Path
) -> CodexInspectionOutput:
    verified_references = []
    limitations = list(output.limitations)
    checkout_root = checkout.resolve()
    for reference in output.references:
        if _is_sensitive_path(reference.path):
            limitations.append(f"Rejected a sensitive-file citation: {reference.path}")
            continue
        candidate = (checkout / reference.path).resolve()
        try:
            candidate.relative_to(checkout_root)
        except ValueError:
            limitations.append(f"Rejected an out-of-repository citation: {reference.path}")
            continue
        if not candidate.is_file():
            limitations.append(f"Could not verify cited file: {reference.path}")
            continue
        try:
            with candidate.open("r", encoding="utf-8", errors="replace") as handle:
                line_count = sum(1 for _line in handle)
        except OSError:
            limitations.append(f"Could not read cited file: {reference.path}")
            continue
        if reference.end_line > line_count:
            limitations.append(f"Could not verify cited lines in: {reference.path}")
            continue
        verified_references.append(reference)
    return output.model_copy(
        update={
            "references": verified_references,
            "files_inspected": [
                path for path in output.files_inspected if not _is_sensitive_path(path)
            ][:100],
            "limitations": limitations[:20],
        }
    )


def _is_sensitive_path(value: str) -> bool:
    path = Path(value)
    lowered_parts = [part.lower() for part in path.parts]
    filename = path.name.lower()
    return (
        any(part in {".secrets", "secrets"} for part in lowered_parts)
        or filename == ".env"
        or filename.startswith(".env.")
        or path.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
    )
