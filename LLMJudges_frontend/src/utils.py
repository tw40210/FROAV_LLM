import json
import os
from typing import Any, Dict, Optional

import psycopg
import streamlit as st

from LLMJudges_frontend.src.config.config_loader import set_default_file_env_vars


def get_db_connection() -> psycopg.Connection:
    """Get database connection usall collected observationing environment variables."""
    try:
        set_default_file_env_vars()
    except Exception:
        pass

    host = os.getenv("PGHOST", "localhost")
    port = int(os.getenv("PGPORT", "5432"))
    dbname = os.getenv("PGDATABASE", "n8n")
    user = os.getenv("PGUSER", "n8n")
    password = os.getenv("PGPASSWORD")

    if not password:
        st.error("PGPASSWORD environment variable not set")
        st.stop()

    dsn = f"host={host} port={port} dbname={dbname} user={user} password={password}"
    print(dsn)
    return psycopg.connect(dsn, autocommit=True)


def logout_user() -> None:
    """Clear user session data."""
    if "feedback_user" in st.session_state:
        del st.session_state["feedback_user"]


def get_logged_in_user() -> Optional[Dict[str, Any]]:
    """Get the currently logged-in user from session state."""
    return st.session_state.get("feedback_user")


def authenticate_user(user_name: str, user_token: str) -> Optional[Dict[str, Any]]:
    """Authenticate user by checking user_name and user_token in database.

    Returns user data if authentication succeeds, None otherwise.
    """
    if not user_name.strip() or not user_token.strip():
        return None

    query_sql = """
        SELECT id, user_name, user_token, user_groups, description
        FROM user_data
        WHERE user_name = %s AND user_token = %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, (user_name.strip(), user_token.strip()))
                result = cur.fetchone()
                if result:
                    colnames = [desc[0] for desc in cur.description]
                    return {col: val for col, val in zip(colnames, result)}
                return None
    except Exception:
        return None


def get_existing_feedback(user_name: str, report_execution_id: str) -> Optional[Dict[str, Any]]:
    """Fetch existing feedback for a user and report execution ID.

    Returns the feedback record if found, None otherwise.
    """
    query_sql = """
        SELECT id, user_name, report_n8n_execution_id, human_feedback_data,
               logged_at, query, company_ticker
        FROM report_human_feedback
        WHERE user_name = %s AND report_n8n_execution_id = %s
        ORDER BY logged_at DESC
        LIMIT 1
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, (user_name, report_execution_id))
                result = cur.fetchone()
                if result:
                    colnames = [desc[0] for desc in cur.description]
                    feedback = {col: val for col, val in zip(colnames, result)}
                    # Parse JSONB if it's a string
                    feedback_data = feedback.get("human_feedback_data")
                    if isinstance(feedback_data, str):
                        try:
                            feedback["human_feedback_data"] = json.loads(feedback_data)
                        except Exception:
                            pass
                    return feedback
                return None
    except Exception:
        return None


def get_user_feedback_execution_ids(user_name: str) -> set[str]:
    """Fetch all report execution IDs for which the user has submitted feedback.

    Returns a set of report_n8n_execution_id strings.
    """
    query_sql = """
        SELECT DISTINCT report_n8n_execution_id
        FROM report_human_feedback
        WHERE user_name = %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, (user_name,))
                results = cur.fetchall()
                return {str(row[0]) for row in results if row[0]}
    except Exception:
        return set()


def render_login_form(container) -> bool:
    """Render login form in the given container. Returns True if login successful."""
    with container:
        st.write("🔐 Please login to provide feedback")
        login_key = "feedback_login_form"

        with st.form(login_key, clear_on_submit=False):
            user_name = st.text_input(
                "User Name",
                placeholder="Enter your user name",
                help="Your registered user name",
            )
            user_token = st.text_input(
                "User Token",
                type="password",
                placeholder="Enter your user token",
                help="Your authentication token",
            )
            login_submitted = st.form_submit_button("Login", use_container_width=True)

        if login_submitted:
            if not user_name.strip():
                st.error("User name is required.")
                return False
            if not user_token.strip():
                st.error("User token is required.")
                return False

            user_data = authenticate_user(user_name.strip(), user_token.strip())
            if user_data:
                st.session_state["feedback_user"] = user_data
                st.success(f"Welcome, {user_data['user_name']}!")
                st.rerun()
                return True
            else:
                st.error("Invalid user name or token. Please try again.")
                return False

        return False
