# -*- coding: utf-8 -*-
"""
Tool Registry for managing available tools.

Provides centralized tool management and lookup for the Agent.
"""

from typing import Optional

from src.agent.base import Tool


class ToolRegistry:
    """
    Registry for managing tools available to the Agent.

    Provides:
    - Tool registration and lookup by name
    - Conversion to Gemini function calling format
    """

    def __init__(self, tools: list[Tool]):
        """
        Initialize ToolRegistry with a list of tools.

        Args:
            tools: List of Tool instances to register
        """
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        """
        Get all registered tools.

        Returns:
            List of all Tool instances
        """
        return list(self._tools.values())

    def get_all_for_gemini(self) -> list[dict]:
        """
        Get all tools in Gemini function calling format.

        Returns:
            List of tool definitions for Gemini API
        """
        return [tool.to_gemini_format() for tool in self._tools.values()]

    def list_names(self) -> list[str]:
        """
        Get list of all tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())
