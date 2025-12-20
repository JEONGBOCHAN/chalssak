# -*- coding: utf-8 -*-
"""Gemini File Search API service."""

from functools import lru_cache
from typing import Any

import requests
from google import genai
from google.genai import types

from src.core.config import get_settings


class GeminiService:
    """Service for interacting with Gemini File Search API."""

    def __init__(self):
        """Initialize the Gemini client."""
        settings = get_settings()
        self._api_key = settings.google_api_key
        self._client = genai.Client(api_key=self._api_key)

    @property
    def client(self) -> genai.Client:
        """Get the Gemini client."""
        return self._client

    # ========== File Search Store (Channel) Operations ==========

    def create_store(self, display_name: str) -> dict[str, Any]:
        """Create a new File Search Store.

        Args:
            display_name: Human-readable name for the store

        Returns:
            Store information including name (ID)
        """
        store = self._client.file_search_stores.create(
            config={"display_name": display_name}
        )
        return {
            "name": store.name,
            "display_name": display_name,
        }

    def get_store(self, store_name: str) -> dict[str, Any] | None:
        """Get a File Search Store by name.

        Args:
            store_name: The store name/ID (e.g., "fileSearchStores/xxx")

        Returns:
            Store information or None if not found
        """
        try:
            store = self._client.file_search_stores.get(name=store_name)
            return {
                "name": store.name,
                "display_name": getattr(store, "display_name", ""),
            }
        except Exception:
            return None

    def list_stores(self) -> list[dict[str, Any]]:
        """List all File Search Stores.

        Returns:
            List of store information
        """
        stores = []
        for store in self._client.file_search_stores.list():
            stores.append({
                "name": store.name,
                "display_name": getattr(store, "display_name", ""),
            })
        return stores

    def delete_store(self, store_name: str, force: bool = True) -> bool:
        """Delete a File Search Store.

        Uses REST API directly because SDK doesn't support force delete.

        Args:
            store_name: The store name/ID
            force: Whether to force delete (removes all files first)

        Returns:
            True if deleted successfully
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}"
        if force:
            url += "?force=true"
        url += f"&key={self._api_key}" if force else f"?key={self._api_key}"

        response = requests.delete(url)
        return response.status_code == 200

    # ========== Document Operations ==========

    def upload_file(
        self,
        store_name: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Upload a file to a File Search Store.

        Args:
            store_name: The store name/ID
            file_path: Path to the file to upload

        Returns:
            Operation information
        """
        operation = self._client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
        )
        return {
            "name": operation.name,
            "done": operation.done,
        }

    def get_operation_status(self, operation_name: str) -> dict[str, Any]:
        """Get the status of an upload operation.

        Args:
            operation_name: The operation name/ID

        Returns:
            Operation status
        """
        try:
            operation = self._client.operations.get(operation_name)
            return {
                "name": operation.name,
                "done": operation.done,
            }
        except Exception:
            return {"name": operation_name, "done": False, "error": "Not found"}

    def list_store_files(self, store_name: str) -> list[dict[str, Any]]:
        """List all files in a File Search Store.

        Args:
            store_name: The store name/ID

        Returns:
            List of file information
        """
        files = []
        try:
            # Use REST API to list files in store
            url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}/files"
            url += f"?key={self._api_key}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for file_data in data.get("files", []):
                    files.append({
                        "name": file_data.get("name", ""),
                        "display_name": file_data.get("displayName", ""),
                        "size_bytes": file_data.get("sizeBytes", 0),
                        "state": file_data.get("state", ""),
                    })
        except Exception:
            pass
        return files

    def delete_file(self, file_name: str) -> bool:
        """Delete a file from File Search Store.

        Args:
            file_name: The file name/ID

        Returns:
            True if deleted successfully
        """
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
            url += f"?key={self._api_key}"
            response = requests.delete(url)
            return response.status_code == 200
        except Exception:
            return False

    # ========== Chat/Search Operations ==========

    def _build_conversation_contents(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[types.Content] | str:
        """Build conversation contents for multi-turn.

        Args:
            query: Current user query
            conversation_history: Previous messages with 'role' and 'content'

        Returns:
            List of Content objects or just the query string
        """
        if not conversation_history:
            return query

        contents = []

        # Add conversation history
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.get("content", ""))]
                )
            )

        # Add current query
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=query)]
            )
        )

        return contents

    def search_and_answer_stream(
        self,
        store_name: str,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
        model: str = "gemini-2.5-flash",
    ):
        """Search documents and generate a streaming answer.

        Uses Gemini File Search API to search documents in the store
        and generate a grounded response with streaming.

        Args:
            store_name: The store name/ID to search in
            query: The user's question
            conversation_history: Optional list of previous messages for context
            model: The model to use for generation

        Yields:
            Chunks of the response as they are generated
        """
        try:
            # Build contents with conversation history for multi-turn
            contents = self._build_conversation_contents(query, conversation_history)

            response_stream = self._client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ]
                ),
            )

            grounding_sources = []

            for chunk in response_stream:
                # Yield text chunks as they arrive
                if chunk.text:
                    yield {
                        "type": "content",
                        "text": chunk.text,
                    }

                # Extract grounding metadata from the final chunk
                if hasattr(chunk, "candidates") and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, "grounding_metadata"):
                        metadata = candidate.grounding_metadata
                        if hasattr(metadata, "grounding_chunks"):
                            for grounding_chunk in metadata.grounding_chunks:
                                source = {
                                    "source": getattr(grounding_chunk, "source", "unknown"),
                                    "content": getattr(grounding_chunk, "text", ""),
                                }
                                if source not in grounding_sources:
                                    grounding_sources.append(source)

            # Yield sources at the end
            if grounding_sources:
                yield {
                    "type": "sources",
                    "sources": grounding_sources,
                }

            # Signal completion
            yield {"type": "done"}

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
            }

    def search_and_answer(
        self,
        store_name: str,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Search documents and generate an answer.

        Uses Gemini File Search API to search documents in the store
        and generate a grounded response.

        Args:
            store_name: The store name/ID to search in
            query: The user's question
            conversation_history: Optional list of previous messages for context
            model: The model to use for generation

        Returns:
            Response with answer and grounding sources
        """
        try:
            # Build contents with conversation history for multi-turn
            contents = self._build_conversation_contents(query, conversation_history)

            response = self._client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ]
                ),
            )

            # Extract grounding sources from response
            sources = []
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, "grounding_chunks"):
                        for chunk in metadata.grounding_chunks:
                            sources.append({
                                "source": getattr(chunk, "source", "unknown"),
                                "content": getattr(chunk, "text", ""),
                            })

            return {
                "response": response.text if response.text else "",
                "sources": sources,
            }

        except Exception as e:
            return {
                "response": "",
                "error": str(e),
                "sources": [],
            }

    # ========== Multi-Store Search Operations ==========

    def multi_store_search(
        self,
        store_names: list[str],
        query: str,
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Search across multiple File Search Stores and generate an answer.

        Uses Gemini File Search API to search documents across multiple stores
        simultaneously and generate a grounded response.

        Args:
            store_names: List of store names/IDs to search (max 5)
            query: The user's question
            model: The model to use for generation

        Returns:
            Response with answer and grounding sources including store info
        """
        if len(store_names) > 5:
            return {
                "response": "",
                "error": "Maximum 5 stores can be searched at once",
                "sources": [],
            }

        if not store_names:
            return {
                "response": "",
                "error": "At least one store must be specified",
                "sources": [],
            }

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=store_names
                            )
                        )
                    ]
                ),
            )

            # Extract grounding sources from response
            sources = []
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, "grounding_chunks"):
                        for chunk in metadata.grounding_chunks:
                            source_info = {
                                "source": getattr(chunk, "source", "unknown"),
                                "content": getattr(chunk, "text", ""),
                            }
                            # Try to extract store name from source
                            if hasattr(chunk, "file_search_store"):
                                source_info["store_name"] = chunk.file_search_store
                            sources.append(source_info)

            return {
                "response": response.text if response.text else "",
                "sources": sources,
            }

        except Exception as e:
            return {
                "response": "",
                "error": str(e),
                "sources": [],
            }

    def multi_store_search_stream(
        self,
        store_names: list[str],
        query: str,
        model: str = "gemini-2.5-flash",
    ):
        """Search across multiple File Search Stores with streaming response.

        Uses Gemini File Search API to search documents across multiple stores
        simultaneously and generate a grounded streaming response.

        Args:
            store_names: List of store names/IDs to search (max 5)
            query: The user's question
            model: The model to use for generation

        Yields:
            Chunks of the response as they are generated
        """
        if len(store_names) > 5:
            yield {
                "type": "error",
                "error": "Maximum 5 stores can be searched at once",
            }
            return

        if not store_names:
            yield {
                "type": "error",
                "error": "At least one store must be specified",
            }
            return

        try:
            response_stream = self._client.models.generate_content_stream(
                model=model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=store_names
                            )
                        )
                    ]
                ),
            )

            grounding_sources = []

            for chunk in response_stream:
                # Yield text chunks as they arrive
                if chunk.text:
                    yield {
                        "type": "content",
                        "text": chunk.text,
                    }

                # Extract grounding metadata from the final chunk
                if hasattr(chunk, "candidates") and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, "grounding_metadata"):
                        metadata = candidate.grounding_metadata
                        if hasattr(metadata, "grounding_chunks"):
                            for grounding_chunk in metadata.grounding_chunks:
                                source = {
                                    "source": getattr(grounding_chunk, "source", "unknown"),
                                    "content": getattr(grounding_chunk, "text", ""),
                                }
                                if hasattr(grounding_chunk, "file_search_store"):
                                    source["store_name"] = grounding_chunk.file_search_store
                                if source not in grounding_sources:
                                    grounding_sources.append(source)

            # Yield sources at the end
            if grounding_sources:
                yield {
                    "type": "sources",
                    "sources": grounding_sources,
                }

            # Signal completion
            yield {"type": "done"}

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
            }

    # ========== FAQ Operations ==========

    def generate_faq(
        self,
        store_name: str,
        count: int = 5,
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Generate FAQ items based on documents in the store.

        Analyzes documents in the File Search Store and generates
        frequently asked questions with answers.

        Args:
            store_name: The store name/ID to analyze
            count: Number of FAQ items to generate (1-20)
            model: The model to use for generation

        Returns:
            Dict with 'items' list containing question/answer pairs
        """
        prompt = f"""Based on the documents in this knowledge base, generate exactly {count} frequently asked questions (FAQ) that users might ask about the content.

For each question:
1. Create a clear, specific question that someone might naturally ask
2. Provide a comprehensive answer based on the document content

Format your response as a JSON array with objects containing "question" and "answer" fields.
Example format:
[
  {{"question": "What is X?", "answer": "X is..."}},
  {{"question": "How does Y work?", "answer": "Y works by..."}}
]

Generate exactly {count} FAQ items. Return ONLY the JSON array, no other text."""

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ],
                    response_mime_type="application/json",
                ),
            )

            # Parse the JSON response
            import json
            try:
                items = json.loads(response.text) if response.text else []
            except json.JSONDecodeError:
                # Try to extract JSON from response if it contains extra text
                text = response.text or ""
                start = text.find("[")
                end = text.rfind("]") + 1
                if start != -1 and end > start:
                    items = json.loads(text[start:end])
                else:
                    items = []

            return {
                "items": items,
            }

        except Exception as e:
            return {
                "items": [],
                "error": str(e),
            }

    # ========== Citation Operations ==========

    def _extract_detailed_sources(
        self,
        grounding_metadata: Any,
    ) -> list[dict[str, Any]]:
        """Extract detailed source information from grounding metadata.

        Args:
            grounding_metadata: Grounding metadata from Gemini response

        Returns:
            List of detailed source information with location data
        """
        sources = []

        if not hasattr(grounding_metadata, "grounding_chunks"):
            return sources

        for idx, chunk in enumerate(grounding_metadata.grounding_chunks, start=1):
            source_info = {
                "index": idx,
                "source": getattr(chunk, "source", "unknown"),
                "content": getattr(chunk, "text", ""),
                "page": None,
                "start_index": None,
                "end_index": None,
            }

            # Try to extract additional location info if available
            if hasattr(chunk, "page"):
                source_info["page"] = chunk.page
            if hasattr(chunk, "start_index"):
                source_info["start_index"] = chunk.start_index
            if hasattr(chunk, "end_index"):
                source_info["end_index"] = chunk.end_index

            # Extract from retrieved_context if available
            if hasattr(chunk, "retrieved_context"):
                ctx = chunk.retrieved_context
                if hasattr(ctx, "uri"):
                    source_info["source"] = ctx.uri
                if hasattr(ctx, "title"):
                    source_info["title"] = ctx.title

            sources.append(source_info)

        return sources

    def _insert_inline_citations(
        self,
        response_text: str,
        sources: list[dict[str, Any]],
    ) -> str:
        """Insert inline citation markers into response text.

        Attempts to find where each source's content appears in the response
        and insert citation markers like [1], [2], etc.

        Args:
            response_text: The original response text
            sources: List of source information with content

        Returns:
            Response text with inline citation markers
        """
        if not sources:
            return response_text

        cited_text = response_text
        citations_added = set()

        # For each source, try to find relevant parts in the response
        for source in sources:
            idx = source.get("index", 0)
            content = source.get("content", "")

            if not content or idx in citations_added:
                continue

            # Try to find sentences that might be from this source
            # Simple approach: look for key phrases from the content
            words = content.split()
            if len(words) >= 3:
                # Try to find a 3-5 word phrase from the source
                phrase_len = min(5, len(words))
                search_phrase = " ".join(words[:phrase_len]).lower()

                # Look for this phrase in the response
                response_lower = cited_text.lower()
                pos = response_lower.find(search_phrase)

                if pos != -1:
                    # Find the end of the sentence
                    sentence_end = pos
                    for end_char in [".", "!", "?", "\n"]:
                        end_pos = cited_text.find(end_char, pos)
                        if end_pos != -1:
                            sentence_end = max(sentence_end, end_pos)
                            break
                    else:
                        sentence_end = min(pos + len(search_phrase) + 50, len(cited_text))

                    # Insert citation at sentence end
                    citation_marker = f" [{idx}]"
                    if citation_marker not in cited_text[pos:sentence_end + 10]:
                        cited_text = (
                            cited_text[:sentence_end + 1]
                            + citation_marker
                            + cited_text[sentence_end + 1:]
                        )
                        citations_added.add(idx)

        # If no citations were added naturally, append them at the end of paragraphs
        if not citations_added and sources:
            # Just add all citation numbers at the end
            all_citations = " ".join([f"[{s.get('index', i+1)}]" for i, s in enumerate(sources)])
            cited_text = cited_text.rstrip() + " " + all_citations

        return cited_text

    def search_with_citations(
        self,
        store_name: str,
        query: str,
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Search documents and generate an answer with inline citations.

        Args:
            store_name: The store name/ID to search in
            query: The user's question
            model: The model to use for generation

        Returns:
            Response with answer, inline citations, and detailed source info
        """
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ]
                ),
            )

            response_text = response.text if response.text else ""
            sources = []

            # Extract detailed source information
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    sources = self._extract_detailed_sources(
                        candidate.grounding_metadata
                    )

            # Create response with inline citations
            cited_response = self._insert_inline_citations(response_text, sources)

            return {
                "response": cited_response,
                "response_plain": response_text,
                "citations": sources,
            }

        except Exception as e:
            return {
                "response": "",
                "response_plain": "",
                "citations": [],
                "error": str(e),
            }

    def search_with_citations_stream(
        self,
        store_name: str,
        query: str,
        model: str = "gemini-2.5-flash",
    ):
        """Search documents with streaming and inline citations.

        Args:
            store_name: The store name/ID to search in
            query: The user's question
            model: The model to use for generation

        Yields:
            Chunks of the response, then citations at the end
        """
        try:
            response_stream = self._client.models.generate_content_stream(
                model=model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ]
                ),
            )

            full_response = ""
            sources = []

            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    yield {
                        "type": "content",
                        "text": chunk.text,
                    }

                # Extract grounding metadata from chunks
                if hasattr(chunk, "candidates") and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, "grounding_metadata"):
                        new_sources = self._extract_detailed_sources(
                            candidate.grounding_metadata
                        )
                        for src in new_sources:
                            if src not in sources:
                                sources.append(src)

            # Yield citations with full context
            if sources:
                cited_response = self._insert_inline_citations(full_response, sources)
                yield {
                    "type": "citations",
                    "response_with_citations": cited_response,
                    "citations": sources,
                }

            yield {"type": "done"}

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
            }

    # ========== Summarization Operations ==========

    def summarize_channel(
        self,
        store_name: str,
        summary_type: str = "short",
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Summarize all documents in a channel.

        Args:
            store_name: The store name/ID to summarize
            summary_type: 'short' (2-3 sentences) or 'detailed' (comprehensive)
            model: The model to use for generation

        Returns:
            Dict with 'summary' text
        """
        if summary_type == "detailed":
            prompt = """Provide a comprehensive summary of all the documents in this knowledge base.

Structure your summary as follows:
1. **Overview**: A brief introduction to what the documents cover
2. **Key Topics**: Main subjects and themes discussed
3. **Important Points**: Significant findings, facts, or conclusions
4. **Additional Details**: Any other notable information

Be thorough but concise. Use the document content to provide accurate information."""
        else:
            prompt = """Summarize all the documents in this knowledge base in 2-3 concise sentences.
Focus on the main topic and the most important points. Be clear and informative."""

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ]
                ),
            )

            return {
                "summary": response.text if response.text else "",
            }

        except Exception as e:
            return {
                "summary": "",
                "error": str(e),
            }

    def summarize_document(
        self,
        store_name: str,
        document_name: str,
        summary_type: str = "short",
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Summarize a specific document in a channel.

        Args:
            store_name: The store name/ID containing the document
            document_name: The document file name to summarize
            summary_type: 'short' (2-3 sentences) or 'detailed' (comprehensive)
            model: The model to use for generation

        Returns:
            Dict with 'summary' text
        """
        if summary_type == "detailed":
            prompt = f"""Provide a comprehensive summary of the document named "{document_name}".

Structure your summary as follows:
1. **Overview**: What the document is about
2. **Key Points**: Main topics and important information
3. **Details**: Significant findings or conclusions
4. **Summary**: Brief closing statement

Focus only on the content from this specific document."""
        else:
            prompt = f"""Summarize the document named "{document_name}" in 2-3 concise sentences.
Focus on the main topic and the most important points from this specific document."""

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ]
                ),
            )

            return {
                "summary": response.text if response.text else "",
            }

        except Exception as e:
            return {
                "summary": "",
                "error": str(e),
            }


    # ========== Timeline Operations ==========

    def generate_timeline(
        self,
        store_name: str,
        max_events: int = 20,
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Generate a timeline of events from documents in the store.

        Analyzes documents to extract date-based events and organizes
        them chronologically.

        Args:
            store_name: The store name/ID to analyze
            max_events: Maximum number of events to extract (1-50)
            model: The model to use for generation

        Returns:
            Dict with 'events' list containing timeline entries
        """
        prompt = f"""Analyze all documents in this knowledge base and extract a chronological timeline of events, dates, and milestones.

For each event:
1. Identify the date or time period (be as specific as possible)
2. Create a clear, descriptive title
3. Provide a detailed description of what happened
4. Note the source document if identifiable

Format your response as a JSON array with objects containing these fields:
- "date": The date or time period (string, e.g., "2024-01-15", "January 2024", "Q1 2024")
- "title": A short descriptive title (string)
- "description": Detailed description of the event (string)
- "source": Source document name if known (string or null)

Sort events chronologically from earliest to latest.
Extract up to {max_events} events.

Return ONLY the JSON array, no other text.

Example format:
[
  {{"date": "2024-01-15", "title": "Project Launch", "description": "The project was officially launched...", "source": "launch_report.pdf"}},
  {{"date": "2024-02-01", "title": "First Milestone", "description": "Completed the first phase...", "source": null}}
]"""

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ],
                    response_mime_type="application/json",
                ),
            )

            # Parse the JSON response
            import json
            try:
                events = json.loads(response.text) if response.text else []
            except json.JSONDecodeError:
                # Try to extract JSON from response if it contains extra text
                text = response.text or ""
                start = text.find("[")
                end = text.rfind("]") + 1
                if start != -1 and end > start:
                    events = json.loads(text[start:end])
                else:
                    events = []

            return {
                "events": events,
            }

        except Exception as e:
            return {
                "events": [],
                "error": str(e),
            }

    # ========== Briefing Operations ==========

    def generate_briefing(
        self,
        store_name: str,
        style: str = "executive",
        max_sections: int = 5,
        model: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Generate a briefing document from the content in the store.

        Creates a structured briefing summarizing all documents.

        Args:
            store_name: The store name/ID to analyze
            style: 'executive' (concise) or 'detailed' (comprehensive)
            max_sections: Maximum number of sections (1-10)
            model: The model to use for generation

        Returns:
            Dict with briefing structure including title, summary, sections, key_points
        """
        if style == "detailed":
            style_instruction = """Create a comprehensive, detailed briefing document.
Include thorough analysis, supporting details, and context for each section.
Sections should be substantial with multiple paragraphs where appropriate."""
        else:
            style_instruction = """Create a concise executive briefing.
Focus on the most critical information. Keep sections brief and actionable.
Prioritize clarity and quick comprehension over exhaustive detail."""

        prompt = f"""Analyze all documents in this knowledge base and create a professional briefing document.

{style_instruction}

Structure your response as a JSON object with these fields:
- "title": A descriptive title for the briefing (string)
- "executive_summary": A brief overview of the entire content (1-2 paragraphs)
- "sections": An array of up to {max_sections} sections, each with:
  - "title": Section title (string)
  - "content": Section content (string, can be multiple paragraphs)
- "key_points": An array of 3-7 key takeaways or action items (strings)

Return ONLY the JSON object, no other text.

Example format:
{{
  "title": "Q1 2024 Project Status Briefing",
  "executive_summary": "This briefing summarizes...",
  "sections": [
    {{"title": "Current Status", "content": "The project is currently..."}},
    {{"title": "Key Achievements", "content": "Major milestones achieved..."}}
  ],
  "key_points": [
    "Project is on track for Q2 delivery",
    "Budget utilization at 75%",
    "Three major risks identified"
  ]
}}"""

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store_name]
                            )
                        )
                    ],
                    response_mime_type="application/json",
                ),
            )

            # Parse the JSON response
            import json
            try:
                briefing = json.loads(response.text) if response.text else {}
            except json.JSONDecodeError:
                # Try to extract JSON from response if it contains extra text
                text = response.text or ""
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    briefing = json.loads(text[start:end])
                else:
                    briefing = {}

            return {
                "title": briefing.get("title", "Briefing"),
                "executive_summary": briefing.get("executive_summary", ""),
                "sections": briefing.get("sections", []),
                "key_points": briefing.get("key_points", []),
            }

        except Exception as e:
            return {
                "title": "",
                "executive_summary": "",
                "sections": [],
                "key_points": [],
                "error": str(e),
            }


@lru_cache
def get_gemini_service() -> GeminiService:
    """Get cached GeminiService instance."""
    return GeminiService()
