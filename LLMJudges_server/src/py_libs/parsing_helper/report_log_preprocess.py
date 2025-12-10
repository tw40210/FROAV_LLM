"""
Utilities to preprocess n8n execution log data for the Financial Report Judges.

This module flattens relevant fields (output, mid_steps, query) from the
execution logs produced by n8n (see `n8n_log_parser.py`) into a single
plain-text string suitable for LLM judges, and builds a payload for
the webhook `http://localhost:5678/webhook-test/judge-financial-report`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Union

from LLMJudges_server.src.config.config_loader import set_default_file_env_vars

try:
    import psycopg
except Exception:  # pragma: no cover - optional import guard for environments without psycopg
    psycopg = None  # type: ignore

set_default_file_env_vars()


def _stringify(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _recursively_parse_json(obj: Any) -> Any:
    """Recursively parse JSON strings in nested data structures.

    This function traverses through dictionaries, lists, and other data structures
    and attempts to parse any string values as JSON. If parsing fails, the original
    string is preserved.
    """
    if isinstance(obj, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(obj)
            # Recursively parse the parsed result in case it contains more JSON strings
            return _recursively_parse_json(parsed)
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, return the original string
            return obj
    elif isinstance(obj, dict):
        # Recursively parse all values in the dictionary
        return {key: _recursively_parse_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        # Recursively parse all items in the list
        return [_recursively_parse_json(item) for item in obj]
    else:
        # For other types (int, float, bool, None), return as-is
        return obj


def preprocess(execution_row_or_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and flatten output, mid_steps and query into plain text.

    Accepts either a raw DB row with `execution_data` or a summarized dict
    returned by `summarize_execution_row(..)` (from `n8n_log_parser.py`).

    Returns a dict with:
      - output_text: str | None
      - queries: list[str]
      - mid_steps_text: str
      - flat_text: str (single string combining the above with light labels)
    """
    row = execution_row_or_summary or {}

    # Prefer summarized fields if present
    output_text: Optional[str] = row.get("output_full")
    mid_steps_obs = row.get("mid_steps_observations_json")

    execution_data: Optional[Dict[str, Any]] = row.get("execution_data")
    if output_text is None and isinstance(execution_data, dict):
        if isinstance(execution_data.get("output"), str):
            output_text = execution_data.get("output")

    # Build mid_steps textual representation
    mid_steps_lines: List[str] = []
    mid_steps_json: List[Any] = []
    # Prefer raw mid_steps from execution_data for full fidelity
    mid_steps = None
    if isinstance(execution_data, dict):
        mid_steps = execution_data.get("mid_steps")
    if isinstance(mid_steps, list):
        for idx, step in enumerate(mid_steps):
            if not isinstance(step, dict):
                mid_steps_lines.append(f"Step {idx+1}: {_stringify(step)}")
                continue
            action = step.get("action")
            observation = step.get("observation")
            parts: List[str] = []
            parts_json = {}
            if isinstance(action, dict):
                tool = action.get("tool")
                if isinstance(tool, str) and tool:
                    parts.append(f"tool={tool}")
                    parts_json[f"tool"] = tool
            if observation is not None:
                parts.append(f"observation={_stringify(observation)}")
                # Recursively parse observation JSON and save in another field
                observation_parsed = _recursively_parse_json(observation)
                parts.append(f"observation_parsed={_stringify(observation_parsed)}")
                parts_json["observation_parsed"] = observation_parsed
            if parts:
                mid_steps_lines.append(f"Step {idx+1}: " + " | ".join(parts))
            if parts_json:
                mid_steps_json.append(parts_json)
    elif isinstance(mid_steps_obs, list):
        # Fallback to summarized observations if raw mid_steps missing
        for idx, obs in enumerate(mid_steps_obs):
            mid_steps_lines.append(f"Step {idx+1}: observation={_stringify(obs)}")

    mid_steps_text = "\n".join(mid_steps_lines).strip()

    # Find possible queries
    query = row["query"]

    # Compose flat text for judges
    sections: List[str] = []
    if query:
        sections.append("[QUERY]\n" + query)
    if output_text:
        sections.append("[OUTPUT]\n" + output_text)
    if mid_steps_text:
        sections.append("[MID_STEPS]\n" + mid_steps_text)

    flat_text = ("\n\n".join(sections)).strip()

    return {
        "output_text": output_text,
        "query": query,
        "mid_steps_text": mid_steps_text,
        "mid_steps_json": mid_steps_json,
        "flat_text": flat_text,
    }


def build_webhook_payload(
    execution_row_or_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Build payload expected by the N8N judge webhook.

    The judge endpoint expects fields similar to those used by the CLI client:
      { "report_text": <flattened>, "company_ticker": <str> }
    """
    processed = preprocess(execution_row_or_summary)
    payload = {
        "report_text": processed.get("flat_text", ""),
        "company_ticker": execution_row_or_summary.get("company_ticker", "Unknown Company"),
        "query": execution_row_or_summary.get("query", ""),
        "n8n_execution_id": execution_row_or_summary.get("n8n_execution_id", ""),
    }
    return payload


def _get_db_connection() -> "psycopg.Connection":
    """Create a PostgreSQL connection using env vars.

    Env vars: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
    """
    if psycopg is None:
        raise RuntimeError("psycopg is required but not installed in the current environment")

    # Ensure .env defaults are loaded
    try:
        set_default_file_env_vars()
    except Exception:
        pass

    host = os.getenv("PGHOST_CLUSTER", "postgres")
    port = int(os.getenv("PGPORT", "5432"))
    dbname = os.getenv("PGDATABASE", "n8n")
    user = os.getenv("PGUSER", "n8n")
    password = os.getenv("PGPASSWORD")

    if not password:
        raise RuntimeError("PGPASSWORD environment variable not set")

    dsn = f"host={host} port={port} dbname={dbname} user={user} password={password}"
    return psycopg.connect(dsn, autocommit=True)


def _fetch_execution_row(execution_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single execution row by `n8n_execution_id` or numeric `id`.

    Returns the row as a dict with `execution_data` parsed to JSON if it was a string.
    """

    query: str
    query = f"SELECT * FROM n8n_report_model_logs WHERE n8n_execution_id = '{execution_id}' LIMIT 1"

    with _get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rec = cur.fetchone()
            if not rec:
                return None
            colnames = [desc[0] for desc in cur.description]
            row = {col: val for col, val in zip(colnames, rec)}
            # Parse JSON execution_data if it's a string
            exec_data = row.get("execution_data")
            if isinstance(exec_data, str):
                try:
                    row["execution_data"] = json.loads(exec_data)
                except Exception:
                    pass
            return row


def get_preprocessed_by_execution_id(execution_id: Union[str, int]) -> Dict[str, Any]:
    """Return preprocessed texts for a given execution id.

    Response body contains at least:
      - report_text: flattened plain text
      - query, company_ticker, n8n_execution_id: passthrough metadata when available
    """
    row = _fetch_execution_row(execution_id)
    if row is None:
        raise ValueError(f"Execution not found for id: {execution_id}")

    processed = preprocess(row)
    return {
        "report_text": processed.get("flat_text", ""),
        "query": row.get("query", ""),
        "output_text": processed.get("output_text", ""),
        "mid_steps_text": processed.get("mid_steps_text", ""),
        "company_ticker": row.get("company_ticker", "Unknown Company"),
        "n8n_execution_id": row.get("n8n_execution_id", ""),
    }
