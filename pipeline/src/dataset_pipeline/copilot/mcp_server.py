"""Servidor MCP del Dataset Copilot (T-3.3, issue #14): expone las cuatro
herramientas de solo lectura de `copilot.tools.CopilotToolkit` por stdio,
para que cualquier cliente MCP (Claude Desktop, Claude Code, u otro host
con un LLM) las pueda usar.

Este módulo es intencionalmente delgado: solo registra las herramientas y
arranca el transporte. La lógica de negocio (qué es cada herramienta, cómo
se lee cada contrato) vive en `copilot.tools`, así el servidor se prueba
como protocolo MCP (`tests/copilot/test_mcp_server_protocol.py`) sin
duplicar lo que ya cubre `test_tools_read_only.py`.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from dataset_pipeline.copilot.settings import CopilotSettings
from dataset_pipeline.copilot.tools import CopilotToolkit

REPO_ROOT = Path(__file__).resolve().parents[4]


def build_server(data_dir: Path | str | None = None) -> MCPServer:
    # Un valor relativo (el default de settings) se resuelve contra la raíz del
    # repo, no contra el cwd, para que el servidor funcione lanzado desde cualquier lado.
    configured = Path(data_dir or CopilotSettings().copilot_data_dir)
    toolkit = CopilotToolkit(configured if configured.is_absolute() else REPO_ROOT / configured)

    server = MCPServer("dataset-copilot")
    server.tool()(toolkit.get_quality_report)
    server.tool()(toolkit.get_split_counts)
    server.tool()(toolkit.list_dataset_versions)
    server.tool()(toolkit.get_version_diff)
    return server


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
