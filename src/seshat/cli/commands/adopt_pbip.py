"""CLI rendering and exit policy for ``seshat adopt-pbip``."""

from __future__ import annotations

import json
import sys
from typing import Any

from ...pbip_adoption import (
    PbipAdoptionError,
    assess_pbip,
    assessment_exit_code,
    render_assessment_text,
    render_scaffold_result_text,
    scaffold_exit_code,
    scaffold_pbip,
)


def _input_error(message: str, output_format: str) -> int:
    safe_message = "PBIP adoption input could not be assessed safely."
    if output_format == "json":
        print(
            json.dumps(
                {"outcome": "input_defect", "error": safe_message}, sort_keys=True
            )
        )
    else:
        print(f"error: {safe_message}", file=sys.stderr)
    return 2


def _emit(document: dict[str, Any], output_format: str, text_renderer) -> None:
    if output_format == "json":
        print(json.dumps(document, sort_keys=True, indent=2))
    else:
        print(text_renderer(document), end="")


def adopt_pbip_main(args: object) -> int:
    command = args.adopt_pbip_command  # type: ignore[attr-defined]
    output_format = args.output_format  # type: ignore[attr-defined]
    if command == "assess":
        try:
            assessment = assess_pbip(args.project)  # type: ignore[attr-defined]
        except PbipAdoptionError as exc:
            return _input_error(str(exc), output_format)
        _emit(assessment, output_format, render_assessment_text)
        return assessment_exit_code(assessment)
    result = scaffold_pbip(
        args.project,  # type: ignore[attr-defined]
        args.accept_assessment,  # type: ignore[attr-defined]
    )
    _emit(result, output_format, render_scaffold_result_text)
    return scaffold_exit_code(result)


__all__ = ["adopt_pbip_main"]
