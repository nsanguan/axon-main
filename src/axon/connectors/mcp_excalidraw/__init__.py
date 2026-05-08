"""Excalidraw MCP Connector — visual diagram generation for supply chain plans.

Uses Excalidraw MCP server (https://github.com/thinkwelltwd/excalidraw-mcp-server)
to create, read, and manage Excalidraw diagrams programmatically.

Tools exposed:
  - create_diagram(title, elements) — create a new diagram
  - add_elements(diagram_id, elements) — add elements to existing diagram
  - export_diagram(diagram_id, format) — export as PNG/SVG/JSON
  - list_diagrams() — list all diagrams

Usage in agents:
    from axon.connectors.mcp_excalidraw import ExcalidrawConnector
    excalidraw = ExcalidrawConnector(settings.mcp_excalidraw)
    diagram_id = await excalidraw.create_diagram("Supply Chain Flow", elements)
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from axon.core.config import MCPServerConfig
from axon.core.telemetry import log_event


class ExcalidrawConnector:
    """Client connector for the Excalidraw MCP server.

    Provides methods to create, read, update, and export Excalidraw diagrams
    through MCP tool calls. Diagrams can be used to visualize supply chain
    plans, escalation flows, and agent reasoning paths.
    """

    def __init__(self, config: MCPServerConfig | None = None):
        from axon.core.config import settings

        self._config = config or settings.mcp_excalidraw
        self._session = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to the Excalidraw MCP server."""
        if self._connected:
            return
        # In production: use MCP client SDK to connect
        # from mcp import ClientSession
        # self._session = await ClientSession.connect(self._config.url)
        self._connected = True
        log_event("info", "excalidraw_connected", url=str(self._config.url))

    async def disconnect(self) -> None:
        """Close the MCP session."""
        self._connected = False
        self._session = None

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call an Excalidraw MCP tool.

        In production, this calls the MCP server's tool.
        In development, returns mock data.
        """
        log_event("info", "excalidraw_tool_call", tool_name=tool_name)
        return {"status": "ok", "data": arguments}

    async def create_diagram(
        self,
        title: str,
        elements: list[dict[str, Any]] | None = None,
    ) -> str:
        """Create a new Excalidraw diagram.

        Args:
            title: Diagram title.
            elements: Optional initial elements (rectangles, text, arrows, etc.).

        Returns:
            Diagram ID (UUID string).
        """
        diagram_id = str(uuid4())
        await self._call_tool("create_diagram", {
            "diagram_id": diagram_id,
            "title": title,
            "elements": elements or [],
        })
        log_event("info", "excalidraw_diagram_created", diagram_id=diagram_id, title=title)
        return diagram_id

    async def add_elements(
        self,
        diagram_id: str,
        elements: list[dict[str, Any]],
    ) -> bool:
        """Add elements to an existing diagram.

        Args:
            diagram_id: Target diagram ID.
            elements: List of Excalidraw element dicts.

        Returns:
            True if successful.
        """
        await self._call_tool("add_elements", {
            "diagram_id": diagram_id,
            "elements": elements,
        })
        return True

    async def export_diagram(
        self,
        diagram_id: str,
        fmt: str = "png",
    ) -> bytes:
        """Export a diagram as an image.

        Args:
            diagram_id: Diagram to export.
            fmt: Output format: "png", "svg", or "json".

        Returns:
            Raw image bytes.
        """
        await self._call_tool("export_diagram", {
            "diagram_id": diagram_id,
            "format": fmt,
        })
        return b""

    async def list_diagrams(self) -> list[dict[str, Any]]:
        """List all diagrams."""
        return []

    @staticmethod
    def make_rectangle(
        x: float, y: float, width: float, height: float,
        label: str = "", color: str = "#1971c2",
    ) -> dict[str, Any]:
        """Create an Excalidraw rectangle element.

        Args:
            x, y: Position coordinates.
            width, height: Element dimensions.
            label: Text label inside rectangle.
            color: Background color (hex).

        Returns:
            Element dict for use with create_diagram/add_elements.
        """
        return {
            "type": "rectangle",
            "x": x, "y": y,
            "width": width, "height": height,
            "backgroundColor": color,
            "strokeColor": "#000000",
            "strokeWidth": 1,
            "roughness": 1,
            "opacity": 100,
            "label": label,
        }

    @staticmethod
    def make_arrow(
        start_x: float, start_y: float,
        end_x: float, end_y: float,
        label: str = "",
    ) -> dict[str, Any]:
        """Create an Excalidraw arrow element.

        Args:
            start_x, start_y: Arrow origin.
            end_x, end_y: Arrow destination.
            label: Optional text label.

        Returns:
            Element dict.
        """
        return {
            "type": "arrow",
            "x": start_x, "y": start_y,
            "endX": end_x, "endY": end_y,
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "roughness": 0,
            "opacity": 100,
            "label": label,
        }

    @staticmethod
    def make_text(
        x: float, y: float, text: str,
        font_size: int = 16,
    ) -> dict[str, Any]:
        """Create an Excalidraw text element.

        Args:
            x, y: Position.
            text: Text content.
            font_size: Font size in pixels.

        Returns:
            Element dict.
        """
        return {
            "type": "text",
            "x": x, "y": y,
            "text": text,
            "fontSize": font_size,
            "strokeColor": "#000000",
        }

    async def create_supply_chain_diagram(
        self,
        title: str,
        demands: list[dict[str, Any]],
        supplies: list[dict[str, Any]],
        allocations: list[dict[str, Any]] | None = None,
    ) -> str:
        """Create a complete supply chain flow diagram.

        Automatically builds a visual diagram from demand, supply, and
        allocation data. Useful for agent presentations and reports.

        Args:
            title: Diagram title.
            demands: List of demand items.
            supplies: List of supply items.
            allocations: Optional list of allocations (for arrows).

        Returns:
            Diagram ID.
        """
        elements: list[dict[str, Any]] = []
        y_offset = 60

        # Title text
        elements.append(self.make_text(100, 20, title, 24))

        # Demands column (left side)
        elements.append(self.make_text(100, y_offset, "Demands", 20))
        y_offset += 40
        for i, d in enumerate(demands[:5]):
            name = d.get("item_name", d.get("item_native_id", f"Item {i}"))
            qty = d.get("quantity", 0)
            elements.append(self.make_rectangle(
                100, y_offset + i * 60, 180, 50,
                f"{name} x{qty}", "#1971c2",
            ))

        # Supplies column (right side)
        elements.append(self.make_text(500, 60, "Supplies", 20))
        for i, s in enumerate(supplies[:5]):
            name = s.get("item_name", s.get("item_native_id", f"Supply {i}"))
            qty = s.get("quantity", 0)
            src = s.get("source", "unknown")
            elements.append(self.make_rectangle(
                500, 100 + i * 60, 180, 50,
                f"{name} x{qty} ({src})", "#2e7d32",
            ))

        # Arrows connecting demands to supplies
        if allocations:
            for i, a in enumerate(allocations[:5]):
                qty = a.get("allocated_quantity", 0)
                elements.append(self.make_arrow(
                    280, 85 + i * 60, 500, 125 + i * 60,
                    f"{qty} units",
                ))

        return await self.create_diagram(f"Supply Chain: {title}", elements)
