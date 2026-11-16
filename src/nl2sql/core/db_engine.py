"""Database execution engine for executing queries safely over relational databases."""

import time
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Encapsulates the execution result or error of a SQL query."""
    success: bool
    sql: str
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    error_type: Optional[str] = None  # e.g., 'SYNTAX_ERROR', 'NO_SUCH_COLUMN', 'TIMEOUT', etc.

    @property
    def is_empty(self) -> bool:
        return self.success and self.row_count == 0


class DatabaseEngine:
    """Manages connection and query execution for a SQLite database."""

    def __init__(self, db_path: str, timeout: float = 5.0):
        self.db_path = str(db_path)
        self.timeout = timeout

    def get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def execute_query(self, sql: str, max_rows: int = 200) -> ExecutionResult:
        """Executes a SQL query in read-only mode and returns structured results."""
        start_time = time.perf_counter()
        clean_sql = sql.strip().rstrip(";")
        
        # Guard against multi-statement injections or destructive commands
        first_token = clean_sql.split()[0].upper() if clean_sql.split() else ""
        destructive_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE"]
        if first_token in destructive_keywords:
            return ExecutionResult(
                success=False,
                sql=sql,
                execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
                error_message=f"Destructive or non-query statement '{first_token}' is disallowed in read-only mode.",
                error_type="DISALLOWED_OPERATION",
            )

        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(clean_sql)
            
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)
            # Convert tuples to lists for JSON serialization
            serialized_rows = [[item for item in row] for row in rows]
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return ExecutionResult(
                success=True,
                sql=sql,
                columns=columns,
                rows=serialized_rows,
                row_count=len(serialized_rows),
                execution_time_ms=round(duration_ms, 2),
            )
        except sqlite3.OperationalError as e:
            err_msg = str(e)
            err_type = "OPERATIONAL_ERROR"
            if "no such column" in err_msg.lower():
                err_type = "NO_SUCH_COLUMN"
            elif "no such table" in err_msg.lower():
                err_type = "NO_SUCH_TABLE"
            elif "syntax error" in err_msg.lower() or "near " in err_msg.lower():
                err_type = "SYNTAX_ERROR"
            elif "ambiguous column" in err_msg.lower():
                err_type = "AMBIGUOUS_COLUMN"
            elif "misuse of aggregate" in err_msg.lower():
                err_type = "AGGREGATE_ERROR"

            return ExecutionResult(
                success=False,
                sql=sql,
                execution_time_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                error_message=err_msg,
                error_type=err_type,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                sql=sql,
                execution_time_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                error_message=str(e),
                error_type="EXECUTION_ERROR",
            )
        finally:
            if conn:
                conn.close()
