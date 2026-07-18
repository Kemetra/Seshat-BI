"""Parity parsing and normalized, approval-neutral dbt run evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from secrets import token_hex
from typing import Any

from seshat.dbt._evidence_schema import validate_evidence_payload
from seshat.dbt.artifacts import ArtifactIntegrityError, cross_check_execution
from seshat.dbt.contracts import (
    ArtifactSet,
    Blocker,
    ExecutionPlan,
    InvocationResult,
    Operation,
    ParityAssertion,
    RunEvidence,
    RunResultsSummary,
    TestSummary,
)
from seshat.dbt.planning import plan_digest
from seshat.dbt.redaction import (
    EnvironmentConfigError,
    load_child_environment,
    sanitize,
    secret_values,
)

_INVOCATION_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_TABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_TEST_STATUS_BUCKETS = {
    "pass": "passed",
    "success": "passed",
    "fail": "failed",
    "warn": "failed",
    "error": "errored",
    "skipped": "skipped",
}
_PRIMARY_RESULT_OPERATIONS = frozenset({Operation.BUILD.value, Operation.TEST.value})
_REPORTED_DECIMAL_ERRORS = {
    "delta": "reported delta does not match values for {assertion_id}",
    "tolerance": "reported tolerance is not governed for {assertion_id}",
}


def _is_parity_result(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, dict) and "assertion_id" in row for row in value)
    )


def _candidate_entry(key: str, value: Any) -> list[list[dict[str, Any]]]:
    if key == "rows" and _is_parity_result(value):
        return [value]
    # dbt 1.12 `show --output json` carries the preview rows as a JSON-encoded
    # STRING under "preview", not a native list. Decode it and treat a decoded
    # parity-result array the same as a native "rows" array.
    if key == "preview" and isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None
        if _is_parity_result(decoded):
            return [decoded]
    return _candidate_rows(value)


def _mapping_candidate_rows(value: dict[str, Any]) -> list[list[dict[str, Any]]]:
    candidates: list[list[dict[str, Any]]] = []
    for key, nested in value.items():
        candidates.extend(_candidate_entry(key, nested))
    return candidates


def _sequence_candidate_rows(value: list[Any]) -> list[list[dict[str, Any]]]:
    candidates: list[list[dict[str, Any]]] = []
    for nested in value:
        candidates.extend(_candidate_rows(nested))
    return candidates


def _candidate_rows(value: Any) -> list[list[dict[str, Any]]]:
    if isinstance(value, dict):
        return _mapping_candidate_rows(value)
    if isinstance(value, list):
        return _sequence_candidate_rows(value)
    return []


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ArtifactIntegrityError(f"parity {label} is not numeric")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ArtifactIntegrityError(f"parity {label} is not numeric") from exc
    if not number.is_finite():
        raise ArtifactIntegrityError(f"parity {label} must be finite")
    return number


def _decimal_string(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


# The governed assertion classes (spec 133 data-model.md) and the tolerance each
# class carries. Tolerance is a function of class -- 0 for exact counts, 0.01 for
# additive money -- NOT a per-table value, so a table cannot loosen its own bound
# (the committed map supplies WHICH assertions; code fixes HOW tight).
_CLASS_TOLERANCES: dict[str, Decimal] = {
    "fact_row_count": Decimal("0"),
    "business_key_count": Decimal("0"),
    "dimension_member_count": Decimal("0"),
    "additive_money_total": Decimal("0.01"),
}


def _parity_contract(raw: dict[str, Any]) -> tuple[str, str, str, Decimal]:
    """Resolve (id, class, subject, tolerance) for one emitted parity row.

    Class-driven, not id-allowlisted: any table's assertion is accepted as long as
    its class is one of the governed classes; the tolerance is then fixed by that
    class. Validating by class rather than a fixed per-table id list is what makes
    this table-agnostic -- every governed table's parity rows (whose ids/subjects
    legitimately differ) validate on the same rules. The per-table REQUIRED set is
    enforced separately, derived from the built graph's selected_unique_ids (see
    _validate_parity_set)."""
    assertion_id = raw.get("assertion_id")
    if not isinstance(assertion_id, str) or not _TABLE_ID.match(assertion_id):
        raise ArtifactIntegrityError(f"invalid parity assertion id {assertion_id!r}")
    assertion_class = raw.get("assertion_class")
    if assertion_class not in _CLASS_TOLERANCES:
        raise ArtifactIntegrityError(
            f"parity assertion class is invalid for {assertion_id}"
        )
    subject = raw.get("subject")
    if not isinstance(subject, str) or not subject.strip():
        raise ArtifactIntegrityError(f"parity subject is invalid for {assertion_id}")
    return assertion_id, assertion_class, subject, _CLASS_TOLERANCES[assertion_class]


def _validate_reported_decimal(
    raw: dict[str, Any], assertion_id: str, field: str, governed: Decimal
) -> None:
    reported = _decimal(raw.get(field), f"{field} for {assertion_id}")
    if reported != governed:
        raise ArtifactIntegrityError(
            _REPORTED_DECIMAL_ERRORS[field].format(assertion_id=assertion_id)
        )


def _parity_values(
    raw: dict[str, Any], assertion_id: str, tolerance: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    expected = _decimal(raw.get("expected"), f"expected for {assertion_id}")
    actual = _decimal(raw.get("actual"), f"actual for {assertion_id}")
    delta = abs(actual - expected)
    _validate_reported_decimal(
        raw,
        assertion_id,
        "delta",
        delta,
    )
    _validate_reported_decimal(
        raw,
        assertion_id,
        "tolerance",
        tolerance,
    )
    return expected, actual, delta


def _validate_reported_pass(
    raw: dict[str, Any], assertion_id: str, passed: bool
) -> None:
    if not isinstance(raw.get("passed"), bool) or raw["passed"] is not passed:
        raise ArtifactIntegrityError(
            f"reported passed boolean is incorrect for {assertion_id}"
        )


def _parity_row(raw: dict[str, Any]) -> ParityAssertion:
    assertion_id, assertion_class, subject, tolerance = _parity_contract(raw)
    expected, actual, delta = _parity_values(raw, assertion_id, tolerance)
    passed = delta <= tolerance
    _validate_reported_pass(raw, assertion_id, passed)
    return ParityAssertion(
        assertion_id=assertion_id,
        assertion_class=assertion_class,
        subject=subject,
        expected=_decimal_string(expected),
        actual=_decimal_string(actual),
        delta=_decimal_string(delta),
        tolerance=_decimal_string(tolerance),
        passed=passed,
    )


def _parse_show_line(line: str, number: int) -> Any | None:
    if not line.strip():
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise ArtifactIntegrityError(
            f"dbt show line {number} is not valid JSON"
        ) from exc


def _structured_parity_result(event: Any) -> list[dict[str, Any]] | None:
    candidates = _candidate_rows(event)
    if len(candidates) > 1:
        raise ArtifactIntegrityError(
            "dbt show event contains multiple structured parity results"
        )
    return candidates[0] if candidates else None


def _show_result_events(show_stdout: str) -> list[list[dict[str, Any]]]:
    result_events: list[list[dict[str, Any]]] = []
    for number, line in enumerate(show_stdout.splitlines(), start=1):
        event = _parse_show_line(line, number)
        if event is None:
            continue
        result = _structured_parity_result(event)
        if result is not None:
            result_events.append(result)
    return result_events


def _only_parity_result(
    result_events: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    if len(result_events) != 1:
        raise ArtifactIntegrityError(
            "dbt show must contain exactly one structured parity result event"
        )
    return result_events[0]


def _normalized_parity_rows(
    raw_rows: list[dict[str, Any]],
) -> tuple[ParityAssertion, ...]:
    rows = tuple(_parity_row(row) for row in raw_rows)
    ids = tuple(row.assertion_id for row in rows)
    if len(ids) != len(set(ids)):
        raise ArtifactIntegrityError("dbt show contains duplicate parity assertion IDs")
    # Deterministic order by assertion id (no per-table id table to key on).
    return tuple(sorted(rows, key=lambda row: row.assertion_id))


def parse_parity_rows(show_stdout: str) -> tuple[ParityAssertion, ...]:
    """Extract exactly one structured dbt show result and normalize its rows."""

    raw_rows = _only_parity_result(_show_result_events(show_stdout))
    return _normalized_parity_rows(raw_rows)


def _unique_test_results(artifacts: ArtifactSet) -> Iterator[Any]:
    seen: set[str] = set()
    for summary in artifacts.run_results:
        for result in summary.results:
            if not result.unique_id.startswith("test.") or result.unique_id in seen:
                continue
            seen.add(result.unique_id)
            yield result


def _test_summary(artifacts: ArtifactSet) -> TestSummary:
    counts = {"passed": 0, "failed": 0, "errored": 0, "skipped": 0}
    for result in _unique_test_results(artifacts):
        bucket = _TEST_STATUS_BUCKETS.get(result.status)
        if bucket is not None:
            counts[bucket] += 1
    return TestSummary(**counts)


def _artifact_hashes(artifacts: ArtifactSet) -> dict[str, str]:
    hashes = {"manifest.json": artifacts.manifest.sha256}
    for summary in artifacts.run_results:
        key = (
            "parity_run_results.json" if summary.which == "show" else "run_results.json"
        )
        if key in hashes and hashes[key] != summary.sha256:
            raise ArtifactIntegrityError(f"multiple conflicting {key} artifacts")
        hashes[key] = summary.sha256
    return hashes


def _elapsed(started_at: str, completed_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ArtifactIntegrityError("invocation timestamps are invalid") from exc
    elapsed = (completed - start).total_seconds()
    if elapsed < 0:
        raise ArtifactIntegrityError("invocation completed before it started")
    return elapsed


def _validate_artifacts(plan: ExecutionPlan, artifacts: ArtifactSet) -> None:
    if (
        artifacts.manifest.schema_uri != plan.manifest.schema_uri
        or artifacts.manifest.semantic_sha256 != plan.manifest.semantic_sha256
    ):
        raise ArtifactIntegrityError("manifest does not match the accepted plan")
    for results in artifacts.run_results:
        cross_check_execution(plan, results)


def _results_for_operations(
    artifacts: ArtifactSet, operations: frozenset[str]
) -> tuple[RunResultsSummary, ...]:
    return tuple(
        result for result in artifacts.run_results if result.which in operations
    )


def _single_result(
    results: tuple[RunResultsSummary, ...], label: str
) -> RunResultsSummary:
    if len(results) != 1:
        raise ArtifactIntegrityError(
            f"dbt evidence requires exactly one {label} run-results artifact"
        )
    return results[0]


def _validate_artifact_roles(
    invocation: InvocationResult, artifacts: ArtifactSet
) -> None:
    primary = _single_result(
        _results_for_operations(artifacts, _PRIMARY_RESULT_OPERATIONS), "primary"
    )
    _single_result(_results_for_operations(artifacts, frozenset({"show"})), "show")
    if primary.which != invocation.operation.value:
        raise ArtifactIntegrityError(
            "primary run-results operation does not match invocation operation"
        )
    if len(artifacts.run_results) != 2:
        raise ArtifactIntegrityError("dbt evidence contains unexpected run-results")


_MODEL_ID = re.compile(r"^model\.[^.]+\.(?P<name>.+)$")


def _selected_model_names(selected_unique_ids: tuple[str, ...]) -> list[str]:
    """The dbt model node names in the built graph (model.* nodes, not tests)."""
    names: list[str] = []
    for uid in selected_unique_ids:
        match = _MODEL_ID.match(uid)
        if match:
            names.append(match.group("name"))
    return names


def _selected_dimension_subjects(
    selected_unique_ids: tuple[str, ...],
) -> frozenset[str]:
    """The dimension model names the build materialized (dim_* model nodes).

    Each dimension_member_count assertion's subject is the dimension's model name
    (e.g. model node ``dim_product`` -> subject ``dim_product``). Parity
    must cover exactly these -- every built dimension, each once, no extras -- so
    the required set is the set of dim_* subjects, not merely their count. The date
    dimension is a dim_* model too, so it is included.
    """
    return frozenset(
        name
        for name in _selected_model_names(selected_unique_ids)
        if name.startswith("dim_")
    )


def _selected_fact_model(selected_unique_ids: tuple[str, ...]) -> str:
    """The single fact model name in the built graph.

    Identified by EXCLUSION, not a name prefix: the fact table is the one built
    model that is not a dimension (dim_*), a staging model (stg_*), or the parity
    audit (audit_*). Prefix-matching the fact would not be portable -- a fact model
    may be named ``fact_*`` or ``fct_*`` -- so exclusion is the table-agnostic rule.
    Exactly one such model must exist.
    """
    facts = [
        name
        for name in _selected_model_names(selected_unique_ids)
        if not name.startswith(("dim_", "stg_", "audit_"))
    ]
    if len(facts) != 1:
        raise ArtifactIntegrityError(
            "the built graph does not contain exactly one fact model "
            f"(found {sorted(facts)})"
        )
    return facts[0]


def _subject_root(subject: str) -> str:
    """The relation a parity subject references -- the part before the first dot.

    Subjects are either a bare model name (``fct_sales``) or a dotted
    measure/grain reference (``fct_sales.net_amount``); both root at the
    model name."""
    return subject.split(".", 1)[0]


# Fact-level assertion classes split by expected cardinality:
#   - fact_row_count / business_key_count are inherent SINGLETONS: one fact table
#     has one row count, one grain has one distinct-key count -- exactly one each.
#   - additive_money_total is NOT a singleton: a fact may carry several additive
#     money measures (e.g. gross_amount AND net_amount), each a separate row. So it
#     requires AT LEAST ONE. Exact per-measure coverage is uncheckable here --
#     money measures are columns, not enumerable model nodes, so unlike dimensions
#     (which are dim_* nodes in selected_unique_ids) the built graph does not list
#     which measures must be reconciled. "At least one, every subject rooting at
#     the built fact" is therefore the strongest check the committed artifacts
#     support. (Exact money-measure coverage would need the map's gold_star to tag
#     which measures are money -- a separate future enhancement, not this layer.)
_FACT_SINGLETON_CLASSES = ("fact_row_count", "business_key_count")
_FACT_CLASSES = (*_FACT_SINGLETON_CLASSES, "additive_money_total")


def _validate_fact_assertions(
    fact_subjects: list[str],
    fact_counts: dict[str, int],
    selected_unique_ids: tuple[str, ...],
) -> None:
    """One row_count + one business_key_count + >=1 additive_money_total, each
    subject rooting at the built fact model."""
    wrong_cardinality = {
        cls: fact_counts.get(cls, 0)
        for cls in _FACT_CLASSES
        if (
            fact_counts.get(cls, 0) != 1
            if cls in _FACT_SINGLETON_CLASSES
            else fact_counts.get(cls, 0) < 1
        )
    }
    if wrong_cardinality:
        raise ArtifactIntegrityError(
            "parity fact-level assertions have the wrong cardinality "
            "(expected exactly one fact_row_count and business_key_count, and at "
            f"least one additive_money_total): {wrong_cardinality}"
        )
    fact_model = _selected_fact_model(selected_unique_ids)
    wrong_fact = sorted({s for s in fact_subjects if _subject_root(s) != fact_model})
    if wrong_fact:
        raise ArtifactIntegrityError(
            "parity fact assertions do not reference the built fact model "
            f"{fact_model!r}: {', '.join(wrong_fact)}"
        )


def _validate_dimension_assertions(
    dim_subjects: list[str],
    selected_unique_ids: tuple[str, ...],
) -> None:
    """The set of dimension subjects must equal the built dim_* models exactly."""
    seen_dims = frozenset(dim_subjects)
    if len(dim_subjects) != len(seen_dims):
        duplicates = sorted({s for s in dim_subjects if dim_subjects.count(s) > 1})
        raise ArtifactIntegrityError(
            "parity has duplicate dimension_member_count subjects: "
            + ", ".join(duplicates)
        )
    expected_dims = _selected_dimension_subjects(selected_unique_ids)
    if seen_dims == expected_dims:
        return
    detail = []
    if expected_dims - seen_dims:
        detail.append("missing " + ", ".join(sorted(expected_dims - seen_dims)))
    if seen_dims - expected_dims:
        detail.append("unexpected " + ", ".join(sorted(seen_dims - expected_dims)))
    raise ArtifactIntegrityError(
        "parity dimension assertions do not match the built dimensions: "
        + "; ".join(detail)
    )


def _validate_parity_set(
    parity: tuple[ParityAssertion, ...],
    selected_unique_ids: tuple[str, ...],
) -> None:
    """Prove the parity audit covers exactly what was built.

    Fact-level: exactly one each of fact_row_count / business_key_count /
    additive_money_total, each one's subject rooting at the built fact model
    (subject, not just count, so a malformed audit cannot reconcile the wrong
    fact relation). Dimensions: the SET of dimension_member_count subjects must
    equal the set of built dim_* models (subject set, not just count, so a
    malformed audit cannot pass by duplicating one dimension and omitting
    another). Partition once here; each side is checked by its own helper.
    """
    fact_counts: dict[str, int] = {cls: 0 for cls in _FACT_CLASSES}
    fact_subjects: list[str] = []
    dim_subjects: list[str] = []
    for row in parity:
        if row.assertion_class in fact_counts:
            fact_counts[row.assertion_class] += 1
            fact_subjects.append(row.subject)
        elif row.assertion_class == "dimension_member_count":
            dim_subjects.append(row.subject)

    _validate_fact_assertions(fact_subjects, fact_counts, selected_unique_ids)
    _validate_dimension_assertions(dim_subjects, selected_unique_ids)


def _execution_blocker(invocation: InvocationResult) -> Blocker | None:
    if invocation.return_code == 0:
        return None
    return Blocker("DBT_EXECUTION_FAILED", "dbt execution completed with failures")


def _test_blocker(tests: TestSummary) -> Blocker | None:
    if not tests.failed and not tests.errored:
        return None
    return Blocker("DBT_TESTS_FAILED", "one or more governed dbt tests failed")


def _parity_blockers(parity: tuple[ParityAssertion, ...]) -> tuple[Blocker, ...]:
    return tuple(
        Blocker(
            "DBT_PARITY_MISMATCH",
            f"{row.assertion_id} delta {row.delta} exceeds tolerance {row.tolerance}",
            assertion_id=row.assertion_id,
        )
        for row in parity
        if not row.passed
    )


def _first_blocker(*blockers: Blocker | None) -> Blocker | None:
    return next((blocker for blocker in blockers if blocker is not None), None)


def _evidence_outcome(
    invocation: InvocationResult,
    tests: TestSummary,
    parity: tuple[ParityAssertion, ...],
) -> tuple[str, int, tuple[Blocker, ...]]:
    fatal = _first_blocker(_execution_blocker(invocation), _test_blocker(tests))
    if fatal is not None:
        return "failed", 1, (fatal,)
    blockers = _parity_blockers(parity)
    if blockers:
        return "blocked", 1, blockers
    return "pass", 0, ()


def _executed_unique_ids(artifacts: ArtifactSet) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                result.unique_id
                for summary in artifacts.run_results
                for result in summary.results
            }
        )
    )


def build_evidence(
    plan: ExecutionPlan,
    invocation: InvocationResult,
    artifacts: ArtifactSet,
    parity: tuple[ParityAssertion, ...],
) -> RunEvidence:
    """Build complete derived evidence without carrying raw process output."""

    if invocation.operation not in {Operation.BUILD, Operation.TEST}:
        raise ArtifactIntegrityError("only build/test invocations produce run evidence")
    _validate_artifact_roles(invocation, artifacts)
    _validate_artifacts(plan, artifacts)
    _validate_parity_set(parity, plan.selected_unique_ids)
    tests = _test_summary(artifacts)
    outcome, exit_code, blockers = _evidence_outcome(invocation, tests, parity)
    return RunEvidence(
        schema_version=1,
        authority="derived-evidence-only",
        invocation_id=invocation.invocation_id,
        table_id=plan.table_id,
        command=invocation.operation.value,
        outcome=outcome,
        seshat_exit_code=exit_code,
        started_at=invocation.started_at,
        completed_at=invocation.completed_at,
        elapsed_seconds=_elapsed(invocation.started_at, invocation.completed_at),
        plan_digest=plan_digest(plan),
        project_fingerprint=plan.project.sha256,
        mapping_path=plan.mapping.path,
        mapping_revision=plan.mapping.git_blob,
        runtime={
            "dbt_core": plan.runtime.dbt_core,
            "dbt_adapter": plan.runtime.dbt_adapter,
            "dbt_adapter_version": plan.runtime.dbt_adapter_version,
        },
        target={"name": plan.runtime.target, "schemas": asdict(plan.schemas)},
        selected_unique_ids=plan.selected_unique_ids,
        executed_unique_ids=_executed_unique_ids(artifacts),
        tests=tests,
        parity=parity,
        artifacts=_artifact_hashes(artifacts),
        blocking_reasons=blockers,
        readiness_effect="none; named-human approval required",
    )


def evidence_to_dict(evidence: RunEvidence) -> dict[str, Any]:
    """Convert evidence to its exact closed JSON shape."""

    return {
        "schema_version": evidence.schema_version,
        "authority": evidence.authority,
        "invocation_id": evidence.invocation_id,
        "table_id": evidence.table_id,
        "command": evidence.command,
        "outcome": evidence.outcome,
        "seshat_exit_code": evidence.seshat_exit_code,
        "started_at": evidence.started_at,
        "completed_at": evidence.completed_at,
        "elapsed_seconds": evidence.elapsed_seconds,
        "plan_digest": evidence.plan_digest,
        "project_fingerprint": evidence.project_fingerprint,
        "mapping_path": evidence.mapping_path,
        "mapping_revision": evidence.mapping_revision,
        "runtime": dict(evidence.runtime),
        "target": dict(evidence.target),
        "selected_unique_ids": list(evidence.selected_unique_ids),
        "executed_unique_ids": list(evidence.executed_unique_ids),
        "tests": asdict(evidence.tests),
        "parity": [asdict(row) for row in evidence.parity],
        "artifacts": dict(evidence.artifacts),
        "blocking_reasons": [
            _blocker_to_dict(blocker) for blocker in evidence.blocking_reasons
        ],
        "readiness_effect": evidence.readiness_effect,
    }


def _blocker_to_dict(blocker: Blocker) -> dict[str, Any]:
    row = {"code": blocker.code, "message": blocker.message}
    if blocker.assertion_id is not None:
        row["assertion_id"] = blocker.assertion_id
    return row


def _validate_evidence_identity(evidence: RunEvidence) -> None:
    if not _TABLE_ID.fullmatch(evidence.table_id):
        raise ArtifactIntegrityError("evidence table_id is unsafe")
    if not _INVOCATION_ID.fullmatch(evidence.invocation_id):
        raise ArtifactIntegrityError("evidence invocation_id is unsafe")
    expected_map = f"mappings/{evidence.table_id}/source-map.yaml"
    if evidence.mapping_path != expected_map:
        raise ArtifactIntegrityError("evidence mapping path does not match table_id")


def _require_repository_path(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise ArtifactIntegrityError("evidence path escapes the repository") from exc


def _mapping_directory(root: Path, evidence: RunEvidence) -> Path:
    mapping_dir = root / "mappings" / evidence.table_id
    if not mapping_dir.is_dir():
        raise ArtifactIntegrityError("evidence mapping directory is missing")
    _require_repository_path(mapping_dir, root)
    return mapping_dir


def _load_evidence_schema(root: Path) -> dict[str, Any]:
    schema_path = root / "schemas" / "dbt-run-evidence.schema.json"
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactIntegrityError("evidence JSON Schema is unavailable") from exc


def _sanitized_payload(root: Path, evidence: RunEvidence) -> dict[str, Any]:
    try:
        environment = load_child_environment(root)
    except EnvironmentConfigError as exc:
        raise ArtifactIntegrityError(
            "local environment could not be sanitized"
        ) from exc
    cleaned = sanitize(evidence_to_dict(evidence), secret_values(environment), root)
    if not isinstance(cleaned, dict):
        raise ArtifactIntegrityError("evidence payload could not be sanitized")
    return cleaned


def _evidence_directory(root: Path, mapping_dir: Path) -> Path:
    evidence_dir = mapping_dir / "dbt-evidence"
    if evidence_dir.exists():
        _require_repository_path(evidence_dir, root)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir


def _serialized_payload(cleaned: dict[str, Any]) -> str:
    return json.dumps(cleaned, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def _atomic_write(path: Path, payload: str) -> None:
    temporary = path.with_name(f".{path.name}.{token_hex(8)}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_evidence(repo_root: Path, evidence: RunEvidence) -> Path:
    """Sanitize, schema-check, and atomically write one evidence record."""

    root = Path(repo_root).resolve()
    _validate_evidence_identity(evidence)
    mapping_dir = _mapping_directory(root, evidence)
    schema = _load_evidence_schema(root)
    cleaned = _sanitized_payload(root, evidence)
    validate_evidence_payload(cleaned, schema)
    evidence_dir = _evidence_directory(root, mapping_dir)
    path = evidence_dir / f"{evidence.invocation_id}.json"
    _atomic_write(path, _serialized_payload(cleaned))
    return path
