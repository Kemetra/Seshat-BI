"""Property test: the text (`run`) and JSON (`run_json`) output paths agree.

`run` iterates rules inline and prints one `_format` line per finding, while
`run_json` routes through `_collect`/`_exit_code` and emits a single JSON
document. Their agreement currently rests only on the docstring-asserted purity
of rules (see `runner._collect`). This test converts that convention into a
tested invariant over two properties:

* US1 -- the *multiset* of findings is identical (order-insensitive `Counter`
  over the four `FindingDict` fields).
* US2 -- the exit code is identical (1 iff any `Severity.ERROR`).

It is test-only: it imports `seshat.core` + `seshat.runner` ONLY (never
`seshat.rules`, never `psycopg2`, never a DB/network), adds no registered rule,
and does not touch `runner.py` / `core.py`. Fixtures are SYNTHETIC and generic
(no C086/pharmacy specifics) and are constrained so the text shape is
unambiguously invertible (no `") ("`, no brackets in messages/locators).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from seshat.core import Finding, RegisteredRule, RuleContext, Severity
from seshat.runner import run, run_json

# A (rule_id, severity-value, message, locator) tuple -- the equivalence key,
# exactly the four fields `Finding.to_dict` / `FindingDict` pin.
FindingKey = tuple[str, str, str, str]


def _ctx() -> RuleContext:
    """Mirror `tests/unit/test_runner.py`: a bare, non-git context."""
    return RuleContext(repo_root=Path("."), tracked_files=())


def _mixed_rules() -> tuple[RegisteredRule, ...]:
    """Synthetic rules covering every severity, with one rule yielding several
    findings. Ids/messages/locators are generic placeholders and contain no
    `") ("` or brackets, so the inverse text parse is unambiguous (FR-006)."""

    def errors_and_info(ctx: RuleContext):
        return [
            Finding("R1", Severity.ERROR, "first message", "a.txt:1"),
            Finding("R1", Severity.INFO, "second message", "a.txt:2"),
        ]

    def warning(ctx: RuleContext):
        return [Finding("R2", Severity.WARNING, "third message", "b.txt:9")]

    return (
        RegisteredRule(id="R1", rule=errors_and_info, title="r1"),
        RegisteredRule(id="R2", rule=warning, title="r2"),
    )


def _warning_only_rules() -> tuple[RegisteredRule, ...]:
    def warning(ctx: RuleContext):
        return [
            Finding("R2", Severity.WARNING, "heads up", "b.txt:9"),
            Finding("R3", Severity.INFO, "noted", "c.txt:3"),
        ]

    return (RegisteredRule(id="R2", rule=warning, title="r2"),)


def _empty_rules() -> tuple[RegisteredRule, ...]:
    def clean(ctx: RuleContext):
        return ()

    return (RegisteredRule(id="C0", rule=clean, title="clean"),)


def _parse_text_findings(text: str) -> Counter[FindingKey]:
    """Invert `_format` -- `"[{sev}] {rule_id} {message} ({locator})"` -- into a
    `Counter` of `(rule_id, severity, message, locator)` tuples.

    Relies on the fixture constraint (no `") ("`, no brackets in the free-text
    fields): severity is bounded by the first `]`, the locator by the final
    `(...)`, the rule_id is the first whitespace token after `]`, and the
    message is everything between. This is NOT a general-purpose robust parser
    (Q2: fixtures are pinned to be unambiguous instead)."""
    counter: Counter[FindingKey] = Counter()
    for line in text.splitlines():
        if not line.strip():
            continue  # ignore trailing/blank lines
        assert line.startswith("[") and "]" in line, f"unexpected line: {line!r}"
        sev_end = line.index("]")
        severity = line[1:sev_end]
        rest = line[sev_end + 1 :].strip()
        lpar = rest.rfind(" (")
        assert lpar != -1 and rest.endswith(")"), f"no locator in line: {line!r}"
        locator = rest[lpar + 2 : -1]
        head = rest[:lpar]
        rule_id, _, message = head.partition(" ")
        counter[(rule_id, severity, message, locator)] += 1
    return counter


def _json_findings_counter(out: str) -> Counter[FindingKey]:
    """Build a `Counter` of `(rule_id, severity, message, locator)` tuples from
    the `findings` array of the JSON document."""
    doc = json.loads(out)
    return Counter(
        (f["rule_id"], f["severity"], f["message"], f["locator"])
        for f in doc["findings"]
    )


@pytest.mark.unit
def test_text_and_json_findings_multisets_match(capsys):
    rules = _mixed_rules()
    ctx = _ctx()

    run(rules, ctx)
    text_counter = _parse_text_findings(capsys.readouterr().out)

    run_json(rules, ctx)
    json_counter = _json_findings_counter(capsys.readouterr().out)

    assert text_counter == json_counter


@pytest.mark.unit
def test_findings_parity_empty_rule_set(capsys):
    rules = _empty_rules()
    ctx = _ctx()

    run(rules, ctx)
    text_counter = _parse_text_findings(capsys.readouterr().out)

    run_json(rules, ctx)
    json_counter = _json_findings_counter(capsys.readouterr().out)

    assert text_counter == json_counter == Counter()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("rules_factory", "expected_code"),
    [
        (_mixed_rules, 1),  # an ERROR is present -> 1
        (_warning_only_rules, 0),  # WARNING/INFO only -> 0
        (_empty_rules, 0),  # no findings -> 0
    ],
)
def test_text_and_json_exit_codes_match(capsys, rules_factory, expected_code):
    rules = rules_factory()
    ctx = _ctx()

    text_code = run(rules, ctx)
    capsys.readouterr()  # drain so text output does not bleed into the JSON read

    json_code = run_json(rules, ctx)
    capsys.readouterr()

    assert text_code == json_code == expected_code
