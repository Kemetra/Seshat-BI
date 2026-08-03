"""The wording a governed code resolves to, per language.

Headings and caveats travel through the kit as CODES -- ``section.headline``,
``caveat.v04_discount`` -- because composing a sentence where the code is used
would put untranslated English on an Arabic page. That decision was made and then
left half-built: the surfaces placed the code itself into the visible heading, so
every report displayed ``section.headline`` to its reader and the emitted offline
document carried no resolver at all.

This module is the resolver. It is the only place report wording lives, which is
what makes "the same report in another language" a matter of adding a language
block rather than editing a template.

**An unresolved code refuses.** Rendering the code raw is the bug this closes;
rendering an empty heading hides it. Both are worse than declining to produce the
document, because a board pack with a blank section heading looks finished.

**It carries wording, never figures.** A vocabulary that could state a number
would be a second place a report's numbers come from, so a term whose key looks
like a figure is refused on load -- the same rule the print overlay lives under.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.report.model import ReportError
from seshat.report.reading import required_mapping, required_text

VOCABULARY_SCHEMA = "seshat.report-vocabulary/v1"
VOCABULARY_NAME = "report-vocabulary.yaml"

# Key fragments that would let wording state meaning, mirroring the print
# overlay's rule. A vocabulary entry is text a reader sees, never a quantity.
_FORBIDDEN_FRAGMENTS = ("value", "metric", "measure", "figure", "dax", "sql")


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """One language's wording, and nothing else."""

    language: str
    terms: Mapping[str, str]

    def text(self, code: str) -> str:
        """The wording for a code, or a refusal naming what is missing."""
        wording = self.terms.get(code)
        if not wording:
            raise ReportError(
                f"no {self.language!r} wording for governed code {code!r}. A surface "
                "may not display the code itself -- that is an internal identifier, "
                f"not a heading. Add {code!r} to the {VOCABULARY_NAME} for this table."
            )
        return wording

    def has(self, code: str) -> bool:
        return bool(self.terms.get(code))


def vocabulary_path(repo_root: Path, table: str) -> Path:
    return repo_root / "mappings" / table / "design" / VOCABULARY_NAME


def load_vocabulary(path: Path, language: str) -> Vocabulary:
    """One language's terms, or a refusal.

    A language the file does not carry refuses rather than falling back to another:
    falling back would put untranslated text beside correctly localised numbers,
    which reads as a finished document.
    """
    document = _document(path)
    _assert_schema(document, path)
    block = _language_block(document, path, language)
    return Vocabulary(language=language, terms=_terms(block, path))


def _document(path: Path) -> dict:
    """The parsed file, with an unreadable or non-mapping one refused by name."""
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReportError(
            f"no report vocabulary at {path}: {exc}. Headings and caveats are "
            "governed codes, so the wording has to be declared somewhere."
        ) from exc
    except yaml.YAMLError as exc:
        raise ReportError(f"cannot read report vocabulary {path}: {exc}") from exc
    return required_mapping(loaded, refusal=f"vocabulary {path} is not a mapping")


def _assert_schema(document: Mapping[str, object], path: Path) -> None:
    """The one schema this loader understands, checked before anything is read."""
    schema = required_text(
        document, "schema", refusal=f"vocabulary {path} declares no schema"
    )
    if schema != VOCABULARY_SCHEMA:
        raise ReportError(
            f"vocabulary {path} declares schema {schema!r}, not {VOCABULARY_SCHEMA!r}"
        )


def _language_block(
    document: Mapping[str, object], path: Path, language: str
) -> Mapping[str, object]:
    """The requested language's block, and never a different one."""
    languages = required_mapping(
        document.get("languages"),
        refusal=f"vocabulary {path} declares no languages",
    )
    block = languages.get(language)
    if not isinstance(block, dict) or not block:
        raise ReportError(
            f"vocabulary {path} carries no {language!r} block. Falling back to "
            "another language would put untranslated text beside correct numbers."
        )
    return block


def _terms(block: Mapping[str, object], path: Path) -> dict[str, str]:
    terms: dict[str, str] = {}
    for code, wording in block.items():
        _reject_meaning(str(code), path)
        if not isinstance(wording, str) or not wording:
            raise ReportError(
                f"vocabulary {path} term {code!r} has no wording; an empty heading "
                "hides the problem rather than stating it"
            )
        terms[str(code)] = wording
    return terms


def _reject_meaning(code: str, path: Path) -> None:
    lowered = code.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise ReportError(
                f"vocabulary {path} term {code!r}: wording cannot state a figure. A "
                "vocabulary that could carry a number would be a second place a "
                "report's numbers come from."
            )
