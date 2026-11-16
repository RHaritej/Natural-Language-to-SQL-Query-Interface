"""ReAct SQL Agent that uses database tools interactively to inspect schema, validate, and verify queries."""

import re
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..core.db_engine import DatabaseEngine, ExecutionResult
from ..core.schema_inspector import SchemaInspector
from ..core.validator import SQLValidator
from ..llm.base import BaseLLMClient, LLMMessage
from .tools import DatabaseTools


class AgentStep(BaseModel):
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    duration_ms: float = 0.0


class AgentRunResult(BaseModel):
    success: bool
    question: str
    final_sql: str
    final_answer: str
    steps: List[AgentStep] = Field(default_factory=list)
    tool_calls_count: int = 0
    final_execution: Optional[ExecutionResult] = None
    total_time_ms: float = 0.0


class ReActSQLAgent:
    """Autonomous SQL Agent using ReAct (Reasoning + Action) with tool usage."""

    def __init__(
        self,
        db_engine: DatabaseEngine,
        inspector: SchemaInspector,
        llm: BaseLLMClient,
        max_steps: int = 6,
        validator: Optional[SQLValidator] = None,
    ):
        self.db_engine = db_engine
        self.inspector = inspector
        self.llm = llm
        self.max_steps = max_steps
        self.validator = validator or SQLValidator(inspector=inspector)
        self.tools = DatabaseTools(db_engine=db_engine, inspector=inspector, validator=self.validator)

    def _build_system_prompt(self) -> str:
        tool_specs = "\n".join(
            f"- {t.name}: {t.description} Parameters: {json.dumps(t.parameters)}"
            for t in self.tools.get_definitions()
        )

        return f"""You are an autonomous SQL database agent.
You solve natural language database questions by inspecting the schema, formulating candidate queries, testing them with database tools, and refining them based on observations.

You have access to the following tools:
{tool_specs}

Use the following format strictly:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{", ".join(t.name for t in self.tools.get_definitions())}]
Action Input: the input to the action as a valid JSON object
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat up to {self.max_steps} times)
Thought: I now have the verified, correct SQL query
Final Answer: ```sql
<the verified SQLite query>
```
"""

    def run(self, question: str) -> AgentRunResult:
        start_time = time.perf_counter()
        system_prompt = self._build_system_prompt()
        
        conversation_history: List[str] = [f"Question: {question}"]
        steps: List[AgentStep] = []
        final_sql = ""
        final_answer = ""

        for step_idx in range(1, self.max_steps + 1):
            step_start = time.perf_counter()
            prompt = "\n\n".join(conversation_history)
            
            # Request next agent action
            try:
                response = self.llm.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.0,
                    stop_sequences=["Observation:"],
                )
                raw_text = response.content.strip()
            except Exception as exc:
                steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=f"LLM error: {exc}",
                        duration_ms=round((time.perf_counter() - step_start) * 1000.0, 2),
                    )
                )
                break

            # Check if agent issued Final Answer
            if "Final Answer:" in raw_text:
                final_answer_part = raw_text.split("Final Answer:")[-1].strip()
                final_answer = final_answer_part
                final_sql = self.validator.clean_markdown_fences(final_answer_part)
                
                # Extract thought if present
                thought = raw_text.split("Final Answer:")[0].replace("Thought:", "").strip()
                steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=thought or "Reached conclusion.",
                        duration_ms=round((time.perf_counter() - step_start) * 1000.0, 2),
                    )
                )
                break

            # Parse Thought, Action, Action Input
            thought, action, action_input = self._parse_agent_step(raw_text)

            if not action:
                # Agent didn't format an action, extract any SQL or conclude
                sql_match = re.search(r"```sql(.*?)```", raw_text, re.DOTALL)
                if sql_match:
                    final_sql = sql_match.group(1).strip()
                    final_answer = raw_text
                else:
                    final_sql = self.validator.clean_markdown_fences(raw_text)
                    final_answer = raw_text
                steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=thought or raw_text,
                        duration_ms=round((time.perf_counter() - step_start) * 1000.0, 2),
                    )
                )
                break

            # Execute Tool
            observation = self.tools.execute_tool(action, action_input)
            
            step = AgentStep(
                step_number=step_idx,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
                duration_ms=round((time.perf_counter() - step_start) * 1000.0, 2),
            )
            steps.append(step)

            # Update conversation history
            step_text = f"Thought: {thought}\nAction: {action}\nAction Input: {json.dumps(action_input)}\nObservation: {observation}"
            conversation_history.append(step_text)

            # If action was execute_query and it succeeded, keep candidate sql
            if action == "execute_query" and "status\": \"success\"" in observation:
                candidate_sql = action_input.get("sql", "")
                if candidate_sql:
                    final_sql = candidate_sql

        # If loop ended without final SQL, extract best candidate from steps
        if not final_sql:
            for s in reversed(steps):
                if s.action == "execute_query" and s.action_input:
                    final_sql = s.action_input.get("sql", "")
                    break

        cleaned_final_sql = self.validator.clean_markdown_fences(final_sql) if final_sql else ""
        final_exec = None
        if cleaned_final_sql:
            val = self.validator.validate(cleaned_final_sql)
            if val.is_valid:
                final_exec = self.db_engine.execute_query(val.normalized_sql or cleaned_final_sql)
        total_time = (time.perf_counter() - start_time) * 1000.0

        return AgentRunResult(
            success=bool(final_exec and final_exec.success),
            question=question,
            final_sql=cleaned_final_sql,
            final_answer=final_answer or f"Completed with SQL: {cleaned_final_sql}",
            steps=steps,
            tool_calls_count=sum(1 for s in steps if s.action is not None),
            final_execution=final_exec,
            total_time_ms=round(total_time, 2),
        )

    def _parse_agent_step(self, text: str) -> tuple[str, Optional[str], Dict[str, Any]]:
        """Robustly parse Thought, Action, and Action Input."""
        thought = ""
        action = None
        action_input = {}

        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", text)
        if action_match:
            action = action_match.group(1).strip()

        input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1).strip())
            except Exception:
                # Try raw string
                raw_val = input_match.group(1).strip()
                action_input = {"raw": raw_val}
        else:
            # Fallback check if Action Input followed on same or next line
            alt_match = re.search(r"Action Input:\s*(.+?)(?=\nObservation:|$)", text, re.DOTALL)
            if alt_match:
                content = alt_match.group(1).strip()
                try:
                    action_input = json.loads(content)
                except Exception:
                    action_input = {"sql": content}

        return thought, action, action_input
