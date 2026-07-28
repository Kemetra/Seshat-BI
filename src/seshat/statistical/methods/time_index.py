"""Strict regular-time-series preparation for governed statistical methods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..contracts import AnalysisWithheld, Blocker, MethodContext
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


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _parse(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise _withheld(
            "STAT_TIME_MISSING",
            "The governed time role contains a missing timestamp.",
            "Provide one timestamp for every approved observation.",
        )
    raw = value.strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _withheld(
            "STAT_TIME_UNPARSEABLE",
            f"The timestamp {raw!r} is not ISO-8601 parseable.",
            "Provide ISO-8601 timestamps at the declared cadence.",
        ) from exc


def _frequency(value: str) -> str:
    aliases = {
        "hourly": "hourly",
        "daily": "daily",
        "weekly": "weekly",
        "monthly": "monthly",
        "quarterly": "quarterly",
        "yearly": "yearly",
        "annual": "yearly",
    }
    try:
        return aliases[value.strip().casefold()]
    except KeyError:
        raise _withheld(
            "STAT_FREQUENCY_UNSUPPORTED",
            f"The declared cadence {value!r} is not a governed frequency.",
            "Use hourly, daily, weekly, monthly, quarterly, or yearly cadence.",
        ) from None


def _contiguous(previous: datetime, current: datetime, frequency: str) -> bool:
    if frequency == "hourly":
        return current - previous == timedelta(hours=1)
    if frequency == "daily":
        return current - previous == timedelta(days=1)
    if frequency == "weekly":
        return current - previous == timedelta(days=7)
    previous_month = previous.year * 12 + previous.month - 1
    current_month = current.year * 12 + current.month - 1
    month_step = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
    return (
        current_month - previous_month == month_step
        and current.day == previous.day
        and current.time() == previous.time()
    )


def regular_series(context: MethodContext) -> RegularSeries:
    """Normalize a unique, contiguous series at the specification cadence."""

    bindings = []
    for role in ("time", "response"):
        binding = context.spec.roles.get(role)
        if binding is None:
            raise _withheld(
                "STAT_METHOD_ROLE_MISSING",
                f"The governed {role} role is not bound.",
                "Bind time and response roles in the analysis specification.",
            )
        try:
            bindings.append(context.data.columns.index(binding.column))
        except ValueError as exc:
            raise _withheld(
                "STAT_PROVIDER_INVALID_DATA",
                f"The acquired data omits the governed {role} column.",
                "Repair the provider projection and rerun the analysis.",
            ) from exc
    parsed: list[tuple[datetime, str, object]] = []
    seen: set[datetime] = set()
    offsets = set()
    for row in context.data.rows:
        timestamp = _parse(row[bindings[0]])
        if timestamp in seen:
            raise _withheld(
                "STAT_TIME_DUPLICATE",
                "The governed time index contains duplicate timestamps.",
                "Aggregate or otherwise resolve duplicates at the approved grain.",
            )
        seen.add(timestamp)
        offsets.add(timestamp.utcoffset())
        value = row[bindings[1]]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise _withheld(
                "STAT_TIME_VALUE_MISSING",
                "The governed series contains a missing response value.",
                "Resolve the gap under an approved missing-data decision.",
            )
        parsed.append((timestamp, str(row[bindings[0]]).strip(), value))
    if len(offsets) > 1:
        raise _withheld(
            "STAT_TIMEZONE_MIXED",
            "The governed time index mixes timezone offsets or awareness.",
            "Normalize timestamps to one approved timezone.",
        )
    parsed.sort(key=lambda item: item[0])
    frequency = _frequency(context.spec.cadence)
    for previous, current in zip(parsed, parsed[1:], strict=False):
        if not _contiguous(previous[0], current[0], frequency):
            raise _withheld(
                "STAT_TIME_IRREGULAR",
                "The governed time index is not contiguous at the declared cadence.",
                "Resolve gaps or approve a regularized upstream dataset.",
            )
    values = finite_array((item[2] for item in parsed), "response")
    minimum = context.spec.minimum_data.get("observations", 1)
    if len(values) < minimum:
        raise _withheld(
            "STAT_MINIMUM_DATA",
            f"The series has {len(values)} observations; {minimum} are required.",
            "Provide more contiguous approved history.",
        )
    period = int(context.spec.method.parameters.get("period", 1))
    cycles = context.spec.minimum_data.get("seasonal_cycles", 0)
    if cycles and len(values) < period * cycles:
        raise _withheld(
            "STAT_SEASONAL_HISTORY",
            f"The series does not contain {cycles} complete seasonal cycles.",
            "Provide more contiguous approved history or revise the declared period.",
        )
    return RegularSeries(
        tuple(item[1] for item in parsed),
        values,
        frequency,
        period,
        None,
    )


def rolling_origins(
    length: int,
    initial_window: int,
    step: int = 1,
    max_folds: int | None = None,
) -> tuple[RollingOrigin, ...]:
    """Return chronological origins whose training endpoint precedes evaluation."""

    if (
        length < 1
        or initial_window < 1
        or step < 1
        or initial_window >= length
        or (max_folds is not None and max_folds < 1)
    ):
        raise ValueError("invalid rolling-origin bounds")
    origins = tuple(
        RollingOrigin(0, evaluate_index - 1, evaluate_index)
        for evaluate_index in range(initial_window, length, step)
    )
    if max_folds is not None:
        origins = origins[-max_folds:]
    return origins
