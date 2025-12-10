import streamlit as st

# Import the tab modules
from LLMJudges_frontend.src import judgement_tab, report_tab
from LLMJudges_frontend.src.utils import (
    authenticate_user,
    get_logged_in_user,
    logout_user,
)


def main() -> None:
    # Intentionally not calling st.set_page_config here to avoid conflicts
    # with internal pages that may set it themselves (e.g., report_tab.main).
    st.title("FROAV_LLM DashboardSS")

    # Sidebar login/logout section
    st.sidebar.header("Authentication")
    logged_in_user = get_logged_in_user()

    if logged_in_user:
        # User is logged in - show user info and logout button
        user_name = logged_in_user.get("user_name", "User")
        st.sidebar.write(f"Logged in as: **{user_name}**")
        if st.sidebar.button("Logout", key="sidebar_logout", use_container_width=True):
            logout_user()
            st.rerun()
    else:
        # User is not logged in - show login form
        with st.sidebar.form("sidebar_login_form", clear_on_submit=False):
            st.write("🔐 Please login to provide feedback")
            user_name = st.text_input(
                "User Name",
                placeholder="Enter your user name",
                help="Your registered user name",
                key="sidebar_user_name",
            )
            user_token = st.text_input(
                "User Token",
                type="password",
                placeholder="Enter your user token",
                help="Your authentication token",
                key="sidebar_user_token",
            )
            login_submitted = st.form_submit_button("Login", use_container_width=True)

        if login_submitted:
            if not user_name.strip():
                st.sidebar.error("User name is required.")
            elif not user_token.strip():
                st.sidebar.error("User token is required.")
            else:
                user_data = authenticate_user(user_name.strip(), user_token.strip())
                if user_data:
                    st.session_state["feedback_user"] = user_data
                    st.sidebar.success(f"Welcome, {user_data['user_name']}!")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid user name or token. Please try again.")

    st.sidebar.divider()

    # Sidebar filters
    st.sidebar.header("Filters")

    limit = st.sidebar.selectbox(
        "Number of records to display",
        options=[5, 10, 25, 50, 100, 200],
        index=1,
        key="judgement_limit_select",
    )

    status_filter = st.sidebar.selectbox(
        "Filter by status",
        options=["All", "success", "error", "running", "waiting"],
        index=0,
        key="judgement_status_select",
    )

    company_filter = st.sidebar.text_input(
        "Filter by company ticker", placeholder="e.g., META, AAPL", key="judgement_company_input"
    )

    # Add simple button-style CSS for tabs
    st.markdown(
        """
        <style>
        .stTabs [data-baseweb="tab"] {
            border: 2px solid #d1d5db;
            /* background-color: #595959; */
            border-radius: 4px;
            padding: 20px 40px;
        }
        .stTabs [data-testid="stMarkdownContainer"] {
            font-size: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["📊 Report", "⚖️ Judgement"])

    with tabs[0]:
        # Render the report tab as the first, switchable tab
        report_tab.main(limit, status_filter, company_filter)

    with tabs[1]:
        # Render the judgement tab
        judgement_tab.main(limit, status_filter, company_filter)


if __name__ == "__main__":
    main()
