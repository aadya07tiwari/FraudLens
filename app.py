"""
FraudLens - Streamlit Chat Interface (Member A)
------------------------------------------------
Wires together:
  1. Intent Agent   -> structured JSON intent
  2. NL-to-SQL Agent -> validated, read-only SQL + query execution

Shows full transparency per demo requirements: the intent JSON, the
generated SQL, and the result table, for every question asked.

Run with:
    streamlit run app.py
"""

import os
import traceback

import streamlit as st
from dotenv import load_dotenv

from agents.intent_agent import parse_intent
from agents.sql_agent import generate_sql, run_query, UnsafeSQLError

from landing import render_landing, apply_console_theme, render_console_header, sidebar_pill
render_landing()  # shows landing/login page and st.stop()s unless ?page=console

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "db/fraudlens.db")
MAX_ROW_LIMIT = int(os.getenv("MAX_ROW_LIMIT", "200"))

# set_page_config must be the first Streamlit call on this page, so it
# comes right after render_landing() (which already st.stop()'d for the
# landing/login pages) and before apply_console_theme() / anything else.
st.set_page_config(page_title="FraudLens", page_icon="🔍", layout="wide")
apply_console_theme()  # reskins this chat UI to match the landing page's brand

render_console_header(
    subtitle="Ask questions about transaction data in plain English. Every step is shown for full transparency."
)


if not os.path.exists(DB_PATH):
    st.warning(
        f"No database found at `{DB_PATH}`. Run this first:\n\n"
        f"`python data/setup_db.py --sample` (quick demo data)\n\n"
        f"or\n\n`python data/setup_db.py --csv <path_to_paysim_csv>`"
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("intent"):
            with st.expander("🧠 Intent JSON"):
                st.json(msg["intent"])
        if msg.get("sql"):
            with st.expander("🗄️ Generated SQL"):
                st.code(msg["sql"], language="sql")
        if msg.get("dataframe") is not None:
            st.dataframe(msg["dataframe"], use_container_width=True)

user_question = st.chat_input("e.g. Show me the top 10 largest TRANSFER transactions flagged as fraud")

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        intent = None
        sql = None
        df = None
        reply_text = ""

        try:
            with st.spinner("Understanding your question..."):
                intent = parse_intent(user_question)

            if intent["task"] == "unknown" or intent.get("clarification_needed"):
                reply_text = intent.get("clarification_needed") or (
                    "I couldn't map that to a transaction-data question. "
                    "Could you rephrase it in terms of accounts, transaction types, amounts, or time range?"
                )
            else:
                with st.spinner("Writing SQL query..."):
                    sql = generate_sql(intent, max_row_limit=MAX_ROW_LIMIT)

                with st.spinner("Running query..."):
                    df = run_query(sql, DB_PATH)

                reply_text = f"Found **{len(df)}** matching row(s)."

            st.markdown(reply_text)

            if intent:
                with st.expander("🧠 Intent JSON"):
                    st.json(intent)
            if sql:
                with st.expander("🗄️ Generated SQL"):
                    st.code(sql, language="sql")
            if df is not None:
                st.dataframe(df, use_container_width=True)

        except UnsafeSQLError as e:
            reply_text = f"⚠️ Blocked an unsafe query before execution: {e}"
            st.error(reply_text)
        except Exception as e:
            reply_text = f"⚠️ Something went wrong: {e}"
            st.error(reply_text)
            with st.expander("Details"):
                st.code(traceback.format_exc())

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply_text,
            "intent": intent,
            "sql": sql,
            "dataframe": df,
        })

with st.sidebar:
    st.header("About")
    st.markdown(
        "**FraudLens** demonstrates an Intent Agent + NL-to-SQL Agent pipeline "
        "over PaySim-style transaction data, with full transparency into "
        "every intermediate step."
    )
    sidebar_pill("DB PATH", DB_PATH)
    sidebar_pill("ROW CAP", str(MAX_ROW_LIMIT))
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()