"""
Streamlit frontend for displaying n8n execution data from n8n_report_model_logs table.

This application provides a web interface to view and analyze execution logs
from the n8n workflow system.
"""

import json
import os
from typing import Any, Dict, List

import streamlit as st

from LLMJudges_frontend.src.feedback_window import render_feedback_form
from LLMJudges_frontend.src.utils import (
    get_db_connection,
    get_logged_in_user,
    get_user_feedback_execution_ids,
)


@st.cache_data(ttl=5)  # Cache for 5 seconds
def fetch_executions(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch execution logs from database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
            SELECT * FROM n8n_report_model_logs 
            ORDER BY logged_at DESC 
            LIMIT %s
            """
            cur.execute(query, (limit,))
            colnames = [desc[0] for desc in cur.description]
            rows: List[Dict[str, Any]] = []
            for rec in cur.fetchall():
                row = {col: val for col, val in zip(colnames, rec)}
                # Parse JSON execution_data if it's a string
                exec_data = row.get("execution_data")
                if isinstance(exec_data, str):
                    try:
                        row["execution_data"] = json.loads(exec_data)
                    except Exception:
                        pass
                # Parse report_groups from string to list
                report_groups = row.get("report_groups")
                if isinstance(report_groups, str):
                    try:
                        row["report_groups"] = json.loads(report_groups)
                    except Exception:
                        # If parsing fails, try to extract numbers from the string
                        # Handle cases like "[1,2,3]" or "1,2,3" or "[1, 2, 3]"
                        try:
                            # Remove brackets and whitespace, then split by comma
                            cleaned = report_groups.strip().strip("[]").strip()
                            if cleaned:
                                row["report_groups"] = [
                                    int(x.strip())
                                    for x in cleaned.split(",")
                                    if x.strip().isdigit()
                                ]
                            else:
                                row["report_groups"] = []
                        except Exception:
                            row["report_groups"] = []
                elif report_groups is None:
                    row["report_groups"] = []
                rows.append(row)
            return rows


def display_execution_data(execution_data: Dict[str, Any], execution_id: int) -> List[str]:
    """Display raw execution data in a structured way."""
    st.write("**Raw Execution Data:**")

    # Collect filenames from mid_steps for download links
    collected_filenames = []

    # Collect observations with (pageContent, page_index, filename)
    collected_observations = []
    logged_observation_chunks = set()

    # Display main fields
    if "output" in execution_data:
        with st.expander("**Report content**"):

            output = execution_data["output"]

            # Create a card-style container for the markdown content
            st.markdown(
                f"""
            <div style="
                background-color: #262626;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
            <h3 style="margin-top: 0; color: #DCDCDC;">📄 Full Output Content</h3>
            {output}
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Display mid_steps
    if "mid_steps" in execution_data:
        with st.expander("**Mid Steps:**"):

            mid_steps = execution_data["mid_steps"]
            if isinstance(mid_steps, list):
                with st.expander(f"**Mid Steps** ({len(mid_steps)} steps)", expanded=False):
                    for step_idx, step in enumerate(mid_steps):
                        with st.expander(f"Step {step_idx+1} (Execution {execution_id})"):
                            # Enhanced display for mid_steps with better formatting
                            if isinstance(step, dict):
                                # Display action section
                                if "action" in step:
                                    st.write("**Action:**")
                                    action = step["action"]
                                    if isinstance(action, dict):
                                        # Display tool information if available
                                        if "tool" in action:
                                            st.write(f"**Tool:** `{action['tool']}`")
                                        if "toolInput" in action:
                                            st.write("**Tool Input:**")
                                            st.json(action["toolInput"])

                                    else:
                                        st.json(action)

                                # Display observation section with enhanced formatting
                                if "observation" in step:
                                    st.write("**Observation:**")
                                    observation = step["observation"]

                                    # Try to parse observation as JSON if it's a string
                                    if isinstance(observation, str):
                                        try:
                                            import json

                                            parsed_observation = json.loads(observation)
                                            if isinstance(parsed_observation, list):
                                                st.write(
                                                    f"**Found {len(parsed_observation)} observation items:**"
                                                )
                                                for obs_idx, obs_item in enumerate(
                                                    parsed_observation
                                                ):
                                                    st.markdown(
                                                        f"<span style='color: #ffff80; font-weight: bold;'>Observation Item {obs_idx+1}</span>",
                                                        unsafe_allow_html=True,
                                                    )
                                                    with st.expander(
                                                        "Click to expand", expanded=False
                                                    ):
                                                        if (
                                                            isinstance(obs_item, dict)
                                                            and "type" in obs_item
                                                            and "text" in obs_item
                                                        ):
                                                            st.write(
                                                                f"**Type:** {obs_item['type']}"
                                                            )
                                                            st.write("**Text Content:**")
                                                            # Try to parse the text content as JSON for better display
                                                            try:
                                                                text_content = json.loads(
                                                                    obs_item["text"]
                                                                )
                                                                st.json(text_content)

                                                                # Extract observation data (pageContent, page_index, filename)
                                                                if isinstance(text_content, dict):
                                                                    page_content = text_content.get(
                                                                        "pageContent", ""
                                                                    )
                                                                    page_index = None
                                                                    filename = None
                                                                    chunk_index = None

                                                                    # Extract metadata if available
                                                                    if "metadata" in text_content:
                                                                        metadata = text_content[
                                                                            "metadata"
                                                                        ]
                                                                        if isinstance(
                                                                            metadata, dict
                                                                        ):
                                                                            filename = metadata.get(
                                                                                "file_name"
                                                                            )
                                                                            page_index = (
                                                                                metadata.get(
                                                                                    "page_index"
                                                                                )
                                                                            )
                                                                            chunk_index = (
                                                                                metadata.get(
                                                                                    "chunk_index"
                                                                                )
                                                                            )

                                                                            # Collect filename for download links
                                                                            if (
                                                                                filename
                                                                                and filename
                                                                                not in collected_filenames
                                                                            ):
                                                                                collected_filenames.append(
                                                                                    filename
                                                                                )

                                                                    # Collect observation if we have pageContent
                                                                    if (
                                                                        page_content
                                                                        and (filename, chunk_index)
                                                                        not in logged_observation_chunks
                                                                    ):
                                                                        logged_observation_chunks.add(
                                                                            (filename, chunk_index)
                                                                        )
                                                                        collected_observations.append(
                                                                            {
                                                                                "pageContent": page_content,
                                                                                "page_index": page_index,
                                                                                "chunk_index": chunk_index,
                                                                                "filename": filename,
                                                                            }
                                                                        )
                                                            except:
                                                                st.text(obs_item["text"])
                                                        else:
                                                            st.json(obs_item)
                                            else:
                                                st.json(parsed_observation)
                                        except json.JSONDecodeError:
                                            st.text(observation)
                                    else:
                                        st.json(observation)

                                # Display other step fields
                                other_step_fields = {
                                    k: v
                                    for k, v in step.items()
                                    if k not in ["action", "observation"]
                                }
                                if other_step_fields:
                                    st.write("**Other Step Fields:**")
                                    st.json(other_step_fields)
                            else:
                                st.json(step)
            else:
                with st.expander("**Mid Steps**", expanded=False):
                    st.json(mid_steps, key=f"mid_steps_{execution_id}")

    # Display other fields
    other_fields = {k: v for k, v in execution_data.items() if k not in ["output", "mid_steps"]}
    if other_fields:
        with st.expander("**Other Fields:**"):
            st.json(other_fields, key=f"other_fields_{execution_id}")

    # Display all collected observations
    if collected_observations:
        with st.expander("**Collected Observations(Reference sources from SEC filings):**"):

            st.subheader("📋 All Collected Observations(Reference sources from SEC filings)")
            st.write(f"**Total observations collected:** {len(collected_observations)}")
            collected_observations.sort(key=lambda x: (x["filename"], x["page_index"]))

            # Display observations in a 3-column layout
            num_cols = 3
            for row_start in range(0, len(collected_observations), num_cols):
                cols = st.columns(num_cols)
                for col_idx, col in enumerate(cols):
                    obs_idx = row_start + col_idx
                    if obs_idx < len(collected_observations):
                        obs = collected_observations[obs_idx]
                        with col:
                            with st.expander(
                                f"Observation {obs_idx+1}: {obs['filename'] or 'Unknown File'}"
                                + (
                                    f" - Page {obs['page_index']}"
                                    if obs["page_index"] is not None
                                    else ""
                                ),
                                expanded=False,
                            ):
                                # Display filename
                                if obs["filename"]:
                                    st.write(f"**Filename:** `{obs['filename']}`")
                                else:
                                    st.write("**Filename:** Not available")

                                # Display page index
                                if obs["page_index"] is not None:
                                    st.write(f"**Page Index:** {obs['page_index']}")
                                else:
                                    st.write("**Page Index:** Not available")

                                # Display chunk index
                                if obs["chunk_index"] is not None:
                                    st.write(f"**Chunk Index:** {obs['chunk_index']}")
                                else:
                                    st.write("**Chunk Index:** Not available")

                                # Display page content
                                st.write("**Page Content:**")
                                # Use a text area for better readability if content is long
                                st.text_area(
                                    "Content",
                                    obs["pageContent"],
                                    height=200,
                                    key=f"obs_content_{execution_id}_{obs_idx}",
                                    label_visibility="collapsed",
                                )
                                if len(obs["pageContent"]) > 500:
                                    st.caption(
                                        f"Showing preview (full content: {len(obs['pageContent'])} characters)"
                                    )

    # Display download links for collected filenames
    if collected_filenames:
        with st.expander("**Files Referenced in Execution:**"):

            st.subheader("📁 Files Referenced in Execution")
            st.write("The following files were referenced during this execution:")

            for filename in collected_filenames:
                # Create a download button for each file
                # Note: This assumes files are stored in a specific directory structure
                # You may need to adjust the file path based on your actual file storage
                base_dir = os.getcwd() + "/LLMJudges_server/"
                company_ticker = filename.split("_")[0]
                file_path = os.path.join(base_dir, "data", "company_data", company_ticker, filename)
                # Check if file exists (you might want to implement actual file checking)
                try:
                    with open(file_path, "rb") as f:
                        file_data = f.read()

                    st.download_button(
                        label=f"📄 Download {filename}",
                        data=file_data,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"download_{filename}_{execution_id}",
                    )
                except FileNotFoundError:
                    st.warning(f"File not found: {filename}")
                except Exception as e:
                    st.error(f"Error accessing file {filename}: {str(e)}")

            st.write(f"**Total files referenced:** {len(collected_filenames)}")


def main(limit: int, status_filter: str, company_filter: str) -> None:
    """Main Streamlit application."""
    st.set_page_config(page_title="N8N Execution Logs Viewer", page_icon="📊", layout="wide")

    st.title("📊 LLM Report Viewer")
    st.markdown("View and analyze execution data from the n8n_report_model_logs table")

    try:
        # Fetch data
        with st.spinner("Loading execution logs..."):
            rows = fetch_executions(limit)

        if not rows:
            st.warning("No execution logs found in the database.")
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

        # Filter by user groups if user is logged in
        logged_in_user = get_logged_in_user()
        if logged_in_user:
            user_groups_str = logged_in_user.get("user_groups")
            # Parse user_groups from string to list
            user_groups = []
            if user_groups_str:
                try:
                    user_groups = json.loads(user_groups_str)
                except Exception:
                    # If parsing fails, try to extract numbers from the string
                    try:
                        cleaned = user_groups_str.strip().strip("[]").strip()
                        if cleaned:
                            user_groups = [
                                int(x.strip()) for x in cleaned.split(",") if x.strip().isdigit()
                            ]
                    except Exception:
                        user_groups = []

            # Filter reports where at least one group number matches
            # If user has groups, only show reports with matching groups
            # If user has no groups, show no reports (empty list)
            if user_groups:
                filtered_rows = [
                    row
                    for row in filtered_rows
                    if row.get("report_groups")
                    and any(group in user_groups for group in row.get("report_groups", []))
                ]
            else:
                # User is logged in but has no groups - show no reports
                filtered_rows = []

        st.write(f"Showing {len(filtered_rows)} of {len(rows)} records")

        if not filtered_rows:
            st.info("No records match the selected filters.")
            return

        summary_records = []
        option_labels = []
        label_to_row: Dict[str, Dict[str, Any]] = {}

        # Get user name for feedback status (already retrieved above for group filtering)
        user_name = logged_in_user.get("user_name") if logged_in_user else None

        # Fetch all execution IDs with feedback for this user (batch query for efficiency)
        feedback_execution_ids = set()
        if user_name:
            feedback_execution_ids = get_user_feedback_execution_ids(user_name)

        for row in filtered_rows:
            # Check if feedback exists for this execution
            feedback_status = "—"
            if user_name:
                report_execution_id = str(row.get("n8n_execution_id") or row.get("id") or "")
                if report_execution_id and report_execution_id in feedback_execution_ids:
                    feedback_status = "✅ Yes"
                elif report_execution_id:
                    feedback_status = "❌ No"

            summary_records.append(
                {
                    "ID": row.get("id"),
                    "Execution ID": row.get("n8n_execution_id"),
                    "Company": row.get("company_ticker"),
                    "Status": row.get("status"),
                    "Logged At": row.get("logged_at"),
                    "Query Preview": (row.get("query") or "")[:80],
                    "Report Groups": row.get("report_groups"),
                    "Feedback Status": feedback_status,
                }
            )

            label = (
                f"[{row.get('status', 'Unknown')}] "
                f"{row.get('company_ticker', 'N/A')} | Exec {row.get('n8n_execution_id') or row.get('id')}"
            )
            if row.get("query"):
                label += f" | {row['query'][:60]}{'...' if len(row['query']) > 60 else ''}"

            option_labels.append(label)
            label_to_row[label] = row

        st.subheader("Execution Summary")
        st.dataframe(
            summary_records,
            hide_index=True,
            width="stretch",
        )

        st.divider()
        selection_placeholder = "-- Select an execution to inspect --"
        selected_label = st.selectbox(
            "Execution Details",
            options=[selection_placeholder] + option_labels,
            index=0,
            key="report_execution_select",
        )

        selected_row = label_to_row.get(selected_label)

        if selected_row:
            st.markdown("### 📄 Detailed View")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**ID:** {selected_row.get('id')}")
                st.write(f"**N8N Execution ID:** {selected_row.get('n8n_execution_id')}")
            with col2:
                st.write(f"**Status:** {selected_row.get('status')}")
                st.write(f"**Company:** {selected_row.get('company_ticker', 'N/A')}")
            with col3:
                st.write(f"**Logged At:** {selected_row.get('logged_at')}")
                if selected_row.get("query"):
                    st.write(f"**Query Length:** {len(selected_row.get('query', ''))} chars")

            if selected_row.get("query"):
                st.subheader("🔍 Full Query")
                st.text_area(
                    "Query",
                    selected_row["query"],
                    height=120,
                    key=f"query_{selected_row.get('id')}",
                )

            execution_data = selected_row.get("execution_data")
            if execution_data:
                st.subheader("🔍 Raw Execution Data")
                _ = display_execution_data(execution_data, selected_row.get("id"))

            render_feedback_form(selected_row)

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
