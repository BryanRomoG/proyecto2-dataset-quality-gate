"""SPEC-F3-05 — Sesgo espacial y estadística descriptiva real.

Nunca reporta solo la media: siempre incluye mediana y percentiles, para que
una distribución sesgada (donde media y mediana divergen) sea visible en el
propio reporte, no solo en un número que la esconde.
"""

import statistics

from pydantic import BaseModel, ConfigDict


class SpatialBiasReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    mean: float
    median: float
    p10: float
    p25: float
    p75: float
    p90: float


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (percentile / 100) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def analyze_spatial_bias(areas: list[float]) -> SpatialBiasReport:
    if not areas:
        raise ValueError("areas no puede estar vacío")

    ordered = sorted(areas)

    return SpatialBiasReport(
        count=len(areas),
        mean=statistics.mean(areas),
        median=statistics.median(areas),
        p10=_percentile(ordered, 10),
        p25=_percentile(ordered, 25),
        p75=_percentile(ordered, 75),
        p90=_percentile(ordered, 90),
    )
