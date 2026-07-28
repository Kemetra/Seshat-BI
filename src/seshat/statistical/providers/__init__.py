"""Rectangular data-provider contracts and built-in providers."""

from .base import (
    Aggregate,
    DataProvider,
    DataRequest,
    Filter,
    Join,
    ProviderProvenance,
    ProviderUnavailable,
    RectangularData,
    ResourceLimits,
    build_data_request,
)
from .gold import GoldProvider
from .local_csv import LocalCsvProvider

__all__ = [
    "Aggregate",
    "DataProvider",
    "DataRequest",
    "Filter",
    "GoldProvider",
    "Join",
    "LocalCsvProvider",
    "ProviderProvenance",
    "ProviderUnavailable",
    "RectangularData",
    "ResourceLimits",
    "build_data_request",
]
