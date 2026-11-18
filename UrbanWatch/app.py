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
