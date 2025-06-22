# Source Code

This directory contains the main application code for the 1-click migration tool.

## Structure
- `mcp_client.py` - Enhanced MCP client for orchestrating multiple servers
- `migration_orchestrator.py` - Main orchestration logic for the migration pipeline
- `config/` - Configuration files for different cloud providers
- `utils/` - Utility functions and helpers
- `tests/` - Unit and integration tests

## Components
1. **MCP Client Manager** - Handles multiple MCP server connections
2. **Migration Orchestrator** - Coordinates the end-to-end migration workflow
3. **Data Transformer** - Handles data mapping between cloud providers
4. **Validation Engine** - Validates configurations before and after migration
