# Category: MCP Servers — Types

Build and audit Model Context Protocol servers and integrations.

Primary audiences: AI agent builders, integration developers.

## Types

### MS1. Hello-world MCP server
- Smallest possible server exposing one tool; connect from a client and call it.

### MS2. Wrap an existing API
- Wrap a public REST API (weather, GitHub, Stripe) as an MCP server with typed tools.

### MS3. Wrap a local capability
- Expose a local CLI or file-system operation via an MCP server.

### MS4. Auth-aware MCP server
- Add OAuth / token-based authentication to a wrapped service.

### MS5. Multi-tool composition
- Compose several MCP servers in a single agent run and demonstrate cross-tool coordination.

### MS6. MCP security audit
- Inspect an MCP server's surface area for unsafe operations, missing scope checks, prompt-injection risks.
