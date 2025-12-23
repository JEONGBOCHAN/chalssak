# -*- coding: utf-8 -*-
"""
Agent module for Docuchat.

Provides an agentic loop implementation for document Q&A.
"""

from src.agent.base import Tool, ToolResult
from src.agent.tools import SearchDocumentsTool, FinishTool
from src.agent.registry import ToolRegistry
from src.agent.agent import Agent, AgentConfig, Observation

__all__ = [
    "Tool",
    "ToolResult",
    "SearchDocumentsTool",
    "FinishTool",
    "ToolRegistry",
    "Agent",
    "AgentConfig",
    "Observation",
]
