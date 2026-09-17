import hashlib
import io

from PIL import Image, ImageDraw

from dataset_pipeline.analyzers import find_duplicate_pairs


def _sample_image() -> Image.Image:
    """Imagen sintética con contenido reconocible (no un lienzo liso), para
    que el pHash tenga estructura real que comparar."""
    img = Image.new("RGB", (200, 200), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 100, 140], fill=(200, 30, 30))
    draw.ellipse([90, 60, 180, 180], fill=(30, 90, 200))
    return img


def _recompress(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def test_exact_hash_misses_a_recompressed_copy() -> None:
    original = _sample_image()
    copy_recompressed = _recompress(original, quality=40)

    def sha256_of(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return hashlib.sha256(buffer.getvalue()).hexdigest()

    assert sha256_of(original) != sha256_of(copy_recompressed)


def test_phash_detects_a_recompressed_copy() -> None:
    original = _sample_image()
    copy_recompressed = _recompress(original, quality=40)

    report = find_duplicate_pairs(
        {1: original, 2: copy_recompressed}, distance_threshold=8
    )

    assert len(report.pairs) == 1
    pair = report.pairs[0]
    assert {pair.image_id_a, pair.image_id_b} == {1, 2}
    assert pair.similarity > 0.8


def test_unrelated_images_are_not_reported_as_duplicates() -> None:
    img_a = _sample_image()
    img_b = Image.new("RGB", (200, 200), color=(10, 10, 10))

    report = find_duplicate_pairs({1: img_a, 2: img_b}, distance_threshold=8)

    assert report.pairs == []
