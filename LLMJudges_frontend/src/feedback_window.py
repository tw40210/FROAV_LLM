import json
from typing import Any, Dict, Optional

import streamlit as st

from LLMJudges_frontend.src.utils import (
    get_db_connection,
    get_existing_feedback,
    get_logged_in_user,
)


def save_report_feedback(
    user_name: str,
    report_execution_id: str,
    feedback_payload: Dict[str, Any],
    query: str | None,
    material_category: str | None,
    existing_feedback_id: Optional[int] = None,
) -> None:
    """Persist feedback into report_human_feedback table.

    If existing_feedback_id is provided, updates the existing record.
    Otherwise, inserts a new record.
    """
    serialized_payload = json.dumps(feedback_payload)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if existing_feedback_id:
                # Update existing feedback
                update_sql = """
                    UPDATE report_human_feedback
                    SET human_feedback_data = %s::jsonb,
                        query = %s,
                        material_category = %s,
                        logged_at = NOW()
                    WHERE id = %s AND user_name = %s
                """
                cur.execute(
                    update_sql,
                    (serialized_payload, query, material_category, existing_feedback_id, user_name),
                )
            else:
                # Insert new feedback
                insert_sql = """
                    INSERT INTO report_human_feedback (
                        user_name,
                        report_n8n_execution_id,
                        human_feedback_data,
                        query,
                        material_category
                    )
                    VALUES (%s, %s, %s::jsonb, %s, %s)
                """
                cur.execute(
                    insert_sql,
                    (user_name, report_execution_id, serialized_payload, query, material_category),
                )


def _feedback_container(label: str, key: str):
    """Return a popover if supported, otherwise an expander."""
    return st.popover(label, use_container_width=True)


def render_feedback_form(row: Dict[str, Any]) -> None:
    """Render feedback trigger and submission form for a report row.

    Requires user to be logged in before showing the feedback form.
    """
    container_label = "💬 Share Feedback"
    container_key = f"feedback_container_{row.get('id')}"
    report_execution_id = str(row.get("n8n_execution_id") or row.get("id") or "")

    if not report_execution_id:
        st.info("Feedback unavailable: missing execution identifier.")
        return

    _, right_col = st.columns([1, 1])
    with right_col:
        container = _feedback_container(container_label, container_key)

    # Check if user is logged in
    logged_in_user = get_logged_in_user()

    if not logged_in_user:
        # Show error message if user is not logged in
        with container:
            st.error("🔐 Please login from the sidebar to provide feedback.")
        return

    # User is logged in, show feedback form
    with container:
        user_name = logged_in_user.get("user_name", "User")

        # Check for existing feedback
        existing_feedback = get_existing_feedback(user_name, report_execution_id)

        if existing_feedback:
            st.info(
                "📝 You have already submitted feedback for this report. You can edit it below."
            )
            existing_data = existing_feedback.get("human_feedback_data", {})

            if isinstance(existing_data, dict):
                default_relevance_score = existing_data.get("relevance_score", 50)
                default_completeness_score = existing_data.get("completeness_score", 50)
                default_reliability_score = existing_data.get("reliability_score", 50)
                default_understandability_score = existing_data.get("understandability_score", 50)
                default_comments = existing_data.get("comments", "")
            else:
                default_relevance_score = 50
                default_completeness_score = 50
                default_reliability_score = 50
                default_understandability_score = 50
                default_comments = ""

            if existing_feedback.get("logged_at"):
                st.caption(f"Last updated: {existing_feedback['logged_at']}")
        else:
            default_relevance_score = 50
            default_completeness_score = 50
            default_reliability_score = 50
            default_understandability_score = 50
            default_comments = ""
            st.write("Let us know how useful this report was.")

        form_key = f"feedback_form_{row.get('id')}"
        button_text = "Update Feedback" if existing_feedback else "Submit Feedback"

        with st.form(form_key, clear_on_submit=False):
            relevance_score = st.slider(
                "Relevance Score (1 = low, 100 = high)",
                min_value=1,
                max_value=100,
                value=default_relevance_score,
            )

            completeness_score = st.slider(
                "Completence Score (1 = low, 100 = high)",
                min_value=1,
                max_value=100,
                value=default_completeness_score,
            )

            reliability_score = st.slider(
                "Reliability Score (1 = low, 100 = high)",
                min_value=1,
                max_value=100,
                value=default_reliability_score,
            )

            understandability_score = st.slider(
                "Understandability Score (1 = low, 100 = high)",
                min_value=1,
                max_value=100,
                value=default_understandability_score,
            )
            comments = st.text_area(
                "Feedback",
                value=default_comments,
                placeholder="Share what worked well or what could improve.",
            )
            submitted = st.form_submit_button(button_text, use_container_width=True)

        if submitted:
            if not comments.strip():
                st.error("Please add a brief comment.")
                return

            feedback_payload = {
                "relevance_score": relevance_score,
                "completeness_score": completeness_score,
                "reliability_score": reliability_score,
                "understandability_score": understandability_score,
                "comments": comments.strip(),
                "report_row_id": row.get("id"),
            }

            try:
                existing_feedback_id = existing_feedback.get("id") if existing_feedback else None
                save_report_feedback(
                    logged_in_user["user_name"],
                    report_execution_id,
                    feedback_payload,
                    row.get("query"),
                    row.get("material_category"),
                    existing_feedback_id=existing_feedback_id,
                )
                success_message = (
                    "Feedback updated — thank you!"
                    if existing_feedback
                    else "Feedback saved — thank you!"
                )
                st.success(success_message)
                st.rerun()  # Rerun to refresh the form with updated data
            except Exception as exc:
                st.error("Unable to save feedback.")
                st.exception(exc)
