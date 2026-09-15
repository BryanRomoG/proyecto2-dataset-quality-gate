"""Modelos Pydantic v2 del formato COCO exportado por el portal de anotación.

Reflejan uno a uno los esquemas Zod de `server/src/export/coco.schema.ts`
(la fuente de verdad del formato) para que un COCO mal formado se rechace
nombrando el campo exacto, en vez de fallar más adelante con un traceback
confuso en algún analizador.

Pydantic v2 real: field_validator, model_validator y ConfigDict. Nada de
la sintaxis de validación de la versión anterior de la librería.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

# [x, y, width, height] en píxeles absolutos.
CocoBbox = tuple[float, float, NonNegativeFloat, NonNegativeFloat]


def _reject_blank(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} no puede ser una cadena vacía o solo espacios")
    return stripped


class CocoInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    version: str
    date_created: str


class CocoCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: PositiveInt
    name: str = Field(min_length=1)
    supercategory: str = Field(min_length=1)

    @field_validator("name", "supercategory")
    @classmethod
    def not_blank(cls, value: str, info) -> str:
        return _reject_blank(value, info.field_name)


class CocoImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: PositiveInt
    file_name: str = Field(min_length=1)
    width: PositiveInt
    height: PositiveInt

    @field_validator("file_name")
    @classmethod
    def valid_file_name(cls, value: str) -> str:
        value = _reject_blank(value, "file_name")
        if "/" in value or "\\" in value or ".." in value:
            raise ValueError(
                f"file_name={value!r} no debe contener rutas ni '..' (solo el nombre del archivo)"
            )
        return value


class CocoAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: PositiveInt
    image_id: PositiveInt
    category_id: PositiveInt
    bbox: CocoBbox
    area: NonNegativeFloat
    iscrowd: Literal[0, 1]
    segmentation: list[list[float]]


class CocoDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: CocoInfo
    licenses: list[object]
    images: list[CocoImage]
    annotations: list[CocoAnnotation]
    categories: list[CocoCategory]

    @model_validator(mode="after")
    def check_references(self) -> "CocoDataset":
        """Valida que cada anotación apunte a una imagen y categoría reales.

        Un `image_id` o `category_id` huérfano no debe descubrirse hasta un
        analizador o un split más adelante: se rechaza aquí, nombrando la
        anotación y el campo exacto que quedó colgado.
        """
        image_ids = {image.id for image in self.images}
        category_ids = {category.id for category in self.categories}

        errors: list[str] = []
        for annotation in self.annotations:
            if annotation.image_id not in image_ids:
                errors.append(
                    f"annotation id={annotation.id}: image_id={annotation.image_id} "
                    "no corresponde a ninguna imagen del dataset (image_id huérfano)"
                )
            if annotation.category_id not in category_ids:
                errors.append(
                    f"annotation id={annotation.id}: category_id={annotation.category_id} "
                    "no corresponde a ninguna categoría del dataset"
                )

        if errors:
            raise ValueError("; ".join(errors))

        return self
