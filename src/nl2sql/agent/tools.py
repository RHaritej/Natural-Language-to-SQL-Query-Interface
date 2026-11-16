"""Database tools available to the autonomous SQL Agent."""

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..core.db_engine import DatabaseEngine, ExecutionResult
from ..core.schema_inspector import SchemaInspector
from ..core.validator import SQLValidator


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class DatabaseTools:
    """Suite of inspection and execution tools exposed to the ReAct agent."""

    def __init__(
        self,
        db_engine: DatabaseEngine,
        inspector: SchemaInspector,
        validator: Optional[SQLValidator] = None,
    ):
        self.db_engine = db_engine
        self.inspector = inspector
        self.validator = validator or SQLValidator(inspector=inspector)

    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="list_tables",
                description="List all available table names in the database.",
                parameters={"type": "object", "properties": {}},
            ),
            ToolDefinition(
                name="describe_table",
                description="Get detailed schema (columns, types, foreign keys) for a specific table.",
                parameters={
                    "type": "object",
                    "properties": {"table_name": {"type": "string", "description": "The name of the table."}},
                    "required": ["table_name"],
                },
            ),
            ToolDefinition(
                name="sample_table_data",
                description="View sample rows from a table to inspect value formats, casing, and codes.",
                parameters={
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Table to sample."},
                        "limit": {"type": "integer", "description": "Number of rows (1-5). Default 3."},
                    },
                    "required": ["table_name"],
                },
            ),
            ToolDefinition(
                name="execute_query",
                description="Execute a candidate SQL query against the database. Returns rows or error message.",
                parameters={
                    "type": "object",
                    "properties": {"sql": {"type": "string", "description": "The SQLite query to execute."}},
                    "required": ["sql"],
                },
            ),
            ToolDefinition(
                name="validate_query",
                description="Check SQL syntax and schema validity without running on the database.",
                parameters={
                    "type": "object",
                    "properties": {"sql": {"type": "string", "description": "The SQL query to validate."}},
                    "required": ["sql"],
                },
            ),
        ]

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Dispatch tool execution and return string observation for the agent."""
        try:
            if not isinstance(args, dict):
                args = {}

            if tool_name == "list_tables":
                tables = self.inspector.get_table_names()
                return json.dumps({"tables": tables})

            elif tool_name == "describe_table":
                t_name = args.get("table_name", "")
                if not t_name:
                    return json.dumps({"error": "Missing required argument 'table_name'."})
                table = self.inspector.tables.get(t_name)
                if not table:
                    return json.dumps({"error": f"Table '{t_name}' not found."})
                return json.dumps({
                    "table": t_name,
                    "columns": [c.model_dump() for c in table.columns],
                    "foreign_keys": [fk.model_dump() for fk in table.foreign_keys],
                })

            elif tool_name == "sample_table_data":
                t_name = args.get("table_name", "")
                if not t_name:
                    return json.dumps({"error": "Missing required argument 'table_name'."})
                table = self.inspector.tables.get(t_name)
                if not table:
                    return json.dumps({"error": f"Table '{t_name}' not found."})
                try:
                    limit = min(max(int(args.get("limit", 3)), 1), 5)
                except (ValueError, TypeError):
                    limit = 3
                return json.dumps({"sample_rows": table.sample_rows[:limit]})

            elif tool_name == "execute_query":
                sql = args.get("sql", "")
                cleaned_sql = self.validator.clean_markdown_fences(sql)
                # Never bypass validator before execution
                val = self.validator.validate(cleaned_sql)
                if not val.is_valid:
                    return json.dumps({
                        "status": "error",
                        "error_type": "VALIDATION_ERROR",
                        "error_message": "; ".join(val.all_errors),
                    })
                res = self.db_engine.execute_query(val.normalized_sql or cleaned_sql)
                if res.success:
                    return json.dumps({
                        "status": "success",
                        "row_count": res.row_count,
                        "columns": res.columns,
                        "rows": res.rows[:10],
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "error_type": res.error_type,
                        "error_message": res.error_message,
                    })

            elif tool_name == "validate_query":
                sql = args.get("sql", "")
                sql = self.validator.clean_markdown_fences(sql)  # strip markdown fences before validation
                val = self.validator.validate(sql)
                return json.dumps({
                    "is_valid": val.is_valid,
                    "syntax_error": val.syntax_error,
                    "schema_errors": val.schema_errors,
                })

            else:
                return json.dumps({"error": f"Unknown tool: '{tool_name}'"})
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
