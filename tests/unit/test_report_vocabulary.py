"""The resolver for governed codes, and the caveats that ride with it.

Two defects met here. Surfaces displayed `section.headline` to readers because the
code was placed straight into the visible heading and the offline document carried
no resolver. And the caveat the signed binding map REQUIRES for v04 could not reach
any surface, because every bundle set `caveats` to empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seshat.report.model import ReportError
from seshat.report.vocabulary import (
    VOCABULARY_SCHEMA,
    Vocabulary,
    load_vocabulary,
    vocabulary_path,
)

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_DOC = {
    "schema": VOCABULARY_SCHEMA,
    "table": "demo_table",
    "languages": {
        "en": {"cover.x": "Cover", "section.a": "Section A"},
        "ar": {"cover.x": "الغلاف", "section.a": "القسم الأول"},
    },
}


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "report-vocabulary.yaml"
    path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")
    return path


def test_a_code_resolves_to_its_wording(tmp_path: Path) -> None:
    vocabulary = load_vocabulary(_write(tmp_path, _DOC), "en")
    assert vocabulary.text("section.a") == "Section A"
    assert vocabulary.language == "en"


def test_each_language_resolves_independently(tmp_path: Path) -> None:
    assert load_vocabulary(_write(tmp_path, _DOC), "ar").text("cover.x") == "الغلاف"


def test_an_unresolved_code_refuses_rather_than_showing_the_code() -> None:
    """Displaying `section.headline` was the defect; an empty heading hides it."""
    with pytest.raises(ReportError, match="no 'en' wording for governed code"):
        Vocabulary(language="en", terms={}).text("section.headline")


def test_a_missing_file_refuses(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="no report vocabulary"):
        load_vocabulary(tmp_path / "absent.yaml", "en")


def test_a_language_the_file_does_not_carry_refuses(tmp_path: Path) -> None:
    """Falling back would put untranslated text beside correct numbers."""
    with pytest.raises(ReportError, match="carries no 'fr' block"):
        load_vocabulary(_write(tmp_path, _DOC), "fr")


def test_a_wrong_schema_refuses(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="declares schema"):
        load_vocabulary(_write(tmp_path, {**_DOC, "schema": "something/v9"}), "en")


def test_an_empty_wording_refuses(tmp_path: Path) -> None:
    document = {**_DOC, "languages": {"en": {"section.a": ""}}}
    with pytest.raises(ReportError, match="has no wording"):
        load_vocabulary(_write(tmp_path, document), "en")


@pytest.mark.parametrize(
    "code", ["figure.total", "metric.sales", "value.x", "measure.y", "sql.q", "dax.d"]
)
def test_a_term_that_would_state_a_figure_refuses(tmp_path: Path, code: str) -> None:
    """A vocabulary that could carry a number would be a second place a report's
    numbers come from."""
    document = {**_DOC, "languages": {"en": {code: "1,552,071.00"}}}
    with pytest.raises(ReportError, match="cannot state a figure"):
        load_vocabulary(_write(tmp_path, document), "en")


def test_the_shipped_vocabulary_loads_and_carries_the_required_caveat() -> None:
    """The binding map requires v04 to footnote its known-status basis."""
    vocabulary = load_vocabulary(vocabulary_path(_REPO, "retail_store_sales"), "en")
    caveat = vocabulary.text("caveat.v04_discount_known_status")
    assert "33.39%" in caveat  # the unknown-status share
    assert "33.55%" in caveat  # the floor the binding map names
    assert vocabulary.text("section.headline") == "Headline"
