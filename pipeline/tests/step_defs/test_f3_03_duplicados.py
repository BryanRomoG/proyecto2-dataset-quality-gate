import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw
from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.analyzers import find_duplicate_pairs

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f3-03-duplicados.feature"))


def _sample_image() -> Image.Image:
    img = Image.new("RGB", (200, 200), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 100, 140], fill=(200, 30, 30))
    draw.ellipse([90, 60, 180, 180], fill=(30, 90, 200))
    return img


def _sha256(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return hashlib.sha256(buffer.getvalue()).hexdigest()


@given("una imagen del dataset copiada con otro nombre y recomprimida", target_fixture="context")
def original_and_recompressed_copy() -> dict:
    original = _sample_image()

    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=40)  # "recomprimida" con otra calidad
    buffer.seek(0)
    copy_recompressed = Image.open(buffer).convert("RGB")

    return {"original": original, "copy": copy_recompressed}


@when("corre el analizador de pHash con umbral de distancia configurable")
def run_phash_analyzer(context: dict) -> None:
    context["report"] = find_duplicate_pairs(
        {1: context["original"], 2: context["copy"]}, distance_threshold=8
    )


@then("el par aparece reportado con su similitud")
def pair_is_reported_with_similarity(context: dict) -> None:
    pairs = context["report"].pairs
    assert len(pairs) == 1
    assert 0.0 < pairs[0].similarity <= 1.0


@then("un analizador que solo compare MD5/SHA exacto no cumple este escenario")
def exact_hash_would_miss_it(context: dict) -> None:
    assert _sha256(context["original"]) != _sha256(context["copy"])
