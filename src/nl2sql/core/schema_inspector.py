"""Schema Inspector for relational databases."""

import sqlite3
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, deque
from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Metadata for a table column."""
    name: str
    data_type: str
    is_primary_key: bool = False
    is_nullable: bool = True
    sample_values: List[Any] = Field(default_factory=list)


class ForeignKeySchema(BaseModel):
    """Foreign key relationship between two tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class TableSchema(BaseModel):
    """Metadata for a database table."""
    name: str
    columns: List[ColumnSchema] = Field(default_factory=list)
    foreign_keys: List[ForeignKeySchema] = Field(default_factory=list)
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]


class SchemaInspector:
    """Introspects and formats relational schemas for LLM prompts and validation."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.tables: Dict[str, TableSchema] = {}
        self._fk_graph: Dict[str, Set[str]] = defaultdict(set)
        self._fk_details: Dict[Tuple[str, str], List[ForeignKeySchema]] = defaultdict(list)
        self.refresh()

    def refresh(self):
        """Introspect the database and rebuild internal schema state."""
        self.tables.clear()
        self._fk_graph.clear()
        self._fk_details.clear()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Fetch all user tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            table_names = [row[0] for row in cursor.fetchall()]

            for t_name in table_names:
                # Column metadata
                cursor.execute(f"PRAGMA table_info('{t_name}');")
                # cid, name, type, notnull, dflt_value, pk
                col_rows = cursor.fetchall()

                columns: List[ColumnSchema] = []
                for cid, name, col_type, notnull, dflt, pk in col_rows:
                    columns.append(
                        ColumnSchema(
                            name=name,
                            data_type=col_type or "TEXT",
                            is_primary_key=bool(pk),
                            is_nullable=not bool(notnull),
                        )
                    )

                # Foreign keys
                cursor.execute(f"PRAGMA foreign_key_list('{t_name}');")
                # id, seq, table, from, to, on_update, on_delete, match (8 values)
                fk_rows = cursor.fetchall()
                foreign_keys: List[ForeignKeySchema] = []
                for row in fk_rows:
                    to_tbl = row[2]
                    from_col = row[3]
                    to_col = row[4]
                    fk = ForeignKeySchema(
                        from_table=t_name,
                        from_column=from_col,
                        to_table=to_tbl,
                        to_column=to_col,
                    )
                    foreign_keys.append(fk)
                    self._fk_graph[t_name].add(to_tbl)
                    self._fk_graph[to_tbl].add(t_name)
                    self._fk_details[(t_name, to_tbl)].append(fk)
                    # Reverse perspective for path finding
                    rev_fk = ForeignKeySchema(
                        from_table=to_tbl,
                        from_column=to_col,
                        to_table=t_name,
                        to_column=from_col,
                    )
                    self._fk_details[(to_tbl, t_name)].append(rev_fk)

                # Sample rows (up to 3)
                sample_rows = []
                try:
                    cursor.execute(f"SELECT * FROM '{t_name}' LIMIT 3;")
                    c_names = [c.name for c in columns]
                    for s_row in cursor.fetchall():
                        sample_rows.append(dict(zip(c_names, s_row)))

                    # Populate sample_values in columns
                    for col in columns:
                        vals = [r[col.name] for r in sample_rows if r.get(col.name) is not None]
                        col.sample_values = list(dict.fromkeys(vals))[:3]
                except Exception:
                    pass

                self.tables[t_name] = TableSchema(
                    name=t_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    sample_rows=sample_rows,
                )
        finally:
            conn.close()

    def get_table_names(self) -> List[str]:
        return list(self.tables.keys())

    def get_column_names(self, table_name: str) -> List[str]:
        table = self.tables.get(table_name)
        return table.column_names if table else []

    def find_shortest_join_path(self, start_table: str, end_table: str) -> Optional[List[str]]:
        """Breadth-first search for shortest join path between two tables."""
        if start_table == end_table:
            return [start_table]
        if start_table not in self.tables or end_table not in self.tables:
            return None

        queue = deque([[start_table]])
        visited = {start_table}

        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == end_table:
                return path

            for neighbor in self._fk_graph.get(curr, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def get_join_conditions(self, path: List[str]) -> List[str]:
        """Given a path of tables [T1, T2, T3], return the ON conditions for joining them."""
        conditions = []
        for i in range(len(path) - 1):
            t1, t2 = path[i], path[i + 1]
            fks = self._fk_details.get((t1, t2), [])
            if fks:
                fk = fks[0]
                conditions.append(f"{fk.from_table}.{fk.from_column} = {fk.to_table}.{fk.to_column}")
            else:
                # Fallback: check matching column name
                t1_cols = set(self.get_column_names(t1))
                t2_cols = set(self.get_column_names(t2))
                common = t1_cols.intersection(t2_cols)
                if common:
                    col = next(iter(common))
                    conditions.append(f"{t1}.{col} = {t2}.{col}")
                else:
                    conditions.append(f"/* Join between {t1} and {t2} */")
        return conditions

    def to_ddl_string(self) -> str:
        """Returns standard CREATE TABLE DDL representation of the database schema."""
        statements = []
        for tbl in self.tables.values():
            col_defs = []
            for col in tbl.columns:
                pk_str = " PRIMARY KEY" if col.is_primary_key else ""
                col_defs.append(f"  {col.name} {col.data_type}{pk_str}")
            for fk in tbl.foreign_keys:
                col_defs.append(
                    f"  FOREIGN KEY ({fk.from_column}) REFERENCES {fk.to_table}({fk.to_column})"
                )
            stmt = f"CREATE TABLE {tbl.name} (\n" + ",\n".join(col_defs) + "\n);"
            statements.append(stmt)
        return "\n\n".join(statements)

    def to_compact_markdown(self, include_samples: bool = True) -> str:
        """Formats the schema into a concise, token-efficient markdown format for LLMs."""
        lines = []
        for tbl in self.tables.values():
            cols = []
            for c in tbl.columns:
                pk = " (PK)" if c.is_primary_key else ""
                sample = f" [e.g. {c.sample_values[0]!r}]" if include_samples and c.sample_values else ""
                cols.append(f"{c.name}: {c.data_type}{pk}{sample}")
            lines.append(f"Table `{tbl.name}`:\n  - Columns: " + ", ".join(cols))
            if tbl.foreign_keys:
                fk_strs = [
                    f"`{fk.from_column}` -> `{fk.to_table}.{fk.to_column}`"
                    for fk in tbl.foreign_keys
                ]
                lines.append(f"  - Foreign Keys: " + ", ".join(fk_strs))
        return "\n".join(lines)
