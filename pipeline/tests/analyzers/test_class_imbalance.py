from dataset_pipeline.analyzers import analyze_class_imbalance


def test_majority_minority_ratio() -> None:
    report = analyze_class_imbalance({"car": 300, "person": 100}, min_images_per_class=300)

    assert report.majority_minority_ratio == 3.0


def test_classes_below_minimum() -> None:
    report = analyze_class_imbalance(
        {"car": 300, "person": 120, "bike": 50}, min_images_per_class=300
    )

    assert report.classes_below_minimum == ["bike", "person"]


def test_no_classes_below_minimum() -> None:
    report = analyze_class_imbalance({"car": 300, "person": 300}, min_images_per_class=300)

    assert report.classes_below_minimum == []
    assert report.majority_minority_ratio == 1.0


def test_report_is_strict_json_even_with_an_empty_class() -> None:
    import json

    report = analyze_class_imbalance({"car": 300, "person": 0}, min_images_per_class=300)

    # Un ratio infinito no puede salir como `Infinity` (no es JSON estándar):
    # jq, JSON.parse y cualquier lector estricto lo rechazan.
    payload = json.dumps(report.model_dump(mode="json"), allow_nan=False)
    assert json.loads(payload)["majority_minority_ratio"] is None
