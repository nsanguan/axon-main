# ADR-001: Pure MCP Architecture (No Direct Database Connections)

- **Status**: Accepted
- **Date**: 2026-05-08
- **Deciders**: nsanguan

## Context

Axon must integrate with multiple ERP systems (Oracle EBS, SAP, Odoo)
and an external knowledge base (RAG server). The traditional approach —
direct JDBC/ORDS connections to each ERP database — creates tight coupling,
requires per-ERP SQL knowledge, and breaks when ERP schemas change.

The Model Context Protocol (MCP) offers a standardized way for AI agents
to discover and call tools on remote systems. MCP servers wrap ERP
functionality as typed tools with JSON schemas, decoupling the AI
from the database layer entirely.

## Decision

**Axon will use MCP as the exclusive protocol for all external system
access. No direct database connections (JDBC, ORDS, ODBC) will exist in
the Axon codebase.**

Every ERP and the RAG server will be accessed through an MCP server that
exposes tools. Axon's connector layer will be pure MCP clients.

## Consequences

### Positive

- **ERP-agnostic**: swapping Oracle EBS for SAP requires only pointing at
  a different MCP server URL — no code changes in Axon itself.
- **Security boundary**: MCP servers can enforce authentication, rate
  limiting, and tool-level access control. Axon never holds database
  credentials.
- **Testability**: MCP server stubs replace entire ERPs in CI. No need
  for Oracle/SAP test instances.
- **Version resilience**: ERP upgrades that change database schemas are
  absorbed by the MCP server, not by Axon's planning logic.
- **Auditability**: every tool call is a logged HTTP request with a
  correlation ID.

### Negative

- **Latency overhead**: every data fetch crosses an HTTP boundary. Mitigated
  by Redis caching (configurable TTL per tool) and batched tool calls.
- **Dependency on MCP ecosystem**: MCP is a relatively young protocol
  (Anthropic, 2024). If adoption stalls, Axon's architecture becomes
  an orphan. Mitigated by keeping the `MCPToolOutput` wrapper generic —
  the connector protocol could be adapted to OpenAPI/gRPC if needed.
- **Tool discovery complexity**: the system must handle tools appearing
  and disappearing as MCP servers are updated. Mitigated by the
  `SemanticTransformer.can_handle()` routing pattern and graceful
  degradation when a tool is unavailable.

## Alternatives Considered

### 1. Direct database connections with an ORM

Rejected. Would require maintaining SQL dialects for 3+ ERP schemas,
violating the "ERP-agnostic" goal. Schema changes in any ERP would
break Axon's queries.

### 2. REST API per ERP with custom adapters

Partially considered. Better than direct DB, but each ERP would require
a custom adapter with its own authentication, pagination, and error
handling. MCP standardizes these concerns across all ERPs.

### 3. Hybrid: MCP for reads, direct DB for writes

Rejected for Phase 1–4. Write-back (Phase 5) will also use MCP's
bi-directional tool calls. Adding direct DB for writes would reintroduce
the coupling we're avoiding and create two error models to maintain.

### 4. Apache Kafka event streaming

Complementary, not alternative. Kafka could be used for real-time event
propagation between ERPs and Axon, but MCP remains the request/response
protocol for tool calls. A future ADR may add Kafka as an additional
perception channel.

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [pydantic-ai MCP support](https://ai.pydantic.dev/mcp/)
- Axon README.md — Modular Project Structure
- Axon docs/architecture.md — Error Model (circuit breaker, degradation)
