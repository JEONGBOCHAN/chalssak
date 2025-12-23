# -*- coding: utf-8 -*-
"""
Agent implementation with Agentic Loop (ReAct pattern).

This module provides:
- Observation: A dataclass recording one thought-action-observation cycle
- AgentConfig: Configuration for Agent behavior
- Agent: Main agent class implementing the Agentic Loop
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Callable

from src.agent.base import Tool, ToolResult
from src.agent.registry import ToolRegistry


# System prompt for the RAG agent
RAG_AGENT_SYSTEM_PROMPT = """You are a document analysis assistant. Your task is to answer user questions based on uploaded documents.

## Available Tools
You have access to the following tools:
1. **search_documents**: Search for relevant information in the uploaded documents
2. **finish**: Complete the task and provide the final answer

## Instructions
1. When the user asks a question, use the search_documents tool to find relevant information
2. If the search results are insufficient, try searching with different keywords
3. Once you have enough information, use the finish tool to provide a complete answer
4. Always cite your sources in the answer

## Important Rules
- You MUST use the finish tool to complete the task
- Include citations from the documents in your final answer
- If no relevant information is found after searching, inform the user honestly
- Do not make up information - only use what you find in the documents
"""


@dataclass
class Observation:
    """
    Record of one thought-action-observation cycle.

    Each observation captures:
    - What the LLM was thinking (thinking)
    - What tool it decided to use (tool_name)
    - What parameters it passed (tool_input)
    - The result of executing the tool (result)
    """

    thinking: Optional[str]
    tool_name: str
    tool_input: dict
    result: ToolResult


@dataclass
class AgentConfig:
    """
    Configuration for Agent behavior.

    Attributes:
        max_iterations: Maximum number of iterations (prevents infinite loops)
        max_result_chars: Maximum length of tool results (context management)
        verbose: Whether to print detailed logs
    """

    max_iterations: int = 3  # Default to 3 to save tokens
    max_result_chars: int = 8000
    verbose: bool = False


class Agent:
    """
    Agent with Agentic Loop implementation for document Q&A.

    The Agent follows the ReAct pattern:
    1. Think: LLM decides what to do next
    2. Act: Execute the chosen tool
    3. Observe: Record the result and update context
    4. Repeat until finish or max_iterations

    Design Principles:
    - Uses Gemini's function calling for tool selection
    - Explicit Termination: Uses 'finish' tool to signal completion
    - Error Propagation: Tool errors are sent back to LLM as ToolResult
    """

    def __init__(
        self,
        gemini_service,
        tools: list[Tool],
        system_prompt: str = RAG_AGENT_SYSTEM_PROMPT,
        config: AgentConfig | None = None,
    ):
        """
        Initialize Agent.

        Args:
            gemini_service: GeminiService instance for LLM calls
            tools: List of tools available to the agent
            system_prompt: System prompt defining agent's role
            config: Agent configuration (uses default if None)
        """
        self.gemini = gemini_service
        self.registry = ToolRegistry(tools)
        self.system_prompt = system_prompt
        self.config = config or AgentConfig()

        # State
        self.observations: list[Observation] = []
        self.messages: list[dict] = []
        self.is_finished: bool = False
        self.final_result: str | None = None
        self.sources_used: list[dict] = []

    def run(self, channel_id: str, query: str, conversation_history: list[dict] = None) -> dict:
        """
        Execute the agent on a given query.

        Implements the Agentic Loop:
        1. Call LLM with current context and tools
        2. Check termination condition (finish tool or max_iterations)
        3. Execute the tool chosen by LLM
        4. Record observation
        5. Update message history
        6. Repeat

        Args:
            channel_id: The channel ID to search in
            query: User's question
            conversation_history: Previous conversation for context

        Returns:
            dict with 'response', 'sources', and 'iterations'
        """
        # Initialize state
        self.observations = []
        self.is_finished = False
        self.final_result = None
        self.sources_used = []

        # Build initial messages
        self.messages = []
        if conversation_history:
            self.messages.extend(conversation_history)
        self.messages.append({"role": "user", "content": query})

        self._log(f"Starting Agent with query: {query}")
        self._log(f"Max iterations: {self.config.max_iterations}")
        self._log(f"Available tools: {self.registry.list_names()}")

        iteration = 0
        accumulated_context = []

        while iteration < self.config.max_iterations:
            iteration += 1
            self._log(f"\n--- Iteration {iteration}/{self.config.max_iterations} ---")

            # 1. Call LLM with tools
            response = self._call_llm_with_tools(query, accumulated_context)

            if response is None:
                self._log("LLM call failed. Terminating.")
                self.final_result = "Failed to get response from AI."
                break

            # 2. Check if LLM wants to call a tool
            tool_call = response.get("tool_call")

            if not tool_call:
                # LLM didn't call a tool - use text response as final answer
                self._log("LLM returned text response without tool call.")
                self.final_result = response.get("text", "No response generated.")
                self.is_finished = True
                break

            tool_name = tool_call.get("name")
            tool_input = tool_call.get("args", {})

            self._log(f"Tool call: {tool_name}")
            self._log(f"Tool input: {tool_input}")

            # 3. Check if finish tool
            if tool_name == "finish":
                self._log("Finish tool called. Terminating normally.")
                self.is_finished = True
                self.final_result = tool_input.get("answer", "Task completed.")
                if "sources_used" in tool_input:
                    # Record sources from the finish call
                    for source_name in tool_input.get("sources_used", []):
                        self.sources_used.append({"source": source_name, "content": ""})
                break

            # 4. Execute tool
            result = self._execute_tool(tool_name, tool_input, channel_id)

            self._log(f"Tool result - success: {result.success}")
            if result.success:
                self._log(f"Output preview: {result.output[:200]}...")
            else:
                self._log(f"Error: {result.error}")

            # 5. Record observation
            obs = Observation(
                thinking=response.get("thinking"),
                tool_name=tool_name,
                tool_input=tool_input,
                result=result,
            )
            self.observations.append(obs)

            # 6. Add to accumulated context for next iteration
            accumulated_context.append({
                "tool": tool_name,
                "input": tool_input,
                "result": result.output if result.success else f"Error: {result.error}"
            })

            # Extract sources from search results
            if tool_name == "search_documents" and result.success:
                self._extract_sources(result.output)

        # Handle max_iterations without finish
        if iteration >= self.config.max_iterations and not self.is_finished:
            self._log(f"\nMax iterations ({self.config.max_iterations}) reached. Generating final answer...")
            # Force generate an answer with accumulated context
            self.final_result = self._generate_forced_answer(query, accumulated_context)

        self._log(f"\n=== Agent Finished ===")
        self._log(f"Total iterations: {iteration}")
        self._log(f"Final result length: {len(self.final_result) if self.final_result else 0}")

        return {
            "response": self.final_result or "No response generated.",
            "sources": self.sources_used,
            "iterations": iteration,
        }

    def _call_llm_with_tools(self, query: str, context: list[dict]) -> Optional[dict]:
        """
        Call LLM with tools and context.

        Returns:
            dict with 'text', 'tool_call', and 'thinking'
        """
        try:
            # Build the prompt with context
            prompt_parts = [self.system_prompt, f"\n\nUser Question: {query}"]

            if context:
                prompt_parts.append("\n\n## Previous Actions and Results:")
                for i, ctx in enumerate(context, 1):
                    prompt_parts.append(f"\n### Action {i}: {ctx['tool']}")
                    prompt_parts.append(f"Input: {json.dumps(ctx['input'], ensure_ascii=False)}")
                    # Truncate long results
                    result_preview = ctx['result'][:self.config.max_result_chars]
                    if len(ctx['result']) > self.config.max_result_chars:
                        result_preview += f"\n...(truncated, {len(ctx['result'])} total chars)"
                    prompt_parts.append(f"Result: {result_preview}")

            prompt_parts.append("\n\nBased on the above, decide your next action. Use search_documents to find more information, or use finish to provide the final answer.")

            full_prompt = "\n".join(prompt_parts)

            # Call Gemini with function calling
            result = self.gemini.call_with_tools(
                prompt=full_prompt,
                tools=self.registry.get_all_for_gemini(),
            )

            return result

        except Exception as e:
            self._log(f"LLM call error: {e}")
            return None

    def _execute_tool(self, tool_name: str, tool_input: dict, channel_id: str) -> ToolResult:
        """
        Execute a tool and return the result.
        """
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}. Available: {self.registry.list_names()}"
            )

        # Set channel_id for search tool
        if hasattr(tool, 'set_channel_id'):
            tool.set_channel_id(channel_id)

        # Execute tool
        result = tool.execute(**tool_input)

        # Truncate output if too long
        if result.success and len(result.output) > self.config.max_result_chars:
            original_length = len(result.output)
            result.output = (
                result.output[:self.config.max_result_chars]
                + f"\n\n...(truncated, {original_length} total chars)"
            )

        return result

    def _extract_sources(self, search_output: str):
        """Extract source names from search results."""
        import re
        # Pattern: [Source N: filename]
        pattern = r'\[Source \d+: ([^\]]+)\]'
        matches = re.findall(pattern, search_output)
        for match in matches:
            if not any(s.get("source") == match for s in self.sources_used):
                self.sources_used.append({"source": match, "content": ""})

    def _generate_forced_answer(self, query: str, context: list[dict]) -> str:
        """Generate an answer when max iterations reached without finish."""
        try:
            prompt_parts = [
                "Based on the search results below, provide a concise answer to the question.",
                f"\nQuestion: {query}",
                "\n\nSearch Results:"
            ]

            for ctx in context:
                if ctx["tool"] == "search_documents":
                    prompt_parts.append(ctx["result"])

            prompt_parts.append("\n\nProvide your answer now. Cite sources where possible.")

            prompt = "\n".join(prompt_parts)

            # Simple generation without tools
            result = self.gemini.generate(prompt)
            return result.get("text", "Unable to generate answer.")

        except Exception as e:
            return f"Failed to generate answer: {str(e)}"

    def _log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.config.verbose:
            print(f"[Agent] {message}")

    def get_execution_summary(self) -> dict:
        """Get execution summary for debugging."""
        tool_usage = {}
        error_count = 0

        for obs in self.observations:
            tool_usage[obs.tool_name] = tool_usage.get(obs.tool_name, 0) + 1
            if not obs.result.success:
                error_count += 1

        return {
            "total_iterations": len(self.observations),
            "is_finished": self.is_finished,
            "final_result_length": len(self.final_result) if self.final_result else 0,
            "tool_usage": tool_usage,
            "error_count": error_count,
            "sources_found": len(self.sources_used),
        }
