from __future__ import annotations
import re
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .base_tool import BaseTool, ToolResult

_BINGSEARCH = 'https://www.bing.com/search?{query}&count={num_results}'

class WebSearch(BaseTool):
    name = 'web_search'
    description = 'Search the web for up-to-date information using Bing. Requires allow_network=true in config.json.'

    def __init__(self, *, allow_network: bool = False, timeout: int = 20) -> None:
        self.allow_network = allow_network
        self.timeout = timeout

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.allow_network:
            raise ValueError('network access is disabled; set allow_network=true in config.json to use web search')
        query = self.string(arguments, 'query')
        num_results = arguments.get('num_results', 5)
        if not isinstance(num_results, int) or not 1 <= num_results <= 10:
            raise ValueError('num_results must be between 1 and 10')
        return {'query': query, 'num_results': num_results}

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        query = arguments['query']
        num_results = arguments['num_results']
        try:
            url = _BINGSEARCH.format(query=urlencode({'q': query}), num_results=num_results)
            req = Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
            html = raw.decode('utf-8', errors='replace')

            results = []
            for block in re.finditer(r'<li class="b_algo" data-id[^>]*>(.*?)</li>', html, re.S):
                snippet_html = block.group(1)
                title_match = re.search(r'<div class="tptt">(.*?)</div>', snippet_html, re.S)
                url_match = re.search(r'<cite>(.*?)</cite>', snippet_html, re.S)
                title = re.sub(r'<.*?>', '', title_match.group(1)).strip() if title_match else ''
                raw_url = url_match.group(1).strip() if url_match else ''
                raw_url = re.sub(r'<.*?>', '', raw_url)
                raw_url = raw_url.replace('<strong>', '').replace('</strong>', '')
                if raw_url.startswith('https://'):
                    url_text = raw_url
                elif raw_url.startswith('//'):
                    url_text = 'https://' + raw_url[2:]
                else:
                    url_text = 'https://' + raw_url
                text = re.sub(r'<.*?>', '', snippet_html)
                text = re.sub(r'\s+', ' ', text).strip()
                text = re.sub(r'^.*?' + re.escape(title), '', text, flags=re.S).strip()
                text = re.sub(r'^.*?' + re.escape(url_text), '', text, flags=re.S).strip()
                text = text[:300]
                if title and url_text:
                    results.append({'title': title, 'url': url_text, 'snippet': text})

            results = results[:num_results]
            if not results:
                return ToolResult(True, f'No web results for: {query}')
            lines = []
            for index, item in enumerate(results, 1):
                lines.append(f"{index}. {item['title']}\n   {item['url']}\n   {item['snippet']}")
            return ToolResult(True, '\n\n'.join(lines))
        except (URLError, OSError, ValueError) as exc:
            return ToolResult(False, '', f'web search failed: {type(exc).__name__}: {exc}')
