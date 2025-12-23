# -*- coding: utf-8 -*-
"""
Tools for Docuchat Agent.

Available tools:
- SearchDocumentsTool: Search documents in a channel
- FinishTool: Signal task completion with final answer
"""

from typing import Callable, Optional

from src.agent.base import Tool, ToolResult


class SearchDocumentsTool(Tool):
    """
    Search documents in a channel using Gemini File Search API.

    This tool allows the agent to search for information in uploaded documents.
    The agent can refine the query and search multiple times if needed.
    """

    def __init__(self, search_fn: Callable[[str, str], dict]):
        """
        Initialize SearchDocumentsTool.

        Args:
            search_fn: Function that takes (channel_id, query) and returns search results
        """
        self._search_fn = search_fn
        self._channel_id: Optional[str] = None

    def set_channel_id(self, channel_id: str):
        """Set the channel ID for searches."""
        self._channel_id = channel_id

    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return """Search for information in the uploaded documents.
Use this tool to find relevant content that can help answer the user's question.
You can search multiple times with different queries if the initial results are insufficient.
The search returns relevant text chunks with source information."""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant information in documents. Be specific and use keywords from the user's question."
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str) -> ToolResult:
        """Execute document search."""
        try:
            if not self._channel_id:
                return ToolResult(
                    success=False,
                    output="",
                    error="Channel ID not set. Cannot perform search."
                )

            result = self._search_fn(self._channel_id, query)

            if "error" in result and result["error"]:
                return ToolResult(
                    success=False,
                    output="",
                    error=result["error"]
                )

            # Format search results
            sources = result.get("sources", [])
            if not sources:
                return ToolResult(
                    success=True,
                    output="No relevant documents found for this query. Try a different search query."
                )

            # Format sources for the agent
            formatted_results = []
            for i, source in enumerate(sources, 1):
                source_name = source.get("source", "unknown")
                content = source.get("content", "")
                formatted_results.append(f"[Source {i}: {source_name}]\n{content}")

            output = "\n\n---\n\n".join(formatted_results)
            return ToolResult(
                success=True,
                output=f"Found {len(sources)} relevant sections:\n\n{output}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}"
            )


class FinishTool(Tool):
    """
    Signal that the task is complete and provide the final answer.

    The agent MUST call this tool when it has gathered enough information
    and is ready to provide the final answer to the user.
    """

    @property
    def name(self) -> str:
        return "finish"

    @property
    def description(self) -> str:
        return """Call this tool when you have gathered enough information and are ready to provide the final answer.
You MUST call this tool to complete the task.
Include the complete answer with citations to the sources you found."""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The complete final answer to the user's question. Include relevant citations from the sources you found."
                },
                "sources_used": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of source document names that were used to generate the answer."
                }
            },
            "required": ["answer"]
        }

    def execute(self, answer: str, sources_used: list[str] = None) -> ToolResult:
        """Execute finish - just returns the answer."""
        return ToolResult(
            success=True,
            output=answer
        )
