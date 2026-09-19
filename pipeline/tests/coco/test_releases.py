import pytest

from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.releases import ReleaseTag, build_versions, semver_key


def _dataset(images_per_class: dict[str, int], small: int = 0) -> CocoDataset:
    """Dataset mínimo: una caja por imagen; `small` cajas son de 10x10 (< 32x32)."""
    categories = [
        {"id": index + 1, "name": name, "supercategory": "none"}
        for index, name in enumerate(images_per_class)
    ]
    images, annotations = [], []
    image_id = 0
    for category_index, (_, count) in enumerate(images_per_class.items()):
        for _ in range(count):
            image_id += 1
            side = 10 if len(annotations) < small else 100
            images.append(
                {"id": image_id, "file_name": f"{image_id}.jpg", "width": 200, "height": 200}
            )
            annotations.append(
                {
                    "id": image_id,
                    "image_id": image_id,
                    "category_id": category_index + 1,
                    "bbox": [0, 0, side, side],
                    "area": side * side,
                    "iscrowd": 0,
                    "segmentation": [],
                }
            )
    return CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "0", "date_created": "2026-01-01"},
            "licenses": [],
            "categories": categories,
            "images": images,
            "annotations": annotations,
        }
    )


def _tag(version: str) -> ReleaseTag:
    return ReleaseTag(version, f"release {version}", "2026-09-18T00:00:00-06:00", "abc1234")


def _build(tags, datasets, remote="in_sync", md5="deadbeef", min_images=5):
    return build_versions(
        tags,
        load_dataset=lambda version: datasets.get(version),
        dataset_md5=lambda version: md5,
        remote_status=lambda version, name: remote(version, name) if callable(remote) else remote,
        min_images_per_class=lambda version: min_images,
    )


def test_semver_key_orders_numerically_not_alphabetically() -> None:
    assert semver_key("v0.10.0") > semver_key("v0.9.0")


def test_semver_key_rejects_non_semver() -> None:
    with pytest.raises(ValueError, match="semántica"):
        semver_key("release-1")


def test_releases_are_sorted_by_semver_and_current_is_the_latest() -> None:
    tags = [_tag("v0.10.0"), _tag("v0.2.0"), _tag("v1.0.0"), _tag("v0.9.0")]

    result = _build(tags, {})

    assert [r["version"] for r in result["releases"]] == ["v0.2.0", "v0.9.0", "v0.10.0", "v1.0.0"]
    assert result["current"] == "v1.0.0"


def test_first_release_has_no_diff() -> None:
    result = _build([_tag("v0.1.0")], {"v0.1.0": _dataset({"car": 6})})

    assert result["releases"][0]["diff_vs_previous"] is None


def test_diff_reports_images_boxes_and_classes_leaving_the_minimum() -> None:
    datasets = {
        "v0.1.0": _dataset({"car": 6, "person": 6}),
        "v0.2.0": _dataset({"car": 6, "person": 3}),  # person sale del mínimo (5)
    }

    result = _build([_tag("v0.1.0"), _tag("v0.2.0")], datasets)
    diff = result["releases"][1]["diff_vs_previous"]

    assert diff["from"] == "v0.1.0"
    assert diff["to"] == "v0.2.0"
    assert diff["images_removed"] == 3
    assert diff["boxes_removed"] == 3
    assert diff["classes_left_minimum"] == ["person"]
    assert diff["classes_below_minimum"] == ["person"]
    assert diff["images_per_class"] == {"car": 6, "person": 3}


def test_diff_reports_the_change_in_small_objects_percentage() -> None:
    datasets = {"v0.1.0": _dataset({"car": 10}, small=0), "v0.2.0": _dataset({"car": 10}, small=5)}

    diff = _build([_tag("v0.1.0"), _tag("v0.2.0")], datasets)["releases"][1]["diff_vs_previous"]

    assert diff["small_objects_pct_before"] == 0.0
    assert diff["small_objects_pct_after"] == 50.0


def test_unreadable_dataset_keeps_the_release_without_inventing_a_diff() -> None:
    datasets = {"v0.1.0": _dataset({"car": 6}), "v0.3.0": _dataset({"car": 8})}  # v0.2.0 no se leyó

    result = _build([_tag("v0.1.0"), _tag("v0.2.0"), _tag("v0.3.0")], datasets)
    by_version = {r["version"]: r for r in result["releases"]}

    assert by_version["v0.2.0"]["diff_vs_previous"] is None
    # v0.3.0 se compara contra la última versión LEÍDA (v0.1.0), no contra un hueco.
    assert by_version["v0.3.0"]["diff_vs_previous"]["from"] == "v0.1.0"


def test_remote_status_is_reported_per_version_and_per_environment() -> None:
    def status(version: str, remote: str) -> str:
        return "missing" if (version, remote) == ("v0.1.0", "dev") else "in_sync"

    result = _build([_tag("v0.1.0"), _tag("v0.2.0")], {}, remote=status)
    first, second = result["releases"]

    assert first["remotes"] == {"dev": "missing", "prod": "in_sync"}
    assert second["remotes"] == {"dev": "in_sync", "prod": "in_sync"}


def test_no_tags_yields_an_empty_timeline() -> None:
    assert _build([], {}) == {"current": None, "releases": []}


def test_each_release_carries_a_snapshot_so_any_two_versions_can_be_compared() -> None:
    datasets = {"v0.1.0": _dataset({"car": 6, "person": 3}, small=2)}

    result = _build([_tag("v0.1.0"), _tag("v0.2.0")], datasets)
    first, second = result["releases"]

    assert first["snapshot"] == {
        "images": 9,
        "boxes": 9,
        "images_per_class": {"car": 6, "person": 3},
        "classes_below_minimum": ["person"],
        "small_objects_pct": pytest.approx(2 / 9 * 100),
    }
    # v0.2.0 no se pudo leer: sin foto, no una foto inventada.
    assert second["snapshot"] is None
