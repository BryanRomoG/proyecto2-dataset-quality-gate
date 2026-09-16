from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.analyzers import analyze_spatial_bias

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f3-05-sesgo-espacial.feature"))


@given("un conjunto de áreas de cajas con distribución sesgada", target_fixture="context")
def skewed_areas() -> dict:
    return {"areas": [10.0, 12.0, 11.0, 13.0, 9.0, 500.0]}  # 500 es un outlier


@when("corre el analizador")
def run_analyzer(context: dict) -> None:
    context["report"] = analyze_spatial_bias(context["areas"])


@then("reporta media, mediana y percentiles")
def reports_full_stats(context: dict) -> None:
    report = context["report"]
    assert report.mean is not None
    assert report.median is not None
    assert report.p10 is not None and report.p90 is not None


@then("no reporta solo la media cuando la distribución está sesgada")
def does_not_report_only_the_mean(context: dict) -> None:
    report = context["report"]
    assert report.median != report.mean
