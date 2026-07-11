"""TDD tests for the scaffold-rule authoring helper + doctor (feature 062).

Covers:
* the declared five-place list guard (FR-017);
* author-mode input validation + refusal paths (FR-009/FR-010);
* the write/print split -- exactly three writes, nothing to golden/glossary
  (FR-002..FR-008, SC-004);
* generic stub (Principle VII) + honest-red contract (SC-002);
* doctor per-place readers, single/sweep, exit-code semantics, read-only
  (FR-011..FR-015), including the known drift instance cited generically (SC-003);
* the stdlib-only / driver-free invariant (FR-016, Principle VIII).

Tests use a tmp_path repo copy so no real repo file is mutated; the live-repo
doctor tests read the real repo but never write.
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest

from seshat import scaffold
from seshat.scaffold import (
    FIVE_PLACES,
    MISSING,
    PRESENT,
    REPO_WIRING_KEYS,
    UNVERIFIABLE,
    doctor,
    validate_identity,
)

pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# T004 [US3]: five-place list guard (FR-017).
# ---------------------------------------------------------------------------


def test_declared_five_places_match_repo_keys() -> None:
    declared = {p.key for p in FIVE_PLACES}
    assert declared == set(REPO_WIRING_KEYS)
    assert len(FIVE_PLACES) == 5


def test_removing_a_declared_place_would_fail_the_guard() -> None:
    # Sub-assertion: dropping any single place breaks the key-set equality, so a
    # future removal cannot pass silently.
    for dropped in FIVE_PLACES:
        remaining = {p.key for p in FIVE_PLACES if p.key != dropped.key}
        assert remaining != set(REPO_WIRING_KEYS)


def test_each_place_declares_targets_and_write_mode() -> None:
    for p in FIVE_PLACES:
        assert p.targets and all(isinstance(t, str) for t in p.targets)
        assert p.write_mode in ("write", "print")
    # golden spans two files; both print-only.
    golden = next(p for p in FIVE_PLACES if p.key == "golden")
    assert len(golden.targets) == 2
    assert golden.write_mode == "print"


# ---------------------------------------------------------------------------
# T005 [US1]: input validation (FR-010).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    ["", "1S", "S 1", "S-1", "S.1", "S/1", "  ", "S1;"],
)
def test_malformed_id_is_rejected(bad_id: str) -> None:
    assert validate_identity(bad_id, "A valid title") is not None


def test_empty_title_is_rejected() -> None:
    assert validate_identity("S9", "") is not None
    assert validate_identity("S9", "   ") is not None


def test_valid_identity_passes() -> None:
    assert validate_identity("S9", "A valid title") is None
    assert validate_identity("PP2", "Another title") is None


def test_scaffold_rejects_malformed_id_with_zero_writes(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    result = scaffold.scaffold(repo, "1bad", "A title")
    assert not result.ok
    assert result.written == ()
    assert _no_new_rule_files(repo)


def test_scaffold_rejects_empty_title_with_zero_writes(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    result = scaffold.scaffold(repo, "Znew", "")
    assert not result.ok
    assert result.written == ()


# ---------------------------------------------------------------------------
# T006 [US1]: refusal paths (FR-009).
# ---------------------------------------------------------------------------


def test_scaffold_refuses_already_registered_id(tmp_path: Path) -> None:
    # S1 is a real registered rule; scaffolding it must refuse with no writes.
    repo = _fixture_repo(tmp_path)
    result = scaffold.scaffold(repo, "S1", "Duplicate")
    assert not result.ok
    assert "already registered" in result.refused
    assert result.written == ()


def test_scaffold_refuses_when_id_already_in_expected_set_but_module_absent(
    tmp_path: Path,
) -> None:
    # Regression: a prior partial scaffold left the id inside EXPECTED_RULE_IDS
    # but its stub module was deleted, so the LIVE registry no longer knows it.
    # The "already registered" refusal (live-registry only) does NOT fire here,
    # so without a text-membership check the id would be inserted a SECOND time,
    # breaking the spec's idempotent-safe "will not double-insert" guarantee.
    repo = _fixture_repo(tmp_path)
    wiring_rel = "tests/unit/test_rules_wiring.py"
    wiring = repo / wiring_rel
    text = wiring.read_text(encoding="utf-8")
    # Inject a fresh id (not a live-registered rule) into EXPECTED_RULE_IDS,
    # simulating the surviving-edit half of a partial prior scaffold.
    injected = text.replace(
        "EXPECTED_RULE_IDS = frozenset(\n    {\n",
        'EXPECTED_RULE_IDS = frozenset(\n    {\n        "Zdup",\n',
        1,
    )
    assert injected != text, "fixture EXPECTED_RULE_IDS block shape changed"
    wiring.write_text(injected, encoding="utf-8")

    result = scaffold.scaffold(repo, "Zdup", "A title")
    assert not result.ok
    assert "already a member" in result.refused
    assert result.written == ()
    # The id appears exactly once -- never double-inserted.
    assert wiring.read_text(encoding="utf-8").count('"Zdup"') == 1


def test_scaffold_refuses_when_stub_module_exists(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    # Pre-create the stub module the helper would write.
    existing = repo / "src/seshat/rules/rule_znew.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("# pre-existing\n", encoding="utf-8")
    result = scaffold.scaffold(repo, "Znew", "A title")
    assert not result.ok
    assert "already exists" in result.refused
    # The pre-existing file is untouched.
    assert existing.read_text(encoding="utf-8") == "# pre-existing\n"


# ---------------------------------------------------------------------------
# T007 [US1]: the write/print split (FR-002..FR-008, SC-004).
# ---------------------------------------------------------------------------


def test_scaffold_writes_exactly_three_targets(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    before = _snapshot(repo)
    result = scaffold.scaffold(repo, "Znew", "A brand new rule")
    assert result.ok
    assert set(result.written) == {
        "src/seshat/rules/rule_znew.py",
        "tests/unit/test_rule_znew.py",
        "tests/unit/test_rules_wiring.py",
    }
    after = _snapshot(repo)
    changed = _changed_paths(before, after)
    # Only the three write targets changed on disk.
    assert changed == set(result.written)


def test_scaffold_never_writes_golden_or_glossary(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    golden_a = (repo / "docs/rules/rules-manifest.json").read_bytes()
    golden_b = (repo / "docs/rules/severity-posture.json").read_bytes()
    glossary = (repo / "docs/glossary.md").read_bytes()
    result = scaffold.scaffold(repo, "Znew", "A brand new rule")
    assert result.ok
    # golden/glossary bytes are byte-identical afterwards.
    assert (repo / "docs/rules/rules-manifest.json").read_bytes() == golden_a
    assert (repo / "docs/rules/severity-posture.json").read_bytes() == golden_b
    assert (repo / "docs/glossary.md").read_bytes() == glossary
    # And they are not in written[].
    for w in result.written:
        assert "rules-manifest.json" not in w
        assert "severity-posture.json" not in w
        assert "glossary.md" not in w


def test_scaffold_prints_regen_commands_and_glossary_row(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    result = scaffold.scaffold(repo, "Znew", "A brand new rule")
    assert result.ok
    joined = "\n".join(result.printed)
    assert "retail manifest" in joined
    assert "retail severity-posture" in joined
    # a glossary row (a markdown table row referencing the id).
    assert any(line.startswith("|") and "Znew" in line for line in result.printed)
    # the import/__all__ edit is shown for review.
    assert any("__all__" in line for line in result.printed)


def test_scaffold_inserts_id_into_expected_set(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    result = scaffold.scaffold(repo, "Znew", "A brand new rule")
    assert result.ok
    wiring = (repo / "tests/unit/test_rules_wiring.py").read_text(encoding="utf-8")
    assert '"Znew"' in wiring
    # The file still parses as valid Python after the insertion.
    ast.parse(wiring)


# ---------------------------------------------------------------------------
# T008 [US1]: generated stub is generic (FR-003, Principle VII).
# ---------------------------------------------------------------------------


def test_generated_stub_is_generic(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    scaffold.scaffold(repo, "Znew", "A brand new rule")
    module = (repo / "src/seshat/rules/rule_znew.py").read_text(encoding="utf-8")
    test = (repo / "tests/unit/test_rule_znew.py").read_text(encoding="utf-8")
    # No worked-example tokens (case-insensitive) leak into generated files.
    banned = ["c086", "pharmacy", "ezaby", "el ezaby", "fct_sales", "dim_product"]
    for token in banned:
        assert token not in module.lower()
        assert token not in test.lower()
    # ASCII-safe (Principle IX).
    assert module.isascii()
    assert test.isascii()


# ---------------------------------------------------------------------------
# T009 [US1]: honest-red contract (SC-002, US1 scenario 3).
# ---------------------------------------------------------------------------


def test_generated_test_stub_fails_immediately(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    scaffold.scaffold(repo, "Znew", "A brand new rule")
    test_src = (repo / "tests/unit/test_rule_znew.py").read_text(encoding="utf-8")
    # The stub contains an explicit failure so it is RED until real logic lands.
    assert "pytest.fail" in test_src
    # Execute the stub in isolation and confirm it raises (Failed).
    ns: dict = {}
    exec(compile(test_src, "test_rule_znew.py", "exec"), ns)  # noqa: S102
    test_fn = ns["test_znew_not_yet_implemented"]
    with pytest.raises(BaseException):
        test_fn()


# ---------------------------------------------------------------------------
# T012 [US2]: per-place readers, present/missing/unverifiable (FR-015).
# ---------------------------------------------------------------------------


def test_place_readers_report_present_for_a_fully_wired_id() -> None:
    # S1 is fully wired (registered, imported, expected, golden, glossary).
    report = doctor(REPO_ROOT, "S1")
    entry = report.entries[0]
    assert entry.id == "S1"
    assert all(state == PRESENT for state in entry.places.values()), entry.places
    assert not entry.has_drift


def test_place_readers_report_missing_for_unregistered_id() -> None:
    report = doctor(REPO_ROOT, "ZZ999")
    entry = report.entries[0]
    # Unknown id: missing in the readable places, never crashes.
    assert entry.places["register"] == MISSING
    assert entry.places["expected_ids"] == MISSING
    assert report.has_drift


def test_place_reader_reports_unverifiable_when_file_absent(tmp_path: Path) -> None:
    # A repo with NO golden records: golden place is unverifiable, not missing.
    empty = tmp_path / "empty_repo"
    empty.mkdir()
    assert scaffold.check_golden(empty, "S1") == UNVERIFIABLE
    assert scaffold.check_expected_ids(empty, "S1") == UNVERIFIABLE
    assert scaffold.check_glossary(empty, "S1") == UNVERIFIABLE


# ---------------------------------------------------------------------------
# T013 [US2]: single + sweep modes; the known drift instance (SC-003).
# ---------------------------------------------------------------------------


def test_doctor_single_id_verifies_one_id() -> None:
    report = doctor(REPO_ROOT, "S1")
    assert len(report.entries) == 1
    assert report.entries[0].id == "S1"


def test_doctor_sweep_covers_every_registered_id() -> None:
    report = doctor(REPO_ROOT)
    swept = {e.id for e in report.entries}
    registered = scaffold._registered_ids(REPO_ROOT)
    assert registered is not None
    assert swept == set(registered)
    assert len(swept) > 1


def test_no_registered_id_is_missing_from_the_glossary() -> None:
    # Post-fix invariant (adversarial audit C12): every registered, wired rule id
    # must ALSO appear in the glossary catalog. The DL1/DL2 family was the known
    # drift instance -- wired everywhere but absent from docs/glossary.md -- and it
    # is now added, so ZERO registered ids may be glossary-gaps. (This asserts the
    # honest end state; the doctor's *ability* to detect a glossary gap is covered
    # by test_doctor_flags_synthetic_glossary_gap below.)
    report = doctor(REPO_ROOT)
    glossary_gaps = [
        e.id
        for e in report.entries
        if e.places["glossary"] == MISSING
        and e.places["register"] == PRESENT
        and e.places["expected_ids"] == PRESENT
        and e.places["golden"] == PRESENT
    ]
    assert glossary_gaps == [], (
        f"registered rule ids missing from docs/glossary.md: {glossary_gaps}"
    )


def test_doctor_flags_synthetic_glossary_gap(tmp_path: Path) -> None:
    # The detector's ABILITY to flag a glossary gap, proven on a synthetic id that
    # is deliberately absent from the fixture glossary -- so the invariant test
    # above (which asserts ZERO real gaps) is not vacuous.
    from seshat.scaffold import check_glossary

    repo = _fixture_repo(tmp_path)
    assert check_glossary(repo, "ZZ99") == MISSING


# ---------------------------------------------------------------------------
# T014 [US2]: exit-code contract (FR-014).
# ---------------------------------------------------------------------------


def test_has_drift_false_when_all_present() -> None:
    report = doctor(REPO_ROOT, "S1")
    assert report.has_drift is False


def test_has_drift_true_when_any_place_missing() -> None:
    report = doctor(REPO_ROOT, "ZZ999")
    assert report.has_drift is True


# ---------------------------------------------------------------------------
# T015 [US2]: doctor writes NOTHING (FR-013).
# ---------------------------------------------------------------------------


def test_doctor_writes_nothing(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    before = _snapshot(repo)
    doctor(repo)  # full sweep
    doctor(repo, "S1")  # single
    after = _snapshot(repo)
    assert _changed_paths(before, after) == set()


# ---------------------------------------------------------------------------
# T018/T019: stdlib-only, driver-free (FR-016, Principle VIII).
# ---------------------------------------------------------------------------


def test_scaffold_module_imports_no_third_party_or_driver() -> None:
    from seshat.rules.never_execute import module_scope_violations

    src = (REPO_ROOT / "src/seshat/scaffold.py").read_text(encoding="utf-8")
    assert module_scope_violations(src) == []


def test_scaffold_module_imports_only_stdlib_and_local() -> None:
    src = (REPO_ROOT / "src/seshat/scaffold.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    stdlib_roots = {"json", "re", "dataclasses", "pathlib", "typing", "__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                # `import seshat.rules` is a local package import (lazy, in-function)
                # -- allowed; anything else must be stdlib.
                assert root in stdlib_roots or root == "seshat", (
                    f"unexpected import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # local relative import (.registry, .core) is fine
            root = (node.module or "").split(".")[0]
            # module-scope from-imports are all stdlib; local ones are relative.
            assert root in stdlib_roots or root == "seshat", (
                f"unexpected from-import: {node.module}"
            )


# ---------------------------------------------------------------------------
# T011/T017: CLI dispatch (author + doctor) via cli.main.
# ---------------------------------------------------------------------------


def test_cli_author_mode_writes_and_prints(tmp_path: Path, capsys) -> None:
    from seshat import cli

    repo = _fixture_repo(tmp_path)
    rc = cli.main(
        ["scaffold", "--repo", str(repo), "--id", "Znew", "--title", "A new rule"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "wrote src/seshat/rules/rule_znew.py" in out
    assert "retail manifest" in out
    assert (repo / "src/seshat/rules/rule_znew.py").exists()


def test_cli_author_mode_missing_title_returns_2(tmp_path: Path) -> None:
    from seshat import cli

    repo = _fixture_repo(tmp_path)
    rc = cli.main(["scaffold", "--repo", str(repo), "--id", "Znew"])
    assert rc == 2


def test_cli_author_mode_refusal_returns_1(tmp_path: Path) -> None:
    from seshat import cli

    repo = _fixture_repo(tmp_path)
    rc = cli.main(
        ["scaffold", "--repo", str(repo), "--id", "S1", "--title", "Duplicate"]
    )
    assert rc == 1


def test_cli_doctor_clean_id_returns_0(capsys) -> None:
    from seshat import cli

    rc = cli.main(["scaffold", "--repo", str(REPO_ROOT), "--doctor", "--id", "S1"])
    assert rc == 0
    assert "[ok] S1" in capsys.readouterr().out


def test_cli_doctor_drift_id_returns_1(capsys) -> None:
    from seshat import cli

    rc = cli.main(["scaffold", "--repo", str(REPO_ROOT), "--doctor", "--id", "ZZ999"])
    assert rc == 1
    assert "[DRIFT] ZZ999" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fixture_repo(tmp_path: Path) -> Path:
    """Build a minimal repo copy carrying the five wiring places.

    Copies only the files the helper reads/writes so tests never mutate the real
    repo. The registry side-effect still resolves against the installed package
    (the copy is for the text-scanned places).
    """
    repo = tmp_path / "repo"
    (repo / "src/seshat/rules").mkdir(parents=True)
    (repo / "tests/unit").mkdir(parents=True)
    (repo / "docs/rules").mkdir(parents=True)
    for rel in (
        "src/seshat/rules/__init__.py",
        "tests/unit/test_rules_wiring.py",
        "docs/rules/rules-manifest.json",
        "docs/rules/severity-posture.json",
        "docs/glossary.md",
    ):
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / rel, dst)
    return repo


def _no_new_rule_files(repo: Path) -> bool:
    rules = repo / "src/seshat/rules"
    names = {p.name for p in rules.glob("*.py")}
    return names == {"__init__.py"}


def _snapshot(repo: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path in sorted(repo.rglob("*")):
        if path.is_file():
            out[path.relative_to(repo).as_posix()] = path.read_bytes()
    return out


def _changed_paths(before: dict[str, bytes], after: dict[str, bytes]) -> set[str]:
    changed = set()
    for rel, data in after.items():
        if before.get(rel) != data:
            changed.add(rel)
    for rel in before:
        if rel not in after:
            changed.add(rel)
    return changed
