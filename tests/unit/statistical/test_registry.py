"""The statistical method registry is closed and lazy."""

from __future__ import annotations

import subprocess
import sys

import pytest

from seshat.statistical.registry import (
    METHODS,
    MethodDescriptor,
    RegistryRefused,
    get_descriptor,
    load_runner,
)

pytestmark = pytest.mark.unit

_CATALOG = {
    "describe",
    "compare_groups",
    "proportion",
    "correlate",
    "regress",
    "detect_anomalies",
    "detect_change_points",
    "forecast",
}


def test_registry_contains_only_the_governed_catalog() -> None:
    assert set(METHODS) == _CATALOG
    assert all(key == descriptor.method_id for key, descriptor in METHODS.items())


def test_importing_registry_does_not_import_numerical_libraries() -> None:
    script = (
        "import sys; import seshat.statistical.registry; "
        "print(sorted(set(sys.modules) & "
        "{'numpy','scipy','statsmodels','ruptures','pandas'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "[]"


def test_unknown_method_is_refused() -> None:
    with pytest.raises(RegistryRefused, match="not governed"):
        get_descriptor("arbitrary_python")


def test_descriptor_outside_internal_methods_cannot_load() -> None:
    descriptor = MethodDescriptor(
        method_id="describe",
        version="1.0",
        module="os",
        function="system",
        required_roles=frozenset({"response"}),
        optional_dependency="statistics",
    )
    with pytest.raises(RegistryRefused, match="registered descriptor"):
        load_runner(descriptor)


def test_registered_descriptors_use_literal_internal_paths() -> None:
    assert all(
        descriptor.module.startswith("seshat.statistical.methods.")
        for descriptor in METHODS.values()
    )
    assert all("." not in descriptor.function for descriptor in METHODS.values())
