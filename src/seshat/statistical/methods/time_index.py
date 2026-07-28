"""Strict regular-time-series preparation for governed statistical methods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

from ..contracts import AnalysisWithheld, MethodContext, require, withheld
from .common import finite_array


@dataclass(frozen=True, slots=True)
class RegularSeries:
    timestamps: tuple[str, ...]
    values: object
    frequency: str
    seasonal_period: int
    excluded_partial_period: str | None


@dataclass(frozen=True, slots=True)
class RollingOrigin:
    train_start: int
    source_end: int
    evaluate_index: int


_Observation = tuple[datetime, str, object]

_FREQUENCY_ALIASES = {
    "hourly": "hourly",
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
    "quarterly": "quarterly",
    "yearly": "yearly",
    "annual": "yearly",
}

_FIXED_STEPS = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}

_MONTH_STEPS = {"monthly": 1, "quarterly": 3, "yearly": 12}


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _parse(value: object) -> datetime:
    require(
        isinstance(value, str) and value.strip(),
        "STAT_TIME_MISSING",
        "The governed time role contains a missing timestamp.",
        "Provide one timestamp for every approved observation.",
    )
    raw = str(value).strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _withheld(
            "STAT_TIME_UNPARSEABLE",
            f"The timestamp {raw!r} is not ISO-8601 parseable.",
            "Provide ISO-8601 timestamps at the declared cadence.",
        ) from exc


def _frequency(value: str) -> str:
    frequency = _FREQUENCY_ALIASES.get(value.strip().casefold())
    require(
        frequency is not None,
        "STAT_FREQUENCY_UNSUPPORTED",
        f"The declared cadence {value!r} is not a governed frequency.",
        "Use hourly, daily, weekly, monthly, quarterly, or yearly cadence.",
    )
    return str(frequency)


def _contiguous(previous: datetime, current: datetime, frequency: str) -> bool:
    fixed_step = _FIXED_STEPS.get(frequency)
    if fixed_step is not None:
        return current - previous == fixed_step
    months = (current.year - previous.year) * 12 + current.month - previous.month
    same_position = current.day == previous.day and current.time() == previous.time()
    return months == _MONTH_STEPS[frequency] and same_position


def _role_indexes(context: MethodContext) -> tuple[int, ...]:
    """Locate the time and response columns the governed roles bind."""

    indexes: list[int] = []
    for role in ("time", "response"):
        binding = context.spec.roles.get(role)
        require(
            binding is not None,
            "STAT_METHOD_ROLE_MISSING",
            f"The governed {role} role is not bound.",
            "Bind time and response roles in the analysis specification.",
        )
        try:
            indexes.append(context.data.columns.index(binding.column))
        except ValueError as exc:
            raise _withheld(
                "STAT_PROVIDER_INVALID_DATA",
                f"The acquired data omits the governed {role} column.",
                "Repair the provider projection and rerun the analysis.",
            ) from exc
    return tuple(indexes)


def _observations(context: MethodContext, roles: tuple[int, ...]) -> list[_Observation]:
    """Parse every row into (timestamp, raw timestamp text, response value)."""

    time_index, value_index = roles
    parsed: list[_Observation] = []
    seen: set[datetime] = set()
    offsets: set[timedelta | None] = set()
    for row in context.data.rows:
        timestamp = _parse(row[time_index])
        require(
            timestamp not in seen,
            "STAT_TIME_DUPLICATE",
            "The governed time index contains duplicate timestamps.",
            "Aggregate or otherwise resolve duplicates at the approved grain.",
        )
        seen.add(timestamp)
        offsets.add(timestamp.utcoffset())
        value = row[value_index]
        require(
            value is not None and (not isinstance(value, str) or value.strip()),
            "STAT_TIME_VALUE_MISSING",
            "The governed series contains a missing response value.",
            "Resolve the gap under an approved missing-data decision.",
        )
        parsed.append((timestamp, str(row[time_index]).strip(), value))
    require(
        len(offsets) <= 1,
        "STAT_TIMEZONE_MIXED",
        "The governed time index mixes timezone offsets or awareness.",
        "Normalize timestamps to one approved timezone.",
    )
    parsed.sort(key=lambda item: item[0])
    return parsed


def _without_partial_period(
    parsed: list[_Observation], parameters: Mapping[str, object]
) -> tuple[list[_Observation], str | None]:
    """Drop a declared partial final period, but only under an explicit policy."""

    if parameters.get("final_period", "complete") != "partial":
        return parsed, None
    require(
        parameters.get("partial_period_policy", "fail") == "exclude",
        "STAT_PARTIAL_PERIOD",
        "The final observation is declared partial and policy forbids use.",
        "Complete the period or approve explicit exclusion.",
    )
    if not parsed:
        return parsed, None
    return parsed[:-1], parsed[-1][1]


def _assert_contiguous(parsed: Sequence[_Observation], frequency: str) -> None:
    require(
        all(
            _contiguous(previous[0], current[0], frequency)
            for previous, current in zip(parsed, parsed[1:], strict=False)
        ),
        "STAT_TIME_IRREGULAR",
        "The governed time index is not contiguous at the declared cadence.",
        "Resolve gaps or approve a regularized upstream dataset.",
    )


def _assert_history(context: MethodContext, values, period: int) -> None:
    """Hold the declared observation floor and seasonal-cycle floor."""

    minimum = context.spec.minimum_data.get("observations", 1)
    require(
        len(values) >= minimum,
        "STAT_MINIMUM_DATA",
        f"The series has {len(values)} observations; {minimum} are required.",
        "Provide more contiguous approved history.",
    )
    cycles = context.spec.minimum_data.get("seasonal_cycles", 0)
    require(
        not cycles or len(values) >= period * cycles,
        "STAT_SEASONAL_HISTORY",
        f"The series does not contain {cycles} complete seasonal cycles.",
        "Provide more contiguous approved history or revise the declared period.",
    )


def regular_series(context: MethodContext) -> RegularSeries:
    """Normalize a unique, contiguous series at the specification cadence."""

    parameters = context.spec.method.parameters
    parsed = _observations(context, _role_indexes(context))
    parsed, excluded_partial_period = _without_partial_period(parsed, parameters)
    frequency = _frequency(context.spec.cadence)
    _assert_contiguous(parsed, frequency)
    values = finite_array((item[2] for item in parsed), "response")
    period = int(parameters.get("period", 1))
    _assert_history(context, values, period)
    return RegularSeries(
        tuple(item[1] for item in parsed),
        values,
        frequency,
        period,
        excluded_partial_period,
    )


def rolling_origins(
    length: int,
    initial_window: int,
    step: int = 1,
    max_folds: int | None = None,
) -> tuple[RollingOrigin, ...]:
    """Return chronological origins whose training endpoint precedes evaluation."""

    bounds = (
        length >= 1,
        initial_window >= 1,
        step >= 1,
        initial_window < length,
        max_folds is None or max_folds >= 1,
    )
    if not all(bounds):
        raise ValueError("invalid rolling-origin bounds")
    origins = tuple(
        RollingOrigin(0, evaluate_index - 1, evaluate_index)
        for evaluate_index in range(initial_window, length, step)
    )
    return origins if max_folds is None else origins[-max_folds:]
