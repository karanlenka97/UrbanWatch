import json
import uuid

import streamlit as st
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from langchain.agents import create_agent

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
