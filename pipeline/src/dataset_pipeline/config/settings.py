"""Configuración de entorno del pipeline, validada con pydantic-settings.

Si falta una variable requerida o llega con un valor no numérico, el proceso
debe fallar aquí, al arrancar, con un mensaje que nombre la variable — no más
adelante, a mitad de un analizador, con un error confuso.
"""

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Límite de tamaño (bytes) para las imágenes que procesan los analizadores.
    upload_max_bytes: PositiveInt
