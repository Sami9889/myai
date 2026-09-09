from __future__ import annotations
import re
from html.parser import HTMLParser
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from .base_tool import BaseTool, ToolResult

class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = False
        self._parts: list[str] = []
        self._skip_tags = {'script', 'style', 'nav', 'header', 'footer', 'aside'}

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_text(self) -> str:
        return '\n'.join(self._parts)

class WebReader(BaseTool):
    name = 'web_read'
    description = 'Fetch a webpage and return its readable text content. Requires allow_network=true in config.json.'

    def __init__(self, *, allow_network: bool = False, timeout: int = 15) -> None:
        self.allow_network = allow_network
        self.timeout = timeout

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.allow_network:
            raise ValueError('network access is disabled; set allow_network=true in config.json to use web read')
        url = self.string(arguments, 'url')
        if not re.match(r'^https?://', url):
            raise ValueError('url must start with http:// or https://')
        max_chars = arguments.get('max_chars', 4000)
        if not isinstance(max_chars, int) or not 100 <= max_chars <= 20000:
            raise ValueError('max_chars must be between 100 and 20000')
        return {'url': url, 'max_chars': max_chars}

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        url = arguments['url']
        max_chars = arguments['max_chars']
        try:
            req = Request(url, headers={'User-Agent': 'myai/0.1 (local agent)'})
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
            charset = response.headers.get_content_charset('utf-8')
            try:
                html = raw.decode(charset, errors='replace')
            except Exception:
                html = raw.decode('utf-8', errors='replace')
            extractor = _TextExtractor()
            extractor.feed(html)
            text = extractor.get_text()
            text = re.sub(r'\n{3,}', '\n\n', text)
            if len(text) > max_chars:
                text = text[:max_chars] + '\n...[truncated]'
            return ToolResult(True, text)
        except (URLError, OSError, ValueError) as exc:
            return ToolResult(False, '', f'failed to fetch {url}: {type(exc).__name__}: {exc}')
