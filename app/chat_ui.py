
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tool_calling import run_agent

st.set_page_config(
    page_title="Project Status Agent",
    page_icon="🤖",
)

st.title("🤖 Project Status Agent")
st.caption("Ask questions about project status, ownership, and risks.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept a new question.
if prompt := st.chat_input("Ask about a project..."):
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = run_agent(prompt)
                answer = result["answer"]

                if isinstance(answer, dict):
                    response = answer.get("answer", str(answer))
                    st.markdown(response)

                    projects = answer.get("projects", [])
                    if projects:
                        st.dataframe(projects, use_container_width=True)
                else:
                    response = str(answer)
                    st.markdown(response)

                with st.expander("Inspect agent trace"):
                    trace = result.get("trace", {})
                    st.markdown(
                        f"**User query:** {trace.get('user_query')}"
                    )
                    st.json(trace)

            except Exception as e:
                response = f"Error: {type(e).__name__}: {e}"
                st.error(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
    })