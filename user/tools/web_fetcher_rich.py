"""
Web Fetcher Rich Tool - Fetches web page content using headless browser (Playwright).
Supports JavaScript-rendered pages unlike Lynx-based web_fetcher.
"""
from typing import Optional
from multi_agent.tools.base import BaseTool


class WebFetcherRich(BaseTool):
    """Fetches web page content using Playwright headless browser with JavaScript support."""

    def __init__(self):
        self._playwright = None
        self._browser = None

    @property
    def name(self) -> str:
        return "web_fetcher_rich"

    @property
    def description(self) -> str:
        return """Fetches web page content from a given URL using a headless browser (Chromium via Playwright).
Unlike web_fetcher, this tool fully supports JavaScript-rendered pages and dynamic content.

Parameters:
- url (str, required): The URL of the web page to fetch
- output_format (str, optional): Output format:
  - 'text' - plain text content (default)
  - 'html' - full HTML source after JavaScript execution
  - 'links' - extract all links from the page
  - 'markdown' - text with inline links in markdown format [text](url)
- wait_for (str, optional): CSS selector to wait for before extracting content (useful for dynamic pages)
- timeout (int, optional): Timeout in milliseconds (default: 30000)
- scroll (bool, optional): Whether to scroll the page to load lazy content (default: False)

Returns the content of the web page or an error message if the fetch fails.
Note: First run may take longer as it downloads the browser."""

    def _ensure_playwright_installed(self) -> tuple[bool, str]:
        """Ensure playwright is installed and browser is available."""
        try:
            from playwright.sync_api import sync_playwright
            return True, ""
        except ImportError:
            return False, "Playwright not installed. Run: pip install playwright && playwright install chromium"

    def execute(
        self,
        url: str,
        output_format: str = "text",
        wait_for: Optional[str] = None,
        timeout: int = 30000,
        scroll: bool = False,
        **kwargs
    ) -> str:
        """
        Fetch web page content using Playwright headless browser.

        Args:
            url: URL of the web page to fetch
            output_format: 'text', 'html', or 'links'
            wait_for: CSS selector to wait for before extracting
            timeout: Timeout in milliseconds
            scroll: Whether to scroll page to load lazy content
            **kwargs: Additional arguments (ignored)

        Returns:
            Web page content as string
        """
        if not url:
            return "Error: URL parameter is required"

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return f"Error: Invalid URL format. URL must start with http:// or https://. Got: {url}"

        # Check playwright installation
        installed, error_msg = self._ensure_playwright_installed()
        if not installed:
            return f"Error: {error_msg}"

        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

        try:
            with sync_playwright() as p:
                # Launch headless Chromium
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_timeout(timeout)

                # Navigate to URL
                response = page.goto(url, wait_until="networkidle")

                if not response:
                    browser.close()
                    return f"Error: Failed to load {url}"

                # Wait for specific element if requested
                if wait_for:
                    try:
                        page.wait_for_selector(wait_for, timeout=timeout)
                    except PlaywrightTimeout:
                        pass  # Continue even if selector not found

                # Scroll to load lazy content if requested
                if scroll:
                    self._scroll_page(page)

                # Extract content based on format
                if output_format == "html":
                    content = page.content()
                    result = self._format_output(url, content, "html", response.status)
                elif output_format == "links":
                    links = self._extract_links(page)
                    content = "\n".join(links)
                    result = self._format_output(url, content, "links", response.status, extra=f"Found {len(links)} links")
                elif output_format == "markdown":
                    content = self._extract_markdown_with_links(page)
                    result = self._format_output(url, content, "markdown", response.status)
                else:  # text
                    content = page.inner_text("body")
                    result = self._format_output(url, content, "text", response.status)

                browser.close()
                return result

        except PlaywrightTimeout:
            return f"Error: Request timed out after {timeout}ms while fetching {url}"
        except Exception as e:
            error_type = type(e).__name__
            return f"Error ({error_type}): {str(e)}"

    def _scroll_page(self, page) -> None:
        """Scroll the page to trigger lazy loading."""
        try:
            # Get page height and scroll incrementally
            page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 500;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            # Wait a bit for content to load after scrolling
            page.wait_for_timeout(1000)
        except Exception:
            pass  # Ignore scroll errors

    def _extract_markdown_with_links(self, page) -> str:
        """Extract text content with inline markdown links."""
        content = page.evaluate("""
            () => {
                function extractWithLinks(node) {
                    let result = '';

                    for (const child of node.childNodes) {
                        if (child.nodeType === Node.TEXT_NODE) {
                            result += child.textContent;
                        } else if (child.nodeType === Node.ELEMENT_NODE) {
                            const tag = child.tagName.toLowerCase();

                            // Skip hidden elements, scripts, styles
                            if (tag === 'script' || tag === 'style' || tag === 'noscript') {
                                continue;
                            }

                            const style = window.getComputedStyle(child);
                            if (style.display === 'none' || style.visibility === 'hidden') {
                                continue;
                            }

                            if (tag === 'a') {
                                const href = child.getAttribute('href');
                                const text = child.innerText.trim();
                                if (href && text && !href.startsWith('javascript:') && !href.startsWith('#')) {
                                    result += '[' + text.replace(/[\\[\\]]/g, '') + '](' + href + ')';
                                } else if (text) {
                                    result += text;
                                }
                            } else if (tag === 'br') {
                                result += '\\n';
                            } else if (tag === 'p' || tag === 'div' || tag === 'section' || tag === 'article') {
                                const inner = extractWithLinks(child);
                                if (inner.trim()) {
                                    result += '\\n' + inner + '\\n';
                                }
                            } else if (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4' || tag === 'h5' || tag === 'h6') {
                                const level = parseInt(tag[1]);
                                const inner = extractWithLinks(child);
                                if (inner.trim()) {
                                    result += '\\n' + '#'.repeat(level) + ' ' + inner.trim() + '\\n';
                                }
                            } else if (tag === 'li') {
                                const inner = extractWithLinks(child);
                                if (inner.trim()) {
                                    result += '\\n- ' + inner.trim();
                                }
                            } else if (tag === 'ul' || tag === 'ol') {
                                result += extractWithLinks(child) + '\\n';
                            } else {
                                result += extractWithLinks(child);
                            }
                        }
                    }
                    return result;
                }

                const body = document.body;
                let text = extractWithLinks(body);

                // Clean up excessive whitespace
                text = text.replace(/\\n{3,}/g, '\\n\\n');
                text = text.replace(/^\\s+|\\s+$/g, '');

                return text;
            }
        """)
        return content

    def _extract_links(self, page) -> list[str]:
        """Extract all links from the page."""
        links = page.evaluate("""
            () => {
                const anchors = document.querySelectorAll('a[href]');
                return Array.from(anchors).map(a => ({
                    href: a.href,
                    text: a.innerText.trim().substring(0, 100)
                }));
            }
        """)

        result = []
        seen = set()
        for link in links:
            href = link.get('href', '')
            text = link.get('text', '').replace('\n', ' ').strip()

            # Skip empty, javascript, and mailto links
            if not href or href.startswith(('javascript:', 'mailto:', '#')):
                continue

            # Deduplicate
            if href in seen:
                continue
            seen.add(href)

            # Format: [text] URL
            if text:
                result.append(f"[{text[:80]}] {href}")
            else:
                result.append(href)

        return result

    def _format_output(
        self,
        url: str,
        content: str,
        format_type: str,
        status_code: int,
        extra: str = ""
    ) -> str:
        """Format the output with summary info."""
        lines = content.split('\n')
        summary = f"Successfully fetched content from: {url}\n"
        summary += f"HTTP Status: {status_code}\n"
        summary += f"Content length: {len(content)} characters, {len(lines)} lines\n"
        summary += f"Format: {format_type} (JavaScript rendered)\n"
        if extra:
            summary += f"{extra}\n"
        summary += "=" * 80 + "\n\n"
        return summary + content


# Export the tool
def get_tool():
    """Return an instance of the WebFetcherRich tool."""
    return WebFetcherRich()
