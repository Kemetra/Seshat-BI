from __future__ import annotations

from pathlib import Path

from tests.unit._gitfix import commit_all, make_git_repo


def pbir_gate_repo(tmp_path: Path, *, approved: bool = True) -> Path:
    repo = make_git_repo(tmp_path)
    readiness = repo / "mappings" / "orders" / "readiness-status.yaml"
    readiness.parent.mkdir(parents=True)
    approvals = (
        'approvals:\n  - stage: "dashboard_ready"\n'
        '    owner: "A Person (owner)"\n'
        '    at: "2026-08-10"\n'
        '    note: "Approved report design"\n'
        if approved
        else "approvals: []\n"
    )
    readiness.write_text(
        f'stages:\n  semantic_model_ready:\n    status: "pass"\n{approvals}',
        encoding="utf-8",
    )
    commit_all(repo, "record PBIR authoring evidence")
    return repo


def gate_args(repo: Path) -> list[str]:
    return ["--repo", str(repo), "--table", "orders"]
