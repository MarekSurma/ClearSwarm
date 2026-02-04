"""
Web Search Tool using Tavily API.
Performs web searches and returns structured results.
"""
import os
import requests
from typing import Optional, List
from multi_agent.tools.base import BaseTool


class WebSearchTavilyTool(BaseTool):
    """Performs web searches using the Tavily Search API."""

    API_ENDPOINT = "https://api.tavily.com/search"

    @property
    def name(self) -> str:
        return "web_search_tavily_tool"

    @property
    def description(self) -> str:
        return """Performs web search using Tavily API and returns structured results.

Parameters:
- query (str, required): The search query to execute
- search_depth (str, optional): Search depth - 'basic' (default), 'advanced', 'fast', or 'ultra-fast'
- max_results (int, optional): Maximum number of results to return (1-20, default: 5)
- topic (str, optional): Topic category - 'general' (default), 'news', or 'finance'
- time_range (str, optional): Time filter - 'day', 'week', 'month', 'year', or None (default)
- include_answer (bool, optional): Include AI-generated answer summary (default: False)
- include_domains (list, optional): List of domains to include in search
- exclude_domains (list, optional): List of domains to exclude from search

Returns search results with titles, URLs, and content snippets."""

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute"
                },
                "search_depth": {
                    "type": "string",
                    "description": "Search depth: 'basic', 'advanced', 'fast', 'ultra-fast'",
                    "enum": ["basic", "advanced", "fast", "ultra-fast"],
                    "default": "basic"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (1-20)",
                    "default": 5
                },
                "topic": {
                    "type": "string",
                    "description": "Topic category: 'general', 'news', 'finance'",
                    "enum": ["general", "news", "finance"],
                    "default": "general"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time filter: 'day', 'week', 'month', 'year'",
                    "enum": ["day", "week", "month", "year"]
                },
                "include_answer": {
                    "type": "boolean",
                    "description": "Include AI-generated answer summary",
                    "default": False
                },
                "include_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of domains to include in search"
                },
                "exclude_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of domains to exclude from search"
                }
            },
            "required": ["query"]
        }

    def execute(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        topic: str = "general",
        time_range: Optional[str] = None,
        include_answer: bool = False,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Execute web search using Tavily API.

        Args:
            query: The search query
            search_depth: Search depth level
            max_results: Maximum results to return
            topic: Topic category
            time_range: Time filter
            include_answer: Whether to include AI answer
            include_domains: Domains to include
            exclude_domains: Domains to exclude
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted search results as string
        """
        if not query:
            return "Error: query parameter is required"

        # Get API key from environment
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY environment variable is not set. Please add it to your .env file."

        # Build request payload
        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": min(max(1, max_results), 20),  # Clamp to 1-20
            "topic": topic,
            "include_answer": include_answer
        }

        if time_range:
            payload["time_range"] = time_range

        if include_domains:
            payload["include_domains"] = include_domains

        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        # Set up headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.API_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 401:
                return "Error: Invalid Tavily API key. Please check your TAVILY_API_KEY."

            if response.status_code == 429:
                return "Error: Rate limit exceeded. Please wait before making more requests."

            response.raise_for_status()

            data = response.json()
            return self._format_results(data, query)

        except requests.exceptions.Timeout:
            return "Error: Request timed out while searching. Please try again."

        except requests.exceptions.RequestException as e:
            return f"Error: Failed to perform search: {str(e)}"

        except Exception as e:
            return f"Error: Unexpected error during search: {str(e)}"

    def _format_results(self, data: dict, query: str) -> str:
        """Format API response into readable string."""
        output = []
        output.append(f"Search Results for: {query}")
        output.append("=" * 60)

        # Include AI answer if present
        if data.get("answer"):
            output.append("\n📝 AI Answer:")
            output.append(data["answer"])
            output.append("")

        # Format search results
        results = data.get("results", [])
        if not results:
            output.append("\nNo results found.")
            return "\n".join(output)

        output.append(f"\n📊 Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            content = result.get("content", "No content available")

            # Truncate content if too long
            if len(content) > 500:
                content = content[:500] + "..."

            output.append(f"[{i}] {title}")
            output.append(f"    URL: {url}")
            output.append(f"    {content}")
            output.append("")

        # Add response metadata
        if data.get("response_time"):
            output.append(f"⏱️ Response time: {data['response_time']:.2f}s")

        return "\n".join(output)


# Export the tool
def get_tool():
    """Return an instance of the WebSearchTavily tool."""
    return WebSearchTavilyTool()
