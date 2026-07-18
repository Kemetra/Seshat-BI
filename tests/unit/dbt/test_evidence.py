from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dbt_artifacts"


@dataclass(frozen=True)
class ArtifactRoleCase:
    primary_count: int
    show_count: int
    primary_operation: str
    expected_error: str


def _sample_plan():
    from seshat.dbt.artifacts import load_manifest
    from seshat.dbt.contracts import (
        ExecutionPlan,
        ManifestBinding,
        MappingBinding,
        ProjectBinding,
        RuntimeBinding,
        ShadowSchemas,
    )

    return ExecutionPlan(
        schema_version=1,
        table_id="retail_store_sales",
        mapping=MappingBinding(
            path="mappings/retail_store_sales/source-map.yaml",
            git_blob="b" * 40,
            sha256="c" * 64,
            readiness_sha256="d" * 64,
            unresolved_questions_sha256="e" * 64,
            approval_id="approval-1",
        ),
        project=ProjectBinding(path="dbt", sha256="f" * 64),
        runtime=RuntimeBinding(
            dbt_core="1.12.0",
            dbt_adapter="dbt-postgres",
            dbt_adapter_version="1.10.2",
            profile="seshat_bi_warehouse",
            target="shadow",
            selector="seshat_table_retail_store_sales",
        ),
        schemas=ShadowSchemas(
            silver="seshat_dbt_shadow_silver",
            gold="seshat_dbt_shadow_gold",
            audit="seshat_dbt_shadow_audit",
        ),
        manifest=ManifestBinding(
            schema_uri="https://schemas.getdbt.com/dbt/manifest/v12.json",
            semantic_sha256=load_manifest(
                FIXTURES / "manifest-v12.json"
            ).semantic_sha256,
        ),
        selected_unique_ids=(
            # Fact model name matches the parity subjects' root (fct_sales_rss) so
            # the fact-subject coverage check resolves to a single built fact model.
            "model.seshat_bi.fct_sales_rss",
            "model.seshat_bi.stg_retail_store_sales",
            # The dimensions the build materialized -- the required parity set is
            # derived from these (one dimension_member_count per dim_* model).
            "model.seshat_bi.dim_customer_rss",
            "model.seshat_bi.dim_product_rss",
            "model.seshat_bi.dim_payment_method_rss",
            "model.seshat_bi.dim_location_rss",
            "model.seshat_bi.dim_date_rss",
            "test.seshat_bi.not_null_fact_transaction_id.abc123",
        ),
    )


def _invocation(return_code: int = 0):
    from seshat.dbt.contracts import InvocationResult, Operation

    return InvocationResult(
        invocation_id="20260716T120000Z-a1b2c3d4",
        operation=Operation.BUILD,
        argv_summary=("build", "--select", "selector:seshat_table_retail_store_sales"),
        return_code=return_code,
        started_at="2026-07-16T12:00:00Z",
        completed_at="2026-07-16T12:01:00Z",
        stdout="",
        stderr="private-host private-pass",
        target_dir=Path("ignored-target"),
        log_dir=Path("ignored-logs"),
    )


def _artifacts():
    from seshat.dbt.artifacts import load_manifest, load_run_results
    from seshat.dbt.contracts import ArtifactSet

    primary = load_run_results(FIXTURES / "run-results-v6.json")
    parity = replace(primary, which="show", sha256="a" * 64, results=())
    return ArtifactSet(
        manifest=load_manifest(FIXTURES / "manifest-v12.json"),
        run_results=(primary, parity),
    )


def _stdout(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_parity_rows_reads_dbt_1_12_preview_string() -> None:
    """dbt 1.12 `show --output json` emits the rows as a JSON string under
    'preview', not a native 'rows' list. The parser must decode it."""
    import json

    from seshat.dbt.evidence import parse_parity_rows

    preview_rows = [
        {
            "assertion_id": "fact_row_count",
            "assertion_class": "fact_row_count",
            "subject": "fct_x",
            "expected": "5",
            "actual": "5",
            "delta": "0",
            "tolerance": "0",
            "passed": True,
        }
    ]
    event = {"data": {"node_name": "audit_x", "preview": json.dumps(preview_rows)}}
    rows = parse_parity_rows(json.dumps(event) + "\n")

    assert len(rows) == 1
    assert rows[0].assertion_id == "fact_row_count"
    assert rows[0].passed is True


def test_parse_parity_rows_accepts_a_non_rss_tables_assertions() -> None:
    """Parity parsing is class-driven, not welded to retail_store_sales ids:
    a different table's assertion ids/subjects validate on the same rules, with
    tolerance derived from the class (0 for counts, 0.01 for money)."""
    import json

    from seshat.dbt.evidence import parse_parity_rows

    preview_rows = [
        {
            "assertion_id": "fact_distinct_grain_key",  # not an rss id
            "assertion_class": "business_key_count",
            "subject": "fct_widget_sales.grain",
            "expected": "100",
            "actual": "100",
            "delta": "0",
            "tolerance": "0",
            "passed": True,
        },
        {
            "assertion_id": "fact_net_amount_sum",
            "assertion_class": "additive_money_total",
            "subject": "fct_widget_sales.net_amount",
            "expected": "10.00",
            "actual": "10.01",
            "delta": "0.01",
            "tolerance": "0.01",  # derived from class, at the boundary -> passes
            "passed": True,
        },
    ]
    event = {"data": {"preview": json.dumps(preview_rows)}}
    rows = parse_parity_rows(json.dumps(event) + "\n")

    by_id = {row.assertion_id: row for row in rows}
    assert set(by_id) == {"fact_distinct_grain_key", "fact_net_amount_sum"}
    assert by_id["fact_net_amount_sum"].tolerance == "0.01"
    assert all(row.passed for row in rows)


def test_complete_parity_passes_and_money_delta_at_tolerance_passes() -> None:
    from seshat.dbt.evidence import parse_parity_rows

    rows = parse_parity_rows(_stdout("show-parity-pass.jsonl"))

    assert {row.assertion_id for row in rows} == {
        "fact_row_count",
        "fact_distinct_transaction_id",
        "fact_total_spent_sum",
        "dim_customer_member_count",
        "dim_product_member_count",
        "dim_payment_method_member_count",
        "dim_location_member_count",
        "dim_date_member_count",
    }
    assert all(row.passed for row in rows)
    money = next(row for row in rows if row.assertion_id == "fact_total_spent_sum")
    assert money.delta == "0.01"
    assert money.tolerance == "0.01"


def test_money_delta_above_tolerance_fails_with_concrete_blocker() -> None:
    from seshat.dbt.evidence import build_evidence, parse_parity_rows

    rows = parse_parity_rows(_stdout("show-parity-fail.jsonl"))
    evidence = build_evidence(_sample_plan(), _invocation(), _artifacts(), rows)

    money = next(row for row in rows if row.assertion_id == "fact_total_spent_sum")
    assert money.delta == "0.0101"
    assert money.passed is False
    assert evidence.outcome == "blocked"
    assert evidence.seshat_exit_code == 1
    assert evidence.blocking_reasons[0].assertion_id == "fact_total_spent_sum"
    assert "0.0101" in evidence.blocking_reasons[0].message


def test_missing_parity_row_blocks_even_with_green_tests() -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import build_evidence, parse_parity_rows

    rows = parse_parity_rows(_stdout("show-parity-missing.jsonl"))

    # The missing fixture drops dim_date_rss; the built set still has it, so the
    # dimension-subject coverage check blocks (a missing dimension, not just a
    # short count).
    with pytest.raises(ArtifactIntegrityError, match="missing dim_date_rss"):
        build_evidence(_sample_plan(), _invocation(), _artifacts(), rows)


def test_parity_with_right_count_but_wrong_dimension_subjects_is_blocked() -> None:
    """A malformed audit with the correct dimension_member_count COUNT but the
    wrong subject SET must block. This is the exact hole subject-blind counting
    left open: duplicate one dimension's check and omit another (two dim_customer,
    zero dim_date) -- the class count still equals the number of built dims, but
    the built dimension set is not covered.
    """
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.contracts import ParityAssertion
    from seshat.dbt.evidence import _validate_parity_set

    def _dim(subject: str) -> ParityAssertion:
        return ParityAssertion(
            assertion_id=f"{subject}_member_count",
            assertion_class="dimension_member_count",
            subject=subject,
            expected="1",
            actual="1",
            delta="0",
            tolerance="0",
            passed=True,
        )

    def _fact(assertion_id: str, cls: str) -> ParityAssertion:
        return ParityAssertion(
            assertion_id=assertion_id,
            assertion_class=cls,
            subject="fct_x",
            expected="1",
            actual="1",
            delta="0",
            tolerance="0",
            passed=True,
        )

    # built dims: dim_customer_x, dim_date_x. Audit covers dim_customer_x TWICE and
    # dim_date_x zero times -- count matches (2), subject set does not.
    selected = (
        "model.seshat_bi.fct_x",
        "model.seshat_bi.dim_customer_x",
        "model.seshat_bi.dim_date_x",
    )
    parity = (
        _fact("fact_row_count", "fact_row_count"),
        _fact("fact_grain", "business_key_count"),
        _fact("fact_money", "additive_money_total"),
        _dim("dim_customer_x"),
        # a second, distinct assertion still comparing dim_customer_x
        ParityAssertion(
            assertion_id="dim_customer_x_alt_count",
            assertion_class="dimension_member_count",
            subject="dim_customer_x",
            expected="1",
            actual="1",
            delta="0",
            tolerance="0",
            passed=True,
        ),
    )

    with pytest.raises(ArtifactIntegrityError, match="dimension"):
        _validate_parity_set(parity, selected)


def test_parity_accepts_multiple_money_measures_but_requires_at_least_one() -> None:
    """A fact with several additive money measures emits one additive_money_total
    row per measure -- that must pass (both subjects root at the built fact), and
    the class still requires at least one row. fact_row_count and
    business_key_count remain exactly-one singletons."""
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.contracts import ParityAssertion
    from seshat.dbt.evidence import _validate_parity_set

    def _row(assertion_id: str, cls: str, subject: str) -> ParityAssertion:
        return ParityAssertion(
            assertion_id=assertion_id,
            assertion_class=cls,
            subject=subject,
            expected="1",
            actual="1",
            delta="0",
            tolerance="0",
            passed=True,
        )

    selected = ("model.seshat_bi.fct_x", "model.seshat_bi.dim_only_x")
    base = [
        _row("fact_row_count", "fact_row_count", "fct_x"),
        _row("fact_grain", "business_key_count", "fct_x.grain"),
        _row("dim_only_x_member_count", "dimension_member_count", "dim_only_x"),
    ]

    # Two money measures on the same fact -> passes.
    two_money = tuple(
        base
        + [
            _row("fact_gross_sum", "additive_money_total", "fct_x.gross_amount"),
            _row("fact_net_sum", "additive_money_total", "fct_x.net_amount"),
        ]
    )
    _validate_parity_set(two_money, selected)  # no raise

    # Zero money measures -> still blocks ("at least one").
    no_money = tuple(base)
    with pytest.raises(ArtifactIntegrityError, match="additive_money_total"):
        _validate_parity_set(no_money, selected)


@pytest.mark.parametrize(
    "case",
    (
        ArtifactRoleCase(0, 1, "build", "exactly one primary"),
        ArtifactRoleCase(2, 1, "build", "exactly one primary"),
        ArtifactRoleCase(1, 0, "build", "exactly one show"),
        ArtifactRoleCase(1, 2, "build", "exactly one show"),
        ArtifactRoleCase(1, 1, "test", "does not match invocation"),
    ),
)
def test_build_evidence_enforces_artifact_roles(case: ArtifactRoleCase) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import build_evidence, parse_parity_rows

    artifacts = _artifacts()
    primary, show = artifacts.run_results
    changed = replace(
        artifacts,
        run_results=(replace(primary, which=case.primary_operation),)
        * case.primary_count
        + (show,) * case.show_count,
    )

    with pytest.raises(ArtifactIntegrityError, match=case.expected_error):
        build_evidence(
            _sample_plan(),
            _invocation(),
            changed,
            parse_parity_rows(_stdout("show-parity-pass.jsonl")),
        )


def test_duplicate_parity_ids_are_rejected() -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import parse_parity_rows

    stdout = _stdout("show-parity-pass.jsonl")
    events = [json.loads(line) for line in stdout.splitlines()]
    rows = events[-1]["data"]["preview"]["rows"]
    rows.append(rows[0])
    changed = "\n".join(json.dumps(event) for event in events)

    with pytest.raises(ArtifactIntegrityError, match="duplicate parity"):
        parse_parity_rows(changed)


def test_incorrect_reported_passed_boolean_is_rejected() -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import parse_parity_rows

    event = json.loads(_stdout("show-parity-fail.jsonl"))
    event["data"]["preview"]["rows"][2]["passed"] = True

    with pytest.raises(ArtifactIntegrityError, match="reported passed"):
        parse_parity_rows(json.dumps(event))


@pytest.mark.parametrize("count", (0, 2))
def test_show_requires_exactly_one_structured_result_event(count: int) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import parse_parity_rows

    event = _stdout("show-parity-pass.jsonl").splitlines()[-1]
    stdout = "\n".join([event] * count)

    with pytest.raises(ArtifactIntegrityError, match="exactly one"):
        parse_parity_rows(stdout)


def test_evidence_never_changes_readiness_authority() -> None:
    from seshat.dbt.evidence import (
        build_evidence,
        evidence_to_dict,
        parse_parity_rows,
    )

    evidence = build_evidence(
        _sample_plan(),
        _invocation(),
        _artifacts(),
        parse_parity_rows(_stdout("show-parity-pass.jsonl")),
    )
    payload = evidence_to_dict(evidence)

    assert payload["authority"] == "derived-evidence-only"
    assert payload["readiness_effect"] == "none; named-human approval required"
    assert "readiness_status" not in payload
    assert payload["outcome"] == "pass"
    assert payload["tests"] == {
        "passed": 1,
        "failed": 0,
        "errored": 0,
        "skipped": 0,
    }


def test_failed_invocation_emits_failed_outcome_without_raw_error() -> None:
    from seshat.dbt.evidence import build_evidence, evidence_to_dict, parse_parity_rows

    evidence = build_evidence(
        _sample_plan(),
        _invocation(return_code=1),
        _artifacts(),
        parse_parity_rows(_stdout("show-parity-pass.jsonl")),
    )
    payload = evidence_to_dict(evidence)

    assert payload["outcome"] == "failed"
    assert payload["seshat_exit_code"] == 1
    assert "private-host" not in json.dumps(payload)
    assert payload["blocking_reasons"][0]["code"] == "DBT_EXECUTION_FAILED"


def test_write_evidence_is_atomic_schema_valid_stable_and_readiness_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.evidence as module

    mapping_dir = tmp_path / "mappings" / "retail_store_sales"
    mapping_dir.mkdir(parents=True)
    readiness = mapping_dir / "readiness-status.yaml"
    readiness.write_text("stages: unchanged\n", encoding="utf-8")
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    runtime_schema = (
        Path(__file__).resolve().parents[3] / "schemas" / "dbt-run-evidence.schema.json"
    )
    schema_dir.joinpath("dbt-run-evidence.schema.json").write_bytes(
        runtime_schema.read_bytes()
    )
    monkeypatch.setattr(
        module,
        "load_child_environment",
        lambda root: {
            "SESHAT_DBT_HOST": "private-host",
            "SESHAT_DBT_PASSWORD": "private-pass",
        },
    )
    evidence = module.build_evidence(
        _sample_plan(),
        _invocation(),
        _artifacts(),
        module.parse_parity_rows(_stdout("show-parity-pass.jsonl")),
    )
    before = readiness.read_bytes()

    path = module.write_evidence(tmp_path, evidence)
    first = path.read_bytes()
    second_path = module.write_evidence(tmp_path, evidence)

    assert path == (mapping_dir / "dbt-evidence" / "20260716T120000Z-a1b2c3d4.json")
    assert second_path == path
    assert second_path.read_bytes() == first
    assert readiness.read_bytes() == before
    assert b"private-host" not in first and b"private-pass" not in first
    assert str(tmp_path).encode() not in first
    assert list(json.loads(first)) == sorted(json.loads(first))
    assert not list(path.parent.glob("*.tmp"))


def test_evidence_schema_rejects_additional_fields() -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import (
        build_evidence,
        evidence_to_dict,
        parse_parity_rows,
        validate_evidence_payload,
    )

    evidence = build_evidence(
        _sample_plan(),
        _invocation(),
        _artifacts(),
        parse_parity_rows(_stdout("show-parity-pass.jsonl")),
    )
    payload = evidence_to_dict(evidence)
    payload["readiness_status"] = "pass"
    runtime_schema = (
        Path(__file__).resolve().parents[3] / "schemas" / "dbt-run-evidence.schema.json"
    )
    schema = json.loads(runtime_schema.read_text(encoding="utf-8"))

    with pytest.raises(ArtifactIntegrityError, match="additional property"):
        validate_evidence_payload(payload, schema)


def test_write_evidence_rejects_table_path_escape(tmp_path: Path) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError
    from seshat.dbt.evidence import build_evidence, parse_parity_rows, write_evidence

    evidence = build_evidence(
        _sample_plan(),
        _invocation(),
        _artifacts(),
        parse_parity_rows(_stdout("show-parity-pass.jsonl")),
    )
    evidence = replace(evidence, table_id="../outside")

    with pytest.raises(ArtifactIntegrityError, match="evidence table_id"):
        write_evidence(tmp_path, evidence)
