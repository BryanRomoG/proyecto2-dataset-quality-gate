"""Configuración del Copilot, separada de `config/settings.py` a propósito:
el resto del pipeline (analizadores, compuerta) no necesita ni debe fallar
si falta `GEMINI_API_KEY` -- solo el Copilot la necesita, y solo cuando de
verdad habla con el LLM (no para correr sus pruebas, que usan un doble).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class CopilotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nunca versionada (AC del issue #14): sale de .env en local, de un
    # Secrets Manager en producción. None si no está configurada -- lo que
    # intenta usarla en ese caso da un error claro, no un traceback de
    # autenticación del SDK de Google.
    gemini_api_key: str | None = None
    # "gemini-2.5-flash" y el alias "gemini-flash-latest" fallaron en
    # desarrollo (404 por retiro de versión, y 503 por alta demanda del
    # alias más usado; documentado en SPECS.md). "gemini-3.5-flash-lite" es
    # el modelo con el que se verificó una llamada real end-to-end.
    gemini_model: str = "gemini-3.5-flash-lite"
    copilot_data_dir: str = "contracts/examples"
