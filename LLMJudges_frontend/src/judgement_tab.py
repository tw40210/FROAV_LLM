"""
Streamlit tab to display rows from n8n_llm_judgement_logs.
"""

import json
import os
from typing import Any, Dict, List

import psycopg
import streamlit as st

from LLMJudges_frontend.src.config.config_loader import set_default_file_env_vars


def get_db_connection() -> psycopg.Connection:
    """Get database connection using environment variables."""
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
    return psycopg.connect(dsn, autocommit=True)


@st.cache_data(ttl=5)
def fetch_judgements(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch judgement logs from database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM n8n_llm_judgement_logs " "ORDER BY logged_at DESC LIMIT %s"
            cur.execute(query, (limit,))
            colnames = [desc[0] for desc in cur.description]
            rows: List[Dict[str, Any]] = []
            for rec in cur.fetchall():
                row = {col: val for col, val in zip(colnames, rec)}
                # Parse JSON judgement_data if it's a string
                jdata = row.get("judgement_data")
                if isinstance(jdata, str):
                    try:
                        row["judgement_data"] = json.loads(jdata)
                    except Exception:
                        pass
                rows.append(row)
            return rows


def _display_judgement_data(jdata: Dict[str, Any], index: int) -> None:
    """Display judgement data in a readable, structured format."""
    if not isinstance(jdata, dict):
        st.json(jdata)
        return

    # Query
    if "query" in jdata:
        st.markdown("### 📋 Query")
        st.info(jdata["query"])

    # Summary Section
    if "summary" in jdata and isinstance(jdata["summary"], dict):
        summary = jdata["summary"]
        st.markdown("### 📊 Summary")

        col1, col2 = st.columns(2)

        with col1:
            if "recommendation" in summary:
                st.write("**Recommendation:**")
                st.write(summary["recommendation"])
        with col2:
            if "models_used" in summary and isinstance(summary["models_used"], list):
                st.write("**Models Used:**")
                for model in summary["models_used"]:
                    st.write(f"- {model}")

    # Overall Assessment
    if "overall_assessment" in jdata and isinstance(jdata["overall_assessment"], dict):
        assessment = jdata["overall_assessment"]
        st.markdown("### 🎯 Overall Assessment")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if "quality_rating" in assessment:
                rating = assessment["quality_rating"]
                color = "🟢" if rating == "GOOD" else "🟡" if rating == "FAIR" else "🔴"
                st.metric("Quality Rating", f"{color} {rating}")
        with col2:
            if "average_score" in assessment:
                st.metric("Average Score", f"{assessment['average_score']:.2f}")
        with col3:
            if "median_score" in assessment:
                st.metric("Median Score", assessment["median_score"])
        with col4:
            if "is_good" in assessment:
                status_icon = "✅" if assessment["is_good"] else "❌"
                st.metric(
                    "Assessment",
                    f"{status_icon} {'Good' if assessment['is_good'] else 'Needs Improvement'}",
                )

        if "score_range" in assessment and isinstance(assessment["score_range"], dict):
            st.write(
                f"**Score Range:** {assessment['score_range'].get('min', 'N/A')} - {assessment['score_range'].get('max', 'N/A')}"
            )

    # Dimension Scores
    if "dimension_scores" in jdata and isinstance(jdata["dimension_scores"], dict):
        st.markdown("### 📈 Dimension Scores(Median of judgements)")
        scores = jdata["dimension_scores"]
        cols = st.columns(len(scores))
        for idx, (dimension, score) in enumerate(scores.items()):
            with cols[idx]:
                # Color coding based on score
                if score >= 85:
                    color = "🟢"
                elif score >= 70:
                    color = "🟡"
                else:
                    color = "🔴"
                st.metric(dimension.capitalize(), f"{color} {score}")

    # Strongest and Weakest Dimensions
    if "insights" in jdata and isinstance(jdata["insights"], dict):
        insights = jdata["insights"]

        has_strongest = "strongest_dimension" in insights and isinstance(
            insights["strongest_dimension"], dict
        )
        has_weakest = "weakest_dimension" in insights and isinstance(
            insights["weakest_dimension"], dict
        )

        if has_strongest or has_weakest:
            col1, col2 = st.columns(2)
            if has_strongest:
                strongest = insights["strongest_dimension"]
                with col1:
                    st.markdown("#### 🏆 Strongest Dimension")
                    st.success(
                        f"**{strongest.get('name', 'N/A').capitalize()}** - Score: {strongest.get('score', 'N/A')}"
                    )

            if has_weakest:
                weakest = insights["weakest_dimension"]
                with col2:
                    st.markdown("#### ⚠️ Weakest Dimension")
                    st.warning(
                        f"**{weakest.get('name', 'N/A').capitalize()}** - Score: {weakest.get('score', 'N/A')}"
                    )

    # Key Strengths and Weaknesses
    if "insights" in jdata and isinstance(jdata["insights"], dict):
        insights = jdata["insights"]

    # Detailed Judgments
    if "detailed_judgments" in jdata and isinstance(jdata["detailed_judgments"], list):
        st.markdown("### 🔍 Detailed Judgments")
        for idx, judgment in enumerate(jdata["detailed_judgments"]):
            if not isinstance(judgment, dict):
                continue

            dimension = judgment.get("dimension", "Unknown")
            score = judgment.get("score", "N/A")

            with st.expander(f"**{dimension.capitalize()}** - Score: {score}", expanded=(idx == 0)):
                # Scores
                if "scores" in judgment and isinstance(judgment["scores"], list):
                    st.markdown("#### 📊 Scores")
                    for idx, score in enumerate(judgment["scores"]):
                        # Color coding based on score
                        if isinstance(score, (int, float)):
                            if score >= 85:
                                color = "🟢"
                            elif score >= 70:
                                color = "🟡"
                            else:
                                color = "🔴"
                            score_display = f"{color} **{score}**"
                        else:
                            score_display = f"**{score}**"

                        if "models" in judgment and isinstance(judgment["models"], list):
                            st.markdown(f"##### {judgment['models'][idx]}: {score_display}")
                        else:
                            st.markdown(f"**Score:** {score_display}")

                # Reasoning
                if "reasoning" in judgment and isinstance(judgment["reasoning"], list):
                    st.markdown("#### 💭 Reasoning")
                    for idx, reason in enumerate(judgment["reasoning"]):
                        if "models" in judgment and isinstance(judgment["models"], list):
                            st.markdown(f"##### {judgment['models'][idx]}: \n")
                        st.markdown(reason)

                # Strengths
                if "strengths" in judgment and isinstance(judgment["strengths"], list):
                    st.markdown("#### ✅ Strengths")
                    for idx, strength_group in enumerate(judgment["strengths"]):
                        if "models" in judgment and isinstance(judgment["models"], list):
                            st.markdown(f"##### {judgment['models'][idx]}: \n")
                        if isinstance(strength_group, list):
                            for strength in strength_group:
                                if isinstance(strength, (str, list)):
                                    if isinstance(strength, str):
                                        st.write(f"• {strength}")
                                    elif isinstance(strength, list):
                                        for item in strength:
                                            if isinstance(item, str):
                                                st.write(f"  - {item}")

                # Weaknesses
                if "weaknesses" in judgment and isinstance(judgment["weaknesses"], list):
                    st.markdown("#### ❌ Weaknesses")
                    for idx, weakness_group in enumerate(judgment["weaknesses"]):
                        if "models" in judgment and isinstance(judgment["models"], list):
                            st.markdown(f"##### {judgment['models'][idx]}: \n")
                        if isinstance(weakness_group, list):
                            for weakness in weakness_group:
                                if isinstance(weakness, (str, list)):
                                    if isinstance(weakness, str):
                                        st.write(f"• {weakness}")
                                    elif isinstance(weakness, list):
                                        for item in weakness:
                                            if isinstance(item, str):
                                                st.write(f"  - {item}")

    # Metadata
    st.markdown("### 📝 Metadata")
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        if "report_id" in jdata:
            st.write(f"**Report ID:** `{jdata['report_id']}`")
        if "company_ticker" in jdata:
            st.write(f"**Company:** {jdata['company_ticker']}")
    with meta_col2:
        if "timestamp" in jdata:
            st.write(f"**Timestamp:** {jdata['timestamp']}")

    # Raw JSON toggle
    with st.expander("🔧 View Raw JSON"):
        st.json(jdata)


def main(limit: int, status_filter: str, company_filter: str) -> None:
    st.title("⚖️ LLM Judgement Logs")
    st.markdown("View and analyze data from the n8n_llm_judgement_logs table")

    try:
        with st.spinner("Loading judgement logs..."):
            rows = fetch_judgements(limit)

        if not rows:
            st.warning("No judgement logs found in the database.")
            return

        # Apply filters
        filtered_rows = rows
        if status_filter != "All":
            filtered_rows = [row for row in filtered_rows if row.get("status") == status_filter]

        if company_filter:
            filtered_rows = [
                row
                for row in filtered_rows
                if company_filter.lower() in (row.get("company_ticker") or "").lower()
            ]

        st.write(f"Showing {len(filtered_rows)} of {len(rows)} records")

        if not filtered_rows:
            st.info("No records match the selected filters.")
            return

        summary_records = []
        option_labels = []
        label_to_row: Dict[str, Dict[str, Any]] = {}

        for row in filtered_rows:
            summary_records.append(
                {
                    "ID": row.get("id"),
                    "Judge Exec ID": row.get("judge_n8n_execution_id"),
                    "Report Exec ID": row.get("report_n8n_execution_id"),
                    "Company": row.get("company_ticker"),
                    "Status": row.get("status"),
                    "Logged At": row.get("logged_at"),
                    "Query Preview": (row.get("query") or "")[:80],
                }
            )

            label = (
                f"[{row.get('status', 'Unknown')}] "
                f"{row.get('company_ticker', 'N/A')} | JudgeExec {row.get('judge_n8n_execution_id') or row.get('id')} | "
                f"ReportExec {row.get('report_n8n_execution_id', 'Unknown')}"
            )
            if row.get("query"):
                label += f" | {row['query'][:60]}{'...' if len(row['query']) > 60 else ''}"

            option_labels.append(label)
            label_to_row[label] = row

        st.subheader("Judgement Summary")
        st.dataframe(summary_records, hide_index=True, width="stretch")

        st.divider()
        selection_placeholder = "-- Select a judgement to inspect --"
        selected_label = st.selectbox(
            "Judgement Details",
            options=[selection_placeholder] + option_labels,
            index=0,
            key="judgement_execution_select",
        )

        selected_row = label_to_row.get(selected_label)

        if selected_row:
            st.markdown("### Detailed View")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**ID:** {selected_row.get('id')}")
                st.write(f"**Judge Exec ID:** {selected_row.get('judge_n8n_execution_id')}")
            with col2:
                st.write(f"**Report Exec ID:** {selected_row.get('report_n8n_execution_id')}")
                st.write(f"**Workflow ID:** {selected_row.get('workflow_id')}")
            with col3:
                st.write(f"**Status:** {selected_row.get('status')}")
                st.write(f"**Logged At:** {selected_row.get('logged_at')}")

            if selected_row.get("company_ticker"):
                st.write(f"**Company:** {selected_row.get('company_ticker')}")

            if selected_row.get("query"):
                st.subheader("Full Query")
                st.text_area(
                    "Query",
                    selected_row["query"],
                    height=100,
                    key=f"judgement_query_{selected_row.get('id')}",
                )

            jdata = selected_row.get("judgement_data")
            if jdata is not None:
                st.subheader("Judgement Data")
                _display_judgement_data(jdata, selected_row.get("id"))

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.exception(e)
