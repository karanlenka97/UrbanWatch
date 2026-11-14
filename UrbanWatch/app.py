import json
import uuid

import streamlit as st
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt

try:
    from agents import get_news, get_weather, llm
except ImportError as exc:
    raise ImportError(
        "app.py expects agents.py to export llm, get_weather, and get_news."
    ) from exc


@wrap_tool_call
def approval_middleware(request, handler):
    tool_call = request.tool_call
    decision = interrupt(
        {
            "tool_name": tool_call["name"],
            "tool_args": tool_call.get("args", {}),
            "tool_call_id": tool_call["id"],
        }
    )
    if decision != "approve":
        return ToolMessage(
            content="Tool call denied by user.",
            tool_call_id=tool_call["id"],
        )
    return handler(request)


def new_agent():
    return create_agent(
        llm,
        tools=[get_weather, get_news],
        system_prompt="You are a helpful city assistant for UrbanWatch.",
        middleware=[approval_middleware],
        checkpointer=InMemorySaver(),
    )


def render_message(message):
    if isinstance(message, HumanMessage):
        st.chat_message("user").write(message.content)
    elif isinstance(message, AIMessage):
        if message.content:
            st.chat_message("assistant").write(message.content)
        for call in getattr(message, "tool_calls", []):
            with st.chat_message("assistant"):
                st.caption(f"Requested tool: {call.get('name', 'tool')}")


def get_pending_approval(state):
    tasks = state.get("tasks", [])
    for task in tasks:
        for item in task.get("interrupts", []):
            value = getattr(item, "value", item)
            if isinstance(value, dict) and "tool_name" in value:
                return value
    return None


st.set_page_config(page_title="UrbanWatch AI", page_icon="🌦️")
st.title("🌦️ UrbanWatch AI")
st.caption("Ask about city weather and local news.")

if "agent" not in st.session_state:
    st.session_state.agent = new_agent()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None

for chat_message in st.session_state.messages:
    render_message(chat_message)

config = {"configurable": {"thread_id": st.session_state.thread_id}}
pending = st.session_state.pending_approval
if pending:
    st.warning(
        f"Allow **{pending['tool_name']}** with these arguments?\n\n"
        f"```json\n{json.dumps(pending.get('tool_args', {}), indent=2)}\n```"
    )
    approve_col, reject_col = st.columns(2)
    if approve_col.button("Approve", type="primary", use_container_width=True):
        try:
            result = st.session_state.agent.invoke(
                Command(resume="approve"), config=config
            )
            st.session_state.pending_approval = get_pending_approval(result)
            if not st.session_state.pending_approval:
                st.session_state.messages = result["messages"]
        except Exception as exc:
            st.error(f"Could not continue the request: {exc}")
            st.session_state.pending_approval = None
        st.rerun()
    if reject_col.button("Reject", use_container_width=True):
        try:
            result = st.session_state.agent.invoke(
                Command(resume="reject"), config=config
            )
            st.session_state.pending_approval = get_pending_approval(result)
            if not st.session_state.pending_approval:
                st.session_state.messages = result["messages"]
        except Exception as exc:
            st.error(f"Could not reject the request cleanly: {exc}")
        st.session_state.pending_approval = None
        st.rerun()

if not pending:
    prompt = st.chat_input("Ask UrbanWatch…")
    if prompt:
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.spinner("UrbanWatch is thinking…"):
            try:
                result = st.session_state.agent.invoke(
                    {"messages": [HumanMessage(content=prompt)]}, config=config
                )
                st.session_state.pending_approval = get_pending_approval(result)
                if not st.session_state.pending_approval:
                    st.session_state.messages = result["messages"]
            except Exception as exc:
                st.error(f"Request failed: {exc}")
        st.rerun()
