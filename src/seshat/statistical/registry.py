"""Closed string registry for governed statistical methods."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable

from .contracts import MethodContext, MethodResult


@dataclass(frozen=True, slots=True)
class MethodDescriptor:
    method_id: str
    version: str
    module: str
    function: str
    required_roles: frozenset[str]
    optional_dependency: str
    libraries: tuple[str, ...]


class RegistryRefused(ValueError):
    """A method identifier or descriptor is outside the governed catalog."""


_DESCRIPTORS = (
    MethodDescriptor(
        "describe",
        "1.0",
        "seshat.statistical.methods.descriptive",
        "run_describe",
        frozenset({"response"}),
        "stats",
        ("numpy", "scipy"),
    ),
    MethodDescriptor(
        "compare_groups",
        "1.0",
        "seshat.statistical.methods.groups",
        "run_compare_groups",
        frozenset({"response", "group"}),
        "stats",
        ("numpy", "scipy"),
    ),
    MethodDescriptor(
        "proportion",
        "1.0",
        "seshat.statistical.methods.proportions",
        "run_proportion",
        frozenset({"numerator", "denominator"}),
        "stats",
        ("numpy", "scipy"),
    ),
    MethodDescriptor(
        "correlate",
        "1.0",
        "seshat.statistical.methods.correlation",
        "run_correlate",
        frozenset({"response", "predictor"}),
        "stats",
        ("numpy", "scipy"),
    ),
    MethodDescriptor(
        "regress",
        "1.0",
        "seshat.statistical.methods.regression",
        "run_regress",
        frozenset({"response", "predictor"}),
        "stats",
        ("numpy", "scipy", "statsmodels"),
    ),
    MethodDescriptor(
        "detect_anomalies",
        "1.0",
        "seshat.statistical.methods.anomaly",
        "run_detect_anomalies",
        frozenset({"response", "time"}),
        "stats",
        ("numpy", "statsmodels"),
    ),
    MethodDescriptor(
        "detect_change_points",
        "1.0",
        "seshat.statistical.methods.changepoint",
        "run_detect_change_points",
        frozenset({"response", "time"}),
        "stats-change",
        ("numpy", "ruptures"),
    ),
    MethodDescriptor(
        "forecast",
        "1.0",
        "seshat.statistical.methods.forecast",
        "run_forecast",
        frozenset({"response", "time"}),
        "stats",
        ("numpy", "statsmodels"),
    ),
)

METHODS = MappingProxyType(
    {descriptor.method_id: descriptor for descriptor in _DESCRIPTORS}
)


def get_descriptor(method_id: str) -> MethodDescriptor:
    try:
        return METHODS[method_id]
    except KeyError:
        raise RegistryRefused(
            f"Statistical method {method_id!r} is not governed."
        ) from None


def load_runner(
    descriptor: MethodDescriptor,
) -> Callable[[MethodContext], MethodResult]:
    """Import only a literal callable from the closed internal registry."""

    registered = METHODS.get(descriptor.method_id)
    if registered != descriptor:
        raise RegistryRefused("Method runner requires a registered descriptor.")
    if not descriptor.module.startswith("seshat.statistical.methods."):
        raise RegistryRefused("Method module is outside the internal methods package.")
    module = importlib.import_module(descriptor.module)
    runner = getattr(module, descriptor.function, None)
    if not callable(runner) or not getattr(runner, "__module__", "").startswith(
        "seshat.statistical.methods"
    ):
        raise RegistryRefused("Registered method callable is invalid.")
    return runner
