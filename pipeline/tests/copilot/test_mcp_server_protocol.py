"""SPEC-F8-01 (parte protocolo) — el Copilot es un servidor MCP real, no
solo funciones de Python con nombres parecidos a herramientas.

Levanta `dataset_pipeline.copilot.mcp_server` como subproceso real por
stdio (el mismo transporte que usaría Claude Desktop u otro cliente MCP) y
habla el protocolo MCP de verdad: `list_tools()` para ver el catálogo
declarado, `call_tool()` para invocar una y leer su resultado. Así se
prueba el servidor tal cual lo vería un cliente externo, no solo el import
directo de `CopilotToolkit` que ya cubre `test_tools_read_only.py`.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).parents[3]
DATA_DIR = REPO_ROOT / "contracts" / "examples"


async def _list_and_call(tool_name: str, arguments: dict | None = None):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "dataset_pipeline.copilot.mcp_server"],
        cwd=str(REPO_ROOT / "pipeline"),
        env={"COPILOT_DATA_DIR": str(DATA_DIR)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = None
            if tool_name:
                result = await session.call_tool(tool_name, arguments or {})
            return tools, result


def test_server_declares_exactly_the_four_read_only_tools() -> None:
    tools, _ = asyncio.run(_list_and_call(tool_name=None))
    names = {tool.name for tool in tools.tools}
    assert names == {
        "get_quality_report",
        "get_split_counts",
        "list_dataset_versions",
        "get_version_diff",
    }
    for tool in tools.tools:
        assert tool.description, f"{tool.name} no tiene descripción declarada"
        assert tool.input_schema, f"{tool.name} no tiene schema de parámetros declarado"


def test_calling_a_tool_over_the_real_protocol_returns_real_data() -> None:
    _, result = asyncio.run(_list_and_call("list_dataset_versions"))
    assert result.is_error is False
    [content] = result.content
    payload = json.loads(content.text)
    assert payload["current"] == "v0.2.0"
    assert {release["version"] for release in payload["releases"]} == {"v0.1.0", "v0.2.0"}
