import pytest

from dataset_pipeline.analyzers import analyze_spatial_bias


def test_reports_mean_median_and_percentiles() -> None:
    areas = [10.0, 12.0, 11.0, 13.0, 9.0, 500.0]  # 500 es un outlier que sesga la media

    report = analyze_spatial_bias(areas)

    assert report.count == 6
    assert report.mean == pytest.approx(sum(areas) / len(areas))
    assert report.median == pytest.approx(11.5)
    # La mediana queda muy por debajo de la media: la distribución está sesgada,
    # y el reporte lo deja ver porque siempre incluye ambas (nunca solo la media).
    assert report.median < report.mean
    assert report.p10 <= report.p25 <= report.median <= report.p75 <= report.p90


def test_empty_input_raises() -> None:
    with pytest.raises(ValueError, match="vacío"):
        analyze_spatial_bias([])
