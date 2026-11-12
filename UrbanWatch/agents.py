#import all the required libraries
from dotenv import load_dotenv
load_dotenv()

import os
import requests

from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from tavily import TavilyClient
