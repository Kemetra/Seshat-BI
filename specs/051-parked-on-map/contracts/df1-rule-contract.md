# Contract: DF1 Rule

## Signature

```python
@register("DF1", "Parked-on dependency edges reconcile with tracked-file evidence")
def check_parked_on(ctx: RuleContext) -> Iterable[Finding]: ...
```

- **Input**: `RuleContext(repo_root, tracked_files)` -- read-only. DF1 reads the
  manifest text, each cited `doc` text, and the `tracked_files` set. It opens no DB, no
  network, executes nothing (Principle VIII / never-execute B1).
- **Output**: an iterable of `Finding`, every one `rule_id="DF1"`,
  `severity=Severity.ERROR`. Empty iterable == clean.
- **Purity**: no global state, no writes, deterministic for a given `RuleContext`.

## Constants

```python
_MANIFEST = "docs/quality/parked-on.yaml"
_REQUIRED_FIELDS = ("id", "blocked", "parked_on", "doc", "anchor", "evidence")
# "shipped_when_tracked" is optional and NOT in _REQUIRED_FIELDS.
```

## Branches (in order; first match per concern emits and continues to next edge)

### Manifest-level (single finding, stop)

1. `_MANIFEST not in ctx.tracked_files` -> ERROR "manifest missing or untracked".
2. lazy `import yaml`; `yaml.safe_load` raises `YAMLError` -> ERROR "not valid YAML".
3. result is not a mapping, or `edges` is not a list -> ERROR "must be a mapping with
   an 'edges' list".
4. `edges == []` (present, well-formed, empty) -> **no finding** (clean, spec Q4).

### Per-edge (one finding per defect; independent across edges)

For each `edge` at index `i` (locator `docs/quality/parked-on.yaml:<id or #i>`):

5. `edge` is not a mapping -> ERROR "edge #i is not a mapping"; continue.
6. any field in `_REQUIRED_FIELDS` missing/empty -> ERROR "edge <id> missing required
   field(s): ..."; continue.
7. `edge["doc"] not in tracked` -> ERROR "edge <id> names doc <doc>, not a tracked
   file"; continue.
8. `edge["anchor"]` not a substring of `read_text(doc)` -> ERROR "edge <id> anchor not
   present in <doc> -- the park assertion moved or was removed"; continue.
9. `edge["evidence"] not in tracked` -> ERROR "edge <id> cites evidence <evidence>
   which is not a tracked file -- the blocker/park evidence does not resolve"; continue.
10. `edge.get("shipped_when_tracked")` is truthy AND in `tracked` -> ERROR "edge <id>
    asserts <blocked> is parked on <parked_on> but <shipped_when_tracked> now exists
    (tracked) -- the target shipped; the park is stale (parked-but-shipped)".

An edge that passes 5-10 yields no finding.

## Guarantees mapped to FR / SC

| Branch | FR | SC |
|---|---|---|
| 1 | FR-004 | SC-003 |
| 2-6 | FR-004 | SC-003 |
| 7-8 | FR-005 | SC-001 |
| 9 | FR-006 | SC-002 |
| 10 | FR-007 | SC-001 |
| ERROR severity throughout | FR-015 | -- |
| no score emitted | FR-008 | -- |
| only listed edges checked | FR-009 | -- |
| read-only, stdlib core | FR-010 | -- |

## Wiring contract

- `src/retail/rules/__init__.py`: add `parked_on` to the import tuple and `__all__`.
- `tests/unit/test_rules_wiring.py`: add `"DF1"` to `EXPECTED_RULE_IDS` (37 -> 38). The
  count assertion stays `len(...)`-derived.
- `docs/rules/rules-manifest.json`: regenerate via `retail manifest` (37 -> 38 entries);
  the rule-registry snapshot test guards equality with the live registry.
- No `EXPECTED_RULE_IDS` hard-coded number is touched; the known 40-raw-`@register`-vs-
  expected-set G6 gap is not relied upon and not fixed here.
