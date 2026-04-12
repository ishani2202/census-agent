# frontend/app.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv
from app.agent import run

load_dotenv()

st.set_page_config(
    page_title="US Census Chat Agent",
    page_icon="🇺🇸",
    layout="centered"
)

st.markdown("""
<style>
    .stExpander { border: 1px solid #e0e0e0; border-radius: 8px; }
    div[data-testid="stSidebarContent"] { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## 🇺🇸 US Census Chat Agent")
            st.markdown("#### Sign in to continue")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            if st.button("Sign in", use_container_width=True, type="primary"):
                if (username == os.getenv("APP_USERNAME", "snowflake") and
                        password == os.getenv("APP_PASSWORD", "census2024")):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True


def main():
    if not check_password():
        return

    with st.sidebar:
        st.markdown("## 🇺🇸 Census Agent")
        st.markdown("---")
        st.markdown("**Try asking:**")
        examples = [
            "Median income in California?",
            "Poverty rate in Texas?",
            "Population of New York?",
            "Median rent in LA County?",
            "Health insurance in Florida?",
            "Income change 2019 vs 2020 in CA?",
            "College degree rate in Washington?",
            "Unemployment rate in Illinois?",
        ]
        for example in examples:
            if st.button(example, use_container_width=True, key=f"ex_{example}"):
                st.session_state.prefill = example

        st.markdown("---")
        st.markdown("**Data coverage:**")
        st.markdown("""
- 📅 2019 & 2020 ACS 5-year estimates
- 🗺️ State & county level
- 👥 ~242,000 Census Block Groups
- 📊 8,120+ demographic variables
        """)
        st.markdown("---")
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.history = []
            st.rerun()

        st.caption("Built on US Census ACS data via Snowflake Marketplace")

    st.markdown("## 🇺🇸 US Census Chat Agent")
    st.caption("Ask questions about US population, income, housing, education, and more.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "prefill" not in st.session_state:
        st.session_state.prefill = None

    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #666;">
            <p style="font-size: 16px;">Ask me anything about US demographics, income, housing, education, and more.</p>
            <p style="font-size: 13px;">Data sourced from the US Census ACS 2019 & 2020 5-year estimates.</p>
        </div>
        """, unsafe_allow_html=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sql"):
                with st.expander("🔍 View SQL query"):
                    st.code(message["sql"], language="sql")

    prefill_value = st.session_state.prefill
    if prefill_value:
        st.session_state.prefill = None

    prompt = st.chat_input("Ask a question about US Census data...")

    if prefill_value and not prompt:
        prompt = prefill_value

    if prompt:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Querying Census data..."):
                response = run(prompt, st.session_state.history)

            answer = response.get("answer", "")
            sql = response.get("sql")
            blocked = response.get("blocked", False)

            st.markdown(answer)

            if sql and not blocked:
                with st.expander("🔍 View SQL query"):
                    st.code(sql, language="sql")

        st.session_state.history.append({
            "user": prompt,
            "plan": response.get("plan", {}),
            "answer": answer
        })

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sql": sql if not blocked else None
        })

        st.rerun()


if __name__ == "__main__":
    main()