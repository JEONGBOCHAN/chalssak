# -*- coding: utf-8 -*-
"""
Tool base classes for Docuchat Agent.

This module provides:
- ToolResult: A Pydantic model for tool execution results
- Tool: An abstract base class for all tools
"""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class ToolResult(BaseModel):
    """
    Result of a tool execution.

    Attributes:
        success: Whether the tool executed successfully
        output: The output of the tool (if successful)
        error: Error message (if failed)
    """

    success: bool
    output: str
    error: Optional[str] = None


class Tool(ABC):
    """
    Abstract base class for all tools.

    All tools must inherit from this class and implement:
    - name: Tool identifier (used by LLM to call the tool)
    - description: Human-readable description (helps LLM decide when to use)
    - parameters: JSON Schema defining the tool's parameters
    - execute: The actual implementation logic

    Design Principle:
    - Never raise exceptions from execute() - always return ToolResult
    - This prevents the Agent from crashing due to tool failures
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (used by LLM to invoke the tool)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description (helps LLM understand when to use this tool)."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """Parameter schema in JSON Schema format."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        IMPORTANT: This method must NEVER raise exceptions.
        All errors should be caught and returned as ToolResult(success=False, error=...).

        Args:
            **kwargs: Parameters defined in the parameters schema

        Returns:
            ToolResult: The result of execution (success or failure)
        """
        pass

    def to_gemini_format(self) -> dict:
        """
        Convert tool definition to Gemini function calling format.

        Returns:
            dict: Tool definition in Gemini format
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
