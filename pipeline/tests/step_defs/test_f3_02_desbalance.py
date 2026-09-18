from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.analyzers import analyze_class_imbalance

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f3-02-desbalance.feature"))


@given("conteos de imágenes por clase", target_fixture="context")
def counts_per_class() -> dict:
    return {"counts": {"car": 300, "person": 100}, "min_images_per_class": 300}


@when("corre el analizador")
def run_analyzer(context: dict) -> None:
    context["report"] = analyze_class_imbalance(
        context["counts"], context["min_images_per_class"]
    )


@then("reporta el ratio clase mayoritaria / minoritaria")
def reports_ratio(context: dict) -> None:
    assert context["report"].majority_minority_ratio == 3.0


@then("lista las clases por debajo del mínimo configurado")
def lists_classes_below_minimum(context: dict) -> None:
    assert context["report"].classes_below_minimum == ["person"]
