"""
Web Fetcher Tool - Fetches web page content using Lynx browser.
"""
import subprocess
from typing import Optional
from multi_agent.tools.base import BaseTool


class WebFetcher(BaseTool):
    """Fetches web page content using the Lynx text browser."""

    @property
    def name(self) -> str:
        return "web_fetcher"

    @property
    def description(self) -> str:
        return """Fetches web page content from a given URL using Lynx text browser.

Parameters:
- url (str, required): The URL of the web page to fetch
- dump_format (str, optional): Output format - 'text' for plain text (default) or 'source' for HTML source
- timeout (int, optional): Timeout in seconds (default: 30)

Returns the text content of the web page or an error message if the fetch fails."""

    def execute(self, url: str, dump_format: str = "text", timeout: int = 30, **kwargs) -> str:
        """
        Fetch web page content using Lynx.

        Args:
            url: URL of the web page to fetch
            dump_format: 'text' for plain text or 'source' for HTML source
            timeout: Timeout in seconds
            **kwargs: Additional arguments (ignored)

        Returns:
            Web page content as string
        """
        if not url:
            return "Error: URL parameter is required"

        # Validate URL format (basic check)
        if not url.startswith(('http://', 'https://')):
            return f"Error: Invalid URL format. URL must start with http:// or https://. Got: {url}"

        try:
            # Build lynx command
            if dump_format == "source":
                # Dump HTML source
                cmd = ['lynx', '-source', url]
            else:
                # Dump as plain text (default)
                cmd = ['lynx', '-dump', '-nolist', url]

            # Execute lynx with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )

            if result.stdout:
                content = result.stdout
                # Add summary info
                lines = content.split('\n')
                summary = f"Successfully fetched content from: {url}\n"
                summary += f"Content length: {len(content)} characters, {len(lines)} lines\n"
                summary += f"Format: {dump_format}\n"
                summary += "=" * 80 + "\n\n"
                return summary + content
            else:
                return f"Error: No content received from {url}"

        except subprocess.TimeoutExpired:
            return f"Error: Request timed out after {timeout} seconds while fetching {url}"

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            return f"Error fetching {url}: {error_msg}"

        except Exception as e:
            return f"Error: Unexpected error while fetching {url}: {str(e)}"


# Export the tool
def get_tool():
    """Return an instance of the WebFetcher tool."""
    return WebFetcher()
