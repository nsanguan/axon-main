# Architecture Diagrams — Axon ASCP

This directory contains Excalidraw-formatted architecture diagrams for the Axon Agentic Supply Chain Planning framework.

## Files

| File | Contents |
|------|----------|
| `axon_architecture.excalidraw` | Full system architecture — 4-layer diagram showing MCP Servers → Connectors → Core (Agents + Orchestrator + Memory + Executive) → Infrastructure |

## How to View & Edit

1. Open [Excalidraw](https://excalidraw.com/)
2. Click **Folder icon** → **Load** → select the `.excalidraw` file
3. Edit as needed, save back to this directory

## Diagram Layers

```
┌──────────────────────────────────────────────────────┐
│  MCP Servers (Data Sources)                          │
│  Oracle EBS | SAP | Odoo | External RAG | Excalidraw │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│  Connectors (MCP Clients + Semantic Transformers)    │
│  mcp_oracle_ebs/ | mcp_sap/ | mcp_odoo/ | ...       │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│  Axon Core — 100% MCP-Native Architecture           │
│  ┌─────────┐ ┌──────────┐ ┌──────────────────┐      │
│  │ Agents  │ │Orchestr. │ │ Executive Agent   │      │
│  │ Comm/Ops│ │LangGraph │ │ Intent + Crisis   │      │
│  │ Tech    │ │+ Escalat │ │ 3 Golden Rules    │      │
│  └─────────┘ └──────────┘ └──────────────────┘      │
│  ┌──────────────────────────────────────┐            │
│  │ Memory: Short-term + Long-term       │            │
│  │ PostgresSaver + PostgresStore        │            │
│  └──────────────────────────────────────┘            │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│  Infrastructure                                      │
│  PostgreSQL 18 | Redis 7 | Docker Compose (7 svcs)  │
└──────────────────────────────────────────────────────┘
```
