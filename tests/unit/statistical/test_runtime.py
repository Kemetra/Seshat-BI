"""Outcome-safe orchestration of policy, provider, methods, and evidence."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path, PurePosixPath
from types import MappingProxyType

import pytest

from seshat.ecosystem_contracts import validate_json_contract
from seshat.statistical.contracts import (
    AnalysisSpec,
    Blocker,
    ColumnBinding,
    Estimate,
    MethodSpec,
    Outcome,
)
from seshat.statistical.evidence import evidence_payload
from seshat.statistical.policy import PolicyContext, PolicyDecision
from seshat.statistical.providers.base import (
    ProviderProvenance,
    ProviderUnavailable,
    RectangularData,
)
from seshat.statistical.registry import MethodContext, MethodResult
from seshat.statistical.runtime import AnalysisWithheld, run_analysis
from seshat.statistical.schema import SpecRefused

pytestmark = pytest.mark.unit


def _spec() -> AnalysisSpec:
    return AnalysisSpec(
        schema_version="1.0",
        analysis_id="weekly_signal",
        revision=2,
        subject="sample",
        question="Is the metric changing?",
        cadence="weekly",
        owner="Example Analyst",
        readiness_status=PurePosixPath("mappings/sample/readiness-status.yaml"),
        metric_contracts=(
            PurePosixPath("mappings/sample/metrics/ApprovedMetric.yaml"),
        ),
        provider=MappingProxyType({"kind": "local_csv", "dataset_id": "weekly_metric"}),
        population=MappingProxyType(
            {
                "grain": "one row per completed week",
                "inclusion": (),
                "exclusion": (),
            }
        ),
        roles=MappingProxyType(
            {"response": ColumnBinding(column="metric_value", logical_type="number")}
        ),
        method=MethodSpec(
            "describe",
            "1.0",
            MappingProxyType({"quantiles": ("0.5",), "outlier_rule": "mad"}),
        ),
        missing_policy="complete_case",
        minimum_data=MappingProxyType(
            {"observations": 2, "groups": 1, "seasonal_cycles": 0}
        ),
        random_seed=1729,
        pii=MappingProxyType(
            {
                "classification": "none",
                "approval_evidence": (),
                "minimum_group_count": 5,
            }
        ),
        outputs=MappingProxyType(
            {
                "evidence": PurePosixPath(
                    "mappings/sample/analyses/weekly_signal.evidence.json"
                ),
                "review": PurePosixPath(
                    "mappings/sample/analyses/weekly_signal.review.md"
                ),
            }
        ),
        source_path=PurePosixPath("mappings/sample/analyses/weekly_signal.yaml"),
        source_sha256="a" * 64,
    )


def _context(root: Path) -> PolicyContext:
    return PolicyContext(
        subject="sample",
        readiness_path=root / "mappings/sample/readiness-status.yaml",
        readiness_revision="7",
        contracts=(),
        approved_tables=frozenset({"gold.sample"}),
        approved_columns=MappingProxyType({"gold.sample": frozenset({"metric_value"})}),
    )


def _data() -> RectangularData:
    return RectangularData(
        columns=("metric_value",),
        rows=(("10",), ("12",)),
        total_count=2,
        excluded_count=0,
        exclusion_reasons=(),
        provenance=ProviderProvenance(
            kind="local_csv",
            safe_label="local_csv:abc",
            data_digest="b" * 64,
            query_digest=None,
            snapshot_id=None,
        ),
    )


class Provider:
    def __init__(self, result=None, error: BaseException | None = None) -> None:
        self.result = result or _data()
        self.error = error
        self.calls = 0

    def fetch(self, request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def _allow(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(
        "seshat.statistical.runtime.evaluate_policy",
        lambda repo_root, spec: PolicyDecision(
            allowed=True, blockers=(), context=_context(root)
        ),
    )


def test_runtime_computes_after_policy_and_provider_preflight(
    tmp_path: Path, monkeypatch
) -> None:
    _allow(monkeypatch, tmp_path)
    versions = {"numpy": "2.5.1", "scipy": "1.18.0"}
    monkeypatch.setattr(
        "seshat.statistical.runtime.importlib.metadata.version",
        versions.__getitem__,
    )
    events: list[str] = []

    class OrderedProvider(Provider):
        def fetch(self, request):
            events.append("provider")
            return super().fetch(request)

    def load(descriptor):
        events.append("load")

        def runner(context: MethodContext) -> MethodResult:
            events.append("run")
            assert context.data.total_count == 2
            return MethodResult(estimates=(Estimate("mean", "11", "USD"),))

        return runner

    monkeypatch.setattr("seshat.statistical.runtime.load_runner", load)

    evidence = run_analysis(tmp_path, _spec(), OrderedProvider())

    assert events == ["provider", "load", "run"]
    assert evidence.outcome is Outcome.COMPUTED
    assert evidence.estimates == (Estimate("mean", "11", "USD"),)
    assert evidence.readiness_effect == "none; named-human approval required"
    assert evidence.input_provenance["source_digest"] == "b" * 64
    assert evidence.method["libraries"] == (
        {"name": "numpy", "version": "2.5.1"},
        {"name": "scipy", "version": "1.18.0"},
    )


def test_runtime_refuses_policy_without_calling_provider(
    tmp_path: Path, monkeypatch
) -> None:
    blocker = Blocker("STAT_GOLD_NOT_READY", "Gold is blocked.", "Validate Gold.")
    monkeypatch.setattr(
        "seshat.statistical.runtime.evaluate_policy",
        lambda repo_root, spec: PolicyDecision(False, (blocker,), None),
    )
    provider = Provider()

    evidence = run_analysis(tmp_path, _spec(), provider)

    assert evidence.outcome is Outcome.REFUSED
    assert evidence.blockers == (blocker,)
    assert provider.calls == 0


def test_runtime_refuses_a_method_version_it_cannot_execute(
    tmp_path: Path, monkeypatch
) -> None:
    # The registry ships one implementation per method id. Executing it for a
    # spec that declares a different version would file 1.0 computations as
    # another version's evidence.
    _allow(monkeypatch, tmp_path)
    loaded: list[object] = []
    monkeypatch.setattr(
        "seshat.statistical.runtime.load_runner",
        lambda descriptor: loaded.append(descriptor),
    )
    spec = replace(_spec(), method=MethodSpec("describe", "2.0", MappingProxyType({})))
    provider = Provider()

    evidence = run_analysis(tmp_path, spec, provider)

    assert evidence.outcome is Outcome.REFUSED
    assert evidence.blockers[0].code == "STAT_METHOD_VERSION_UNKNOWN"
    assert loaded == []
    assert provider.calls == 0


def test_runtime_converts_spec_refusal_to_refused(tmp_path: Path, monkeypatch) -> None:
    def refuse(repo_root, spec):
        raise SpecRefused(("$.method: invalid",))

    monkeypatch.setattr("seshat.statistical.runtime.evaluate_policy", refuse)
    evidence = run_analysis(tmp_path, _spec(), Provider())

    assert evidence.outcome is Outcome.REFUSED
    assert evidence.blockers[0].code == "STAT_SPEC_REFUSED"


def test_runtime_converts_method_withholding(tmp_path: Path, monkeypatch) -> None:
    _allow(monkeypatch, tmp_path)
    blocker = Blocker(
        "STAT_MINIMUM_DATA",
        "Too few complete observations.",
        "Provide more completed periods.",
    )

    def runner(context):
        raise AnalysisWithheld((blocker,))

    monkeypatch.setattr(
        "seshat.statistical.runtime.load_runner",
        lambda descriptor: runner,
    )

    evidence = run_analysis(tmp_path, _spec(), Provider())

    assert evidence.outcome is Outcome.WITHHELD
    assert evidence.blockers == (blocker,)


def test_runtime_converts_provider_unavailable(tmp_path: Path, monkeypatch) -> None:
    _allow(monkeypatch, tmp_path)
    blocker = Blocker(
        "STAT_PROVIDER_RESOURCE_LIMIT",
        "Input exceeds row ceiling.",
        "Narrow the input.",
    )
    provider = Provider(error=ProviderUnavailable(blocker))

    evidence = run_analysis(tmp_path, _spec(), provider)

    assert evidence.outcome is Outcome.UNAVAILABLE
    assert evidence.blockers == (blocker,)


def test_runtime_converts_missing_dependency_after_provider_preflight(
    tmp_path: Path, monkeypatch
) -> None:
    _allow(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "seshat.statistical.runtime.load_runner",
        lambda descriptor: (_ for _ in ()).throw(ImportError("scipy missing")),
    )
    provider = Provider()

    evidence = run_analysis(tmp_path, _spec(), provider)

    assert provider.calls == 1
    assert evidence.outcome is Outcome.UNAVAILABLE
    assert evidence.blockers[0].code == "STAT_DEPENDENCY_UNAVAILABLE"


def test_runtime_redacts_unexpected_failures(tmp_path: Path, monkeypatch) -> None:
    _allow(monkeypatch, tmp_path)

    def runner(context):
        raise ValueError("C:/private/customer.csv password=secret")

    monkeypatch.setattr(
        "seshat.statistical.runtime.load_runner",
        lambda descriptor: runner,
    )

    evidence = run_analysis(tmp_path, _spec(), Provider())
    payload = json.dumps(evidence_payload(evidence))

    assert evidence.outcome is Outcome.FAILED
    assert evidence.blockers[0].code == "STAT_RUNTIME_FAILED"
    assert "customer.csv" not in payload
    assert "secret" not in payload
    assert evidence.invocation_id


def test_runtime_does_not_catch_process_interrupts(tmp_path: Path, monkeypatch) -> None:
    _allow(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "seshat.statistical.runtime.load_runner",
        lambda descriptor: lambda context: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        run_analysis(tmp_path, _spec(), Provider())


def test_runtime_evidence_conforms_to_committed_schema(
    tmp_path: Path, monkeypatch
) -> None:
    _allow(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "seshat.statistical.runtime.load_runner",
        lambda descriptor: lambda context: MethodResult(),
    )
    evidence = run_analysis(tmp_path, _spec(), Provider())
    schema = json.loads(
        (
            Path(__file__).parents[3]
            / "schemas/statistical-analysis-evidence.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert validate_json_contract(evidence_payload(evidence), schema) == []
