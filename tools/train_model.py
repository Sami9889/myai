"""Multiple training data sources for the local model."""
from __future__ import annotations
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from core_engine.tokenizer import ByteBPETokenizer
from core_engine.trainer import train_on_text
from tools.web_search import WebSearch
from tools.web_reader import WebReader
from utils.config_loader import load_config

ROOT = Path(__file__).resolve().parent.parent
random.seed(42)

DEFAULT_QUERIES = [
    'Python programming language',
    'artificial intelligence',
    'machine learning',
    'software engineering',
    'data structures algorithms',
    'web development',
    'computer science',
]

def log(msg: str) -> None:
    print(msg, flush=True)

# Source 1: Web search + webpage read
def fetch_web_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    search = WebSearch(allow_network=True, timeout=20)
    reader = WebReader(allow_network=True, timeout=20)
    seen_urls: set[str] = set()
    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [web] searching: {query}')
        try:
            result = search.run({'query': query, 'num_results': 5})
            if not result.ok:
                log(f'  [warn] web search failed: {result.error}')
                continue
            log(f'  [info] web search results received')
            for line in result.output.splitlines():
                if line.startswith('   ') and not line.startswith('   http'):
                    parts.append(line.strip())
                elif line.startswith('http'):
                    url = line.strip()
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    try:
                        log(f'  [web] fetching: {url}')
                        read_result = reader.run({'url': url, 'max_chars': 2000})
                        if read_result.ok and read_result.output:
                            parts.append(read_result.output)
                            fetched += 1
                            log(f'  [info] web fetched {len(read_result.output)} chars')
                            if sum(len(p) for p in parts) >= max_chars:
                                break
                        else:
                            log(f'  [warn] web fetch failed: {read_result.error}')
                    except Exception as exc:
                        log(f'  [warn] web fetch error: {exc}')
                        continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] web search error: {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 2: Wikipedia articles
def fetch_wikipedia_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from html.parser import HTMLParser

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

    seen_titles: set[str] = set()
    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wiki] searching: {query}')
        try:
            search_url = 'https://en.wikipedia.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Wikipedia results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                try:
                    article_url = 'https://en.wikipedia.org/wiki/' + title.replace(' ', '_')
                    log(f'  [wiki] fetching: {title}')
                    req = Request(article_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
                    with urlopen(req, timeout=20) as response:
                        raw = response.read()
                    html = raw.decode('utf-8', errors='replace')
                    extractor = _TextExtractor()
                    extractor.feed(html)
                    text = extractor.get_text()
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    if text:
                        parts.append(text)
                        fetched += 1
                        log(f'  [info] wiki fetched {len(text)} chars')
                    else:
                        log(f'  [warn] wiki article empty: {title}')
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                except Exception as exc:
                    log(f'  [warn] wiki fetch failed: {title} | {exc}')
                    continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wiki search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 3: Stack Exchange / Stack Overflow
def fetch_stackexchange_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [stack] searching: {query}')
        try:
            search_url = 'https://api.stackexchange.com/2.3/search/advanced?' + urlencode({
                'order': 'desc',
                'sort': 'relevance',
                'q': query,
                'site': 'stackoverflow',
                'filter': 'withbody',
                'pagesize': 3,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            items = search_data.get('items', [])
            if not items:
                log(f'  [warn] no Stack Overflow results for: {query}')
                continue
            for item in items:
                title = item.get('title', '')
                body = item.get('body', '')
                body = re.sub(r'<[^>]+>', '', body)
                body = re.sub(r'\s+', ' ', body).strip()
                if title and body:
                    parts.append(f'Q: {title}\nA: {body[:1500]}')
                    fetched += 1
                    log(f'  [info] stack fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] stack search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 4: arXiv papers
def fetch_arxiv_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [arxiv] searching: {query}')
        try:
            search_url = 'https://export.arxiv.org/api/query?' + urlencode({
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': 3,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                raw = response.read().decode('utf-8')
            entries = re.findall(r'<entry>(.*?)</entry>', raw, re.S)
            if not entries:
                log(f'  [warn] no arXiv results for: {query}')
                continue
            for entry in entries:
                title = re.search(r'<title>(.*?)</title>', entry, re.S)
                summary = re.search(r'<summary>(.*?)</summary>', entry, re.S)
                if title and summary:
                    title_text = re.sub(r'\s+', ' ', title.group(1)).strip()
                    summary_text = re.sub(r'\s+', ' ', summary.group(1)).strip()
                    parts.append(f'Paper: {title_text}\nAbstract: {summary_text[:1000]}')
                    fetched += 1
                    log(f'  [info] arxiv fetched: {title_text[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] arxiv search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 5: GitHub repositories
def fetch_github_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [github] searching: {query}')
        try:
            search_url = 'https://api.github.com/search/repositories?' + urlencode({
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': 3,
            })
            req = Request(search_url, headers={
                'User-Agent': 'myai-trainer/0.1 (research)',
                'Accept': 'application/vnd.github.v3+json',
            })
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            repos = search_data.get('items', [])
            if not repos:
                log(f'  [warn] no GitHub repos for: {query}')
                continue
            for repo in repos:
                name = repo.get('full_name', '')
                description = repo.get('description', '') or ''
                readme_url = f'https://raw.githubusercontent.com/{name}/main/README.md'
                if not description and not readme_url:
                    continue
                text = f'Repository: {name}\nDescription: {description}'
                if readme_url:
                    try:
                        reader = WebReader(allow_network=True, timeout=15)
                        readme_result = reader.run({'url': readme_url, 'max_chars': 1500})
                        if readme_result.ok and readme_result.output:
                            text += '\n\nREADME:\n' + readme_result.output[:1500]
                    except Exception:
                        pass
                parts.append(text)
                fetched += 1
                log(f'  [info] github fetched: {name}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] github search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 6: Hacker News
def fetch_hackernews_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [hn] searching: {query}')
        try:
            search_url = f'https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=3'
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            hits = search_data.get('hits', [])
            if not hits:
                log(f'  [warn] no Hacker News results for: {query}')
                continue
            for hit in hits:
                title = hit.get('title', '')
                url = hit.get('url', '')
                text = hit.get('story_text', '') or hit.get('comment_text', '') or ''
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\s+', ' ', text).strip()
                entry = f'Title: {title}\nURL: {url}'
                if text:
                    entry += f'\nContent: {text[:1000]}'
                parts.append(entry)
                fetched += 1
                log(f'  [info] hn fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] hn search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 7: Reddit posts
def fetch_reddit_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [reddit] searching: {query}')
        try:
            search_url = 'https://www.reddit.com/search.json?' + urlencode({
                'q': query,
                'limit': 3,
                'sort': 'relevance',
            })
            req = Request(search_url, headers={
                'User-Agent': 'myai-trainer/0.1 (research)',
            })
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            children = search_data.get('data', {}).get('children', [])
            if not children:
                log(f'  [warn] no Reddit results for: {query}')
                continue
            for child in children:
                post = child.get('data', {})
                title = post.get('title', '')
                selftext = post.get('selftext', '') or ''
                selftext = re.sub(r'<[^>]+>', '', selftext)
                selftext = re.sub(r'\s+', ' ', selftext).strip()
                if title:
                    entry = f'Post: {title}'
                    if selftext:
                        entry += f'\n{selftext[:1500]}'
                    parts.append(entry)
                    fetched += 1
                    log(f'  [info] reddit fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] reddit search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 8: Generic URL fetcher (fallback)
def fetch_url_text(urls: list[str], max_chars: int = 12000) -> tuple[str, int]:
    reader = WebReader(allow_network=True, timeout=20)
    parts: list[str] = []
    fetched = 0

    for url in urls:
        try:
            log(f'  [url] fetching: {url}')
            result = reader.run({'url': url, 'max_chars': 2000})
            if result.ok and result.output:
                parts.append(result.output)
                fetched += 1
                log(f'  [info] url fetched {len(result.output)} chars')
            else:
                log(f'  [warn] url fetch failed: {result.error}')
        except Exception as exc:
            log(f'  [warn] url fetch error: {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched


# Source 9: Wiktionary definitions
def fetch_wiktionary_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wiktionary] searching: {query}')
        try:
            search_url = 'https://en.wiktionary.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Wiktionary results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                if not title:
                    continue
                try:
                    article_url = 'https://en.wiktionary.org/wiki/' + title.replace(' ', '_')
                    log(f'  [wiktionary] fetching: {title}')
                    req = Request(article_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
                    with urlopen(req, timeout=20) as response:
                        raw = response.read()
                    html = raw.decode('utf-8', errors='replace')
                    text = re.sub(r'<[^>]+>', ' ', html)
                    text = re.sub(r'\s+', ' ', text).strip()
                    text = text[:1000]
                    if text:
                        parts.append(f'Definition: {title}\n{text}')
                        fetched += 1
                        log(f'  [info] wiktionary fetched: {title[:60]}')
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                except Exception as exc:
                    log(f'  [warn] wiktionary fetch failed: {title} | {exc}')
                    continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wiktionary search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 10: Wikiquote quotes
def fetch_wikiquote_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wikiquote] searching: {query}')
        try:
            search_url = 'https://en.wikiquote.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Wikiquote results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                if not title:
                    continue
                try:
                    article_url = 'https://en.wikiquote.org/wiki/' + title.replace(' ', '_')
                    log(f'  [wikiquote] fetching: {title}')
                    req = Request(article_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
                    with urlopen(req, timeout=20) as response:
                        raw = response.read()
                    html = raw.decode('utf-8', errors='replace')
                    text = re.sub(r'<[^>]+>', ' ', html)
                    text = re.sub(r'\s+', ' ', text).strip()
                    text = text[:800]
                    if text:
                        parts.append(f'Quote: {title}\n{text}')
                        fetched += 1
                        log(f'  [info] wikiquote fetched: {title[:60]}')
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                except Exception as exc:
                    log(f'  [warn] wikiquote fetch failed: {title} | {exc}')
                    continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wikiquote search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 11: Wikidata facts
def fetch_wikidata_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wikidata] searching: {query}')
        try:
            search_url = 'https://www.wikidata.org/w/api.php?' + urlencode({
                'action': 'wbsearchentities',
                'search': query,
                'language': 'en',
                'format': 'json',
                'limit': 3,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            entities = search_data.get('search', [])
            if not entities:
                log(f'  [warn] no Wikidata results for: {query}')
                continue
            for entity in entities:
                entity_id = entity.get('id', '')
                label = entity.get('label', '')
                description = entity.get('description', '')
                if not entity_id:
                    continue
                try:
                    entity_url = f'https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json'
                    log(f'  [wikidata] fetching: {label}')
                    req = Request(entity_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
                    with urlopen(req, timeout=20) as response:
                        raw = response.read()
                    data = json.loads(raw.decode('utf-8'))
                    entity_data = data.get('entities', {}).get(entity_id, {})
                    claims = entity_data.get('claims', {})
                    facts = []
                    for prop, values in list(claims.items())[:5]:
                        for val in values[:1]:
                            mainsnak = val.get('mainsnak', {})
                            if mainsnak.get('snaktype') == 'value':
                                datavalue = mainsnak.get('datavalue', {})
                                if 'value' in datavalue:
                                    facts.append(f'{prop}: {datavalue["value"]}')
                    text = f'Entity: {label} ({entity_id})\nDescription: {description}\n' + '\n'.join(facts)
                    parts.append(text[:800])
                    fetched += 1
                    log(f'  [info] wikidata fetched: {label[:60]}')
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                except Exception as exc:
                    log(f'  [warn] wikidata fetch failed: {label} | {exc}')
                    continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wikidata search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 12: OpenLibrary books
def fetch_openlibrary_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [openlibrary] searching: {query}')
        try:
            search_url = 'https://openlibrary.org/search.json?' + urlencode({
                'q': query,
                'limit': 3,
                'mode': 'everything',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            docs = search_data.get('docs', [])
            if not docs:
                log(f'  [warn] no OpenLibrary results for: {query}')
                continue
            for doc in docs:
                title = doc.get('title', '')
                author = doc.get('author_name', [''])[0]
                first_publish = doc.get('first_publish_year', '')
                subject = doc.get('subject', [])[:3]
                if not title:
                    continue
                text = f'Book: {title}\nAuthor: {author}\nFirst Published: {first_publish}'
                if subject:
                    text += '\nSubjects: ' + ', '.join(subject)
                parts.append(text)
                fetched += 1
                log(f'  [info] openlibrary fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] openlibrary search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 13: PubMed abstracts
def fetch_pubmed_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [pubmed] searching: {query}')
        try:
            search_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?' + urlencode({
                'db': 'pubmed',
                'term': query,
                'retmax': 3,
                'retmode': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                log(f'  [warn] no PubMed results for: {query}')
                continue
            for pmid in id_list:
                try:
                    fetch_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urlencode({
                        'db': 'pubmed',
                        'id': pmid,
                        'rettype': 'abstract',
                        'retmode': 'text',
                    })
                    req = Request(fetch_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
                    with urlopen(req, timeout=20) as response:
                        abstract = response.read().decode('utf-8', errors='replace').strip()
                    abstract = re.sub(r'\s+', ' ', abstract)
                    if abstract:
                        parts.append(f'PMID: {pmid}\n{abstract[:1000]}')
                        fetched += 1
                        log(f'  [info] pubmed fetched: PMID {pmid}')
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                except Exception as exc:
                    log(f'  [warn] pubmed fetch failed: {pmid} | {exc}')
                    continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] pubmed search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 14: CrossRef DOI metadata
def fetch_crossref_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [crossref] searching: {query}')
        try:
            search_url = 'https://api.crossref.org/works?' + urlencode({
                'query': query,
                'rows': 3,
                'select': 'title,author,published-print,container-title',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            items = search_data.get('message', {}).get('items', [])
            if not items:
                log(f'  [warn] no CrossRef results for: {query}')
                continue
            for item in items:
                title = item.get('title', [''])[0]
                authors = item.get('author', [])
                author_names = ', '.join([a.get('family', '') for a in authors[:3]])
                published = item.get('published-print', {}).get('date-parts', [['']])[0]
                container = item.get('container-title', [''])[0]
                if not title:
                    continue
                text = f'Title: {title}\nAuthors: {author_names}\nJournal: {container}\nYear: {published[0] if published else ""}'
                parts.append(text)
                fetched += 1
                log(f'  [info] crossref fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] crossref search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 15: Europe PMC abstracts
def fetch_europepmc_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [europepmc] searching: {query}')
        try:
            search_url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/SEARCH?' + urlencode({
                'query': query,
                'resultType': 'core',
                'format': 'json',
                'pageSize': 3,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            results = search_data.get('resultList', {}).get('result', [])
            if not results:
                log(f'  [warn] no Europe PMC results for: {query}')
                continue
            for result in results:
                title = result.get('title', '')
                abstract = result.get('abstractText', '')
                if not title:
                    continue
                text = f'Title: {title}\nAbstract: {abstract[:800]}'
                parts.append(text)
                fetched += 1
                log(f'  [info] europepmc fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] europepmc search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 16: OpenStreetMap Nominatim place data
def fetch_nominatim_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [nominatim] searching: {query}')
        try:
            search_url = 'https://nominatim.openstreetmap.org/search?' + urlencode({
                'q': query,
                'format': 'json',
                'limit': 3,
                'addressdetails': 1,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            if not search_data:
                log(f'  [warn] no Nominatim results for: {query}')
                continue
            for place in search_data:
                display_name = place.get('display_name', '')
                place_type = place.get('type', '')
                lat = place.get('lat', '')
                lon = place.get('lon', '')
                if not display_name:
                    continue
                text = f'Place: {display_name}\nType: {place_type}\nCoordinates: {lat}, {lon}'
                parts.append(text)
                fetched += 1
                log(f'  [info] nominatim fetched: {display_name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] nominatim search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 17: REST Countries country data
def fetch_restcountries_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [restcountries] searching: {query}')
        try:
            search_url = f'https://restcountries.com/v3.1/name/{query.replace(" ", "%20")}?limit=3'
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            if not search_data:
                log(f'  [warn] no REST Countries results for: {query}')
                continue
            for country in search_data:
                name = country.get('name', {}).get('common', '')
                capital = country.get('capital', [''])[0]
                region = country.get('region', '')
                population = country.get('population', 0)
                if not name:
                    continue
                text = f'Country: {name}\nCapital: {capital}\nRegion: {region}\nPopulation: {population}'
                parts.append(text)
                fetched += 1
                log(f'  [info] restcountries fetched: {name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] restcountries search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 18: Open Notify astronaut data
def fetch_opennotify_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [opennotify] searching: {query}')
        try:
            req = Request('http://api.open-notify.org/astros.json', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            people = data.get('people', [])
            if not people:
                log(f'  [warn] no Open Notify results')
                continue
            for person in people[:5]:
                name = person.get('name', '')
                craft = person.get('craft', '')
                if name:
                    parts.append(f'Astronaut: {name}\nSpacecraft: {craft}')
                    fetched += 1
                    log(f'  [info] opennotify fetched: {name}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] opennotify failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 19: Sunrise/Sunset API
def fetch_sunrise_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [sunrise] searching: {query}')
        try:
            lat, lng = 40.7128, -74.0060
            if ',' in query:
                parts_coords = query.split(',')
                if len(parts_coords) >= 2:
                    lat = float(parts_coords[0].strip())
                    lng = float(parts_coords[1].strip())
            search_url = 'https://api.sunrise-sunset.org/json?' + urlencode({
                'lat': str(lat),
                'lng': str(lng),
                'date': 'today',
                'formatted': 0,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            results = data.get('results', {})
            if results:
                text = f'Location: {query}\nSunrise: {results.get("sunrise", "")}\nSunset: {results.get("sunset", "")}'
                parts.append(text)
                fetched += 1
                log(f'  [info] sunrise fetched: {query}')
            else:
                log(f'  [warn] no sunrise results for: {query}')
        except Exception as exc:
            log(f'  [warn] sunrise failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 20: Wikipedia random article
def fetch_wikipediarandom_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wikipediarandom] searching: {query}')
        try:
            req = Request('https://en.wikipedia.org/api/rest_v1/page/random/summary', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            title = data.get('title', '')
            extract = data.get('extract', '')
            if title and extract:
                parts.append(f'Article: {title}\n{extract}')
                fetched += 1
                log(f'  [info] wikipediarandom fetched: {title[:60]}')
            else:
                log(f'  [warn] wikipediarandom empty')
        except Exception as exc:
            log(f'  [warn] wikipediarandom failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 21: DuckDuckGo instant answers
def fetch_duckduckgo_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [duckduckgo] searching: {query}')
        try:
            search_url = 'https://api.duckduckgo.com/?' + urlencode({
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            abstract = data.get('AbstractText', '') or data.get('Answer', '') or data.get('Definition', '')
            related = data.get('RelatedTopics', [])[:2]
            text = f'Query: {query}\nAnswer: {abstract}'
            for topic in related:
                if isinstance(topic, dict):
                    text += '\n' + topic.get('Text', '')
            parts.append(text[:800])
            fetched += 1
            log(f'  [info] duckduckgo fetched: {query[:60]}')
        except Exception as exc:
            log(f'  [warn] duckduckgo failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 22: Open Trivia Database
def fetch_opentdb_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [opentdb] searching: {query}')
        try:
            req = Request('https://opentdb.com/api.php?amount=3&type=multiple', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            results = data.get('results', [])
            if not results:
                log(f'  [warn] no Open Trivia results')
                continue
            for result in results:
                question = result.get('question', '')
                correct = result.get('correct_answer', '')
                incorrect = result.get('incorrect_answers', [])
                text = f'Question: {question}\nCorrect: {correct}\nIncorrect: {", ".join(incorrect)}'
                parts.append(text)
                fetched += 1
                log(f'  [info] opentdb fetched: {question[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] opentdb failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 23: JokeAPI
def fetch_jokeapi_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [jokeapi] searching: {query}')
        try:
            req = Request('https://v2.jokeapi.dev/joke/Any?amount=3&safe-mode', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            jokes = data if isinstance(data, list) else [data]
            for joke in jokes[:3]:
                setup = joke.get('setup', '') or joke.get('joke', '')
                delivery = joke.get('delivery', '')
                category = joke.get('category', '')
                text = f'Category: {category}\n{setup}'
                if delivery:
                    text += f'\n{delivery}'
                parts.append(text)
                fetched += 1
                log(f'  [info] jokeapi fetched: {category}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] jokeapi failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 24: Cat Facts API
def fetch_catfacts_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [catfacts] searching: {query}')
        try:
            req = Request('https://catfact.ninja/facts?limit=3', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            facts = data.get('data', [])
            if not facts:
                log(f'  [warn] no Cat Facts results')
                continue
            for fact in facts:
                fact_text = fact.get('fact', '')
                if fact_text:
                    parts.append(fact_text)
                    fetched += 1
                    log(f'  [info] catfacts fetched: {fact_text[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] catfacts failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 25: Dog Facts API
def fetch_dogfacts_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [dogfacts] searching: {query}')
        try:
            req = Request('https://dog-api.kinduff.com/api/facts?number=3', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            facts = data.get('facts', [])
            if not facts:
                log(f'  [warn] no Dog Facts results')
                continue
            for fact in facts:
                if fact:
                    parts.append(fact)
                    fetched += 1
                    log(f'  [info] dogfacts fetched: {fact[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] dogfacts failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 26: Bored API
def fetch_bored_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [bored] searching: {query}')
        try:
            req = Request('https://www.boredapi.com/api/activity', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            activity = data.get('activity', '')
            if activity:
                parts.append(f'Activity: {activity}')
                fetched += 1
                log(f'  [info] bored fetched: {activity[:60]}')
        except Exception as exc:
            log(f'  [warn] bored failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 27: Advice Slip API
def fetch_advice_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [advice] searching: {query}')
        try:
            req = Request('https://api.adviceslip.com/advice', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                raw = response.read().decode('utf-8', errors='replace')
            data = json.loads(raw)
            slip = data.get('slip', {})
            advice_text = slip.get('advice', '')
            if advice_text:
                parts.append(advice_text)
                fetched += 1
                log(f'  [info] advice fetched: {advice_text[:60]}')
        except Exception as exc:
            log(f'  [warn] advice failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 28: Kanye Rest API
def fetch_kanye_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [kanye] searching: {query}')
        try:
            req = Request('https://api.kanye.rest/', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            quote = data.get('quote', '')
            if quote:
                parts.append(f'Quote: {quote}')
                fetched += 1
                log(f'  [info] kanye fetched: {quote[:60]}')
        except Exception as exc:
            log(f'  [warn] kanye failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 29: Random User API
def fetch_randomuser_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [randomuser] searching: {query}')
        try:
            req = Request('https://randomuser.me/api/?results=3', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            results = data.get('results', [])
            if not results:
                log(f'  [warn] no Random User results')
                continue
            for user in results:
                name = f"{user.get('name', {}).get('first', '')} {user.get('name', {}).get('last', '')}"
                gender = user.get('gender', '')
                email = user.get('email', '')
                country = user.get('location', {}).get('country', '')
                text = f'Name: {name}\nGender: {gender}\nEmail: {email}\nCountry: {country}'
                parts.append(text)
                fetched += 1
                log(f'  [info] randomuser fetched: {name}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] randomuser failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 30: Random Data API
def fetch_randomdata_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [randomdata] searching: {query}')
        try:
            req = Request('https://random-data-api.com/api/users/random_user?size=3', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            if not data:
                log(f'  [warn] no Random Data results')
                continue
            for user in data[:3]:
                first = user.get('first_name', '')
                last = user.get('last_name', '')
                email = user.get('email', '')
                username = user.get('username', '')
                text = f'Name: {first} {last}\nEmail: {email}\nUsername: {username}'
                parts.append(text)
                fetched += 1
                log(f'  [info] randomdata fetched: {first} {last}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] randomdata failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 31: Numbers API
def fetch_numbersapi_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [numbersapi] searching: {query}')
        try:
            req = Request('http://numbersapi.com/random/3?json', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            for num, fact in data.items():
                parts.append(f'{num}: {fact}')
                fetched += 1
                log(f'  [info] numbersapi fetched: {num}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] numbersapi failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 32: IP API
def fetch_ipapi_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [ipapi] searching: {query}')
        try:
            req = Request('https://ipapi.co/json/', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            text = f'IP: {data.get("ip", "")}\nCity: {data.get("city", "")}\nRegion: {data.get("region", "")}\nCountry: {data.get("country_name", "")}\nOrg: {data.get("org", "")}'
            parts.append(text)
            fetched += 1
            log(f'  [info] ipapi fetched: {data.get("ip", "")}')
        except Exception as exc:
            log(f'  [warn] ipapi failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 33: Timezone API
def fetch_timezone_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [timezone] searching: {query}')
        try:
            req = Request('https://worldtimeapi.org/api/timezone/Europe/London', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            text = f'Timezone: {data.get("timezone", "")}\nDatetime: {data.get("datetime", "")}\nDay of week: {data.get("day_of_week", "")}'
            parts.append(text)
            fetched += 1
            log(f'  [info] timezone fetched: {data.get("timezone", "")}')
        except Exception as exc:
            log(f'  [warn] timezone failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 34: Holiday API
def fetch_holidays_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [holidays] searching: {query}')
        try:
            req = Request('https://date.nager.at/api/v3/PublicHolidays/2024/US', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            holidays = data[:5]
            for holiday in holidays:
                name = holiday.get('localName', '')
                date = holiday.get('date', '')
                if name:
                    parts.append(f'Holiday: {name}\nDate: {date}')
                    fetched += 1
                    log(f'  [info] holidays fetched: {name}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] holidays failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 35: Exchange Rate API
def fetch_exchangerate_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [exchangerate] searching: {query}')
        try:
            req = Request('https://api.exchangerate-api.com/v4/latest/USD', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            rates = data.get('rates', {})
            text = f'Base: {data.get("base", "")}\nDate: {data.get("date", "")}'
            for currency, rate in list(rates.items())[:5]:
                text += f'\n{currency}: {rate}'
            parts.append(text)
            fetched += 1
            log(f'  [info] exchangerate fetched: {data.get("base", "")}')
        except Exception as exc:
            log(f'  [warn] exchangerate failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 36: CoinGecko crypto
def fetch_coingecko_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [coingecko] searching: {query}')
        try:
            req = Request('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=5&page=1', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            if not data:
                log(f'  [warn] no CoinGecko results')
                continue
            for coin in data[:3]:
                name = coin.get('name', '')
                symbol = coin.get('symbol', '')
                price = coin.get('current_price', 0)
                text = f'Coin: {name} ({symbol})\nPrice: ${price}'
                parts.append(text)
                fetched += 1
                log(f'  [info] coingecko fetched: {name}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] coingecko failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 37: CoinCap crypto
def fetch_coincap_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [coincap] searching: {query}')
        try:
            req = Request('https://api.coincap.io/v2/assets?limit=5', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            assets = data.get('data', [])
            if not assets:
                log(f'  [warn] no CoinCap results')
                continue
            for asset in assets[:3]:
                name = asset.get('name', '')
                symbol = asset.get('symbol', '')
                price = asset.get('priceUsd', '0')
                text = f'Asset: {name} ({symbol})\nPrice: ${price}'
                parts.append(text)
                fetched += 1
                log(f'  [info] coincap fetched: {name}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] coincap failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 38: MetaWeather
def fetch_metaweather_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [metaweather] searching: {query}')
        try:
            search_url = 'https://www.metaweather.com/api/location/search/?' + urlencode({
                'query': query,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            if not search_data:
                log(f'  [warn] no MetaWeather results for: {query}')
                continue
            for location in search_data[:2]:
                title = location.get('title', '')
                woeid = location.get('woeid', '')
                if not title:
                    continue
                text = f'Location: {title}\nWOEID: {woeid}'
                parts.append(text)
                fetched += 1
                log(f'  [info] metaweather fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] metaweather failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 39: MealDB recipes
def fetch_mealdb_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [mealdb] searching: {query}')
        try:
            search_url = 'https://www.themealdb.com/api/json/v1/1/search.php?' + urlencode({'s': query})
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            meals = data.get('meals', [])
            if not meals:
                log(f'  [warn] no MealDB results for: {query}')
                continue
            for meal in meals[:2]:
                name = meal.get('strMeal', '')
                category = meal.get('strCategory', '')
                area = meal.get('strArea', '')
                instructions = meal.get('strInstructions', '')[:300]
                text = f'Meal: {name}\nCategory: {category}\nArea: {area}\nInstructions: {instructions}'
                parts.append(text)
                fetched += 1
                log(f'  [info] mealdb fetched: {name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] mealdb failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 40: Cocktail DB
def fetch_cocktaildb_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [cocktaildb] searching: {query}')
        try:
            search_url = 'https://www.thecocktaildb.com/api/json/v1/1/search.php?' + urlencode({'s': query})
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            drinks = data.get('drinks', [])
            if not drinks:
                log(f'  [warn] no Cocktail DB results for: {query}')
                continue
            for drink in drinks[:2]:
                name = drink.get('strDrink', '')
                category = drink.get('strCategory', '')
                glass = drink.get('strGlass', '')
                instructions = drink.get('strInstructions', '')[:300]
                text = f'Drink: {name}\nCategory: {category}\nGlass: {glass}\nInstructions: {instructions}'
                parts.append(text)
                fetched += 1
                log(f'  [info] cocktaildb fetched: {name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] cocktaildb failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 41: Open Food Facts
def fetch_openfoodfacts_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [openfoodfacts] searching: {query}')
        try:
            search_url = 'https://world.openfoodfacts.org/api/v2/search?' + urlencode({
                'search_terms': query,
                'page_size': 3,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            products = data.get('products', [])
            if not products:
                log(f'  [warn] no Open Food Facts results for: {query}')
                continue
            for product in products[:2]:
                name = product.get('product_name', '')
                brand = product.get('brands', '')
                categories = product.get('categories', '')
                text = f'Product: {name}\nBrand: {brand}\nCategories: {categories}'
                parts.append(text)
                fetched += 1
                log(f'  [info] openfoodfacts fetched: {name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] openfoodfacts failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 42: PubChem compounds
def fetch_pubchem_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import quote
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [pubchem] searching: {query}')
        try:
            search_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(query)}/JSON'
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            compound = data.get('PC_Compounds', [{}])[0]
            props = compound.get('props', [])
            formula = ''
            mw = ''
            for prop in props:
                label = prop.get('urn', {}).get('label', '')
                if label == 'Molecular Formula':
                    formula = prop.get('value', {}).get('sval', '')
                elif label == 'Molecular Weight':
                    mw = prop.get('value', {}).get('fval', '')
            text = f'Compound: {query}\nFormula: {formula}\nMolecular Weight: {mw}'
            parts.append(text)
            fetched += 1
            log(f'  [info] pubchem fetched: {query}')
        except Exception as exc:
            log(f'  [warn] pubchem failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 43: ChEMBL bioactivity
def fetch_chembl_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import quote
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [chembl] searching: {query}')
        try:
            search_url = f'https://www.ebi.ac.uk/chembl/api/data/molecule?pref_name__iexact={quote(query)}&limit=1'
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            molecules = data.get('molecules', [])
            if not molecules:
                log(f'  [warn] no ChEMBL results for: {query}')
                continue
            mol = molecules[0]
            pref_name = mol.get('pref_name', '')
            chembl_id = mol.get('chEMBL_ID', '')
            text = f'Molecule: {pref_name}\nChEMBL ID: {chembl_id}'
            parts.append(text)
            fetched += 1
            log(f'  [info] chembl fetched: {pref_name}')
        except Exception as exc:
            log(f'  [warn] chembl failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 44: ClinicalTrials
def fetch_clinicaltrials_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [clinicaltrials] searching: {query}')
        try:
            search_url = 'https://clinicaltrials.gov/api/query/full_studies?' + urlencode({
                'expr': query,
                'min_rnk': 1,
                'max_rnk': 3,
                'fmt': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            studies = data.get('FullStudiesResponse', {}).get('FullStudies', [])
            if not studies:
                log(f'  [warn] no ClinicalTrials results for: {query}')
                continue
            for study in studies:
                protocol = study.get('Study', {}).get('ProtocolSection', {})
                identification = protocol.get('IdentificationModule', {})
                brief_title = identification.get('BriefTitle', '')
                official_title = identification.get('OfficialTitle', '')
                text = f'Brief Title: {brief_title}\nOfficial Title: {official_title[:200]}'
                parts.append(text)
                fetched += 1
                log(f'  [info] clinicaltrials fetched: {brief_title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] clinicaltrials failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 45: Launch Library
def fetch_launchlibrary_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [launchlibrary] searching: {query}')
        try:
            req = Request('https://ll.thespacedevs.com/2.2.0/launch/upcoming?limit=3', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            launches = data.get('results', [])
            if not launches:
                log(f'  [warn] no Launch Library results')
                continue
            for launch in launches[:3]:
                name = launch.get('name', '')
                status = launch.get('status', {}).get('name', '')
                net = launch.get('net', '')
                text = f'Launch: {name}\nStatus: {status}\nNET: {net}'
                parts.append(text)
                fetched += 1
                log(f'  [info] launchlibrary fetched: {name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] launchlibrary failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 46: SpaceX launches
def fetch_spacex_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [spacex] searching: {query}')
        try:
            req = Request('https://api.spacexdata.com/v4/launches?limit=3', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            if not data:
                log(f'  [warn] no SpaceX results')
                continue
            for launch in data[:3]:
                name = launch.get('name', '')
                date = launch.get('date_utc', '')
                success = launch.get('success', '')
                text = f'Launch: {name}\nDate: {date}\nSuccess: {success}'
                parts.append(text)
                fetched += 1
                log(f'  [info] spacex fetched: {name[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] spacex failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 47: ISS location
def fetch_iss_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [iss] searching: {query}')
        try:
            req = Request('http://api.open-notify.org/iss-now.json', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            timestamp = data.get('timestamp', '')
            position = data.get('iss_position', {})
            lat = position.get('latitude', '')
            lon = position.get('longitude', '')
            text = f'Timestamp: {timestamp}\nLatitude: {lat}\nLongitude: {lon}'
            parts.append(text)
            fetched += 1
            log(f'  [info] iss fetched: {lat}, {lon}')
        except Exception as exc:
            log(f'  [warn] iss failed: {query} | {exc}')

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 48: Earthquake data
def fetch_earthquake_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [earthquake] searching: {query}')
        try:
            req = Request('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson', headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
            features = data.get('features', [])
            if not features:
                log(f'  [warn] no earthquake data')
                continue
            for feature in features[:5]:
                props = feature.get('properties', {})
                mag = props.get('mag', '')
                place = props.get('place', '')
                time = props.get('time', '')
                text = f'Magnitude: {mag}\nPlace: {place}\nTime: {time}'
                parts.append(text)
                fetched += 1
                log(f'  [info] earthquake fetched: {place[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] earthquake failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 49: Wikimedia Commons
def fetch_commons_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [commons] searching: {query}')
        try:
            search_url = 'https://commons.wikimedia.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
                'srnamespace': 6,
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Commons results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                snippet = page.get('snippet', '')
                if not title:
                    continue
                text = f'File: {title}\n{snippet}'
                parts.append(text)
                fetched += 1
                log(f'  [info] commons fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] commons search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 50: Wikisource
def fetch_wikisource_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wikisource] searching: {query}')
        try:
            search_url = 'https://en.wikisource.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Wikisource results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                snippet = page.get('snippet', '')
                if not title:
                    continue
                text = f'Source: {title}\n{snippet}'
                parts.append(text)
                fetched += 1
                log(f'  [info] wikisource fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wikisource search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 51: Wikinews
def fetch_wikinews_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wikinews] searching: {query}')
        try:
            search_url = 'https://en.wikinews.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Wikinews results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                snippet = page.get('snippet', '')
                if not title:
                    continue
                text = f'News: {title}\n{snippet}'
                parts.append(text)
                fetched += 1
                log(f'  [info] wikinews fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wikinews search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched

# Source 52: Wikivoyage
def fetch_wikivoyage_text(queries: list[str], max_chars: int = 12000) -> tuple[str, int]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    parts: list[str] = []
    fetched = 0

    for query in queries:
        log(f'  [wikivoyage] searching: {query}')
        try:
            search_url = 'https://en.wikivoyage.org/w/api.php?' + urlencode({
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 3,
                'format': 'json',
            })
            req = Request(search_url, headers={'User-Agent': 'myai-trainer/0.1 (research)'})
            with urlopen(req, timeout=20) as response:
                search_data = json.loads(response.read().decode('utf-8'))
            pages = search_data.get('query', {}).get('search', [])
            if not pages:
                log(f'  [warn] no Wikivoyage results for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                snippet = page.get('snippet', '')
                if not title:
                    continue
                text = f'Guide: {title}\n{snippet}'
                parts.append(text)
                fetched += 1
                log(f'  [info] wikivoyage fetched: {title[:60]}')
                if sum(len(p) for p in parts) >= max_chars:
                    break
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] wikivoyage search failed: {query} | {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars], fetched


# ──────────────────────────────────────────────────────────────
# Main fetcher: combines all sources
# ──────────────────────────────────────────────────────────────
def fetch_training_text(queries: list[str], max_chars: int = 20000) -> str:
    sources = [
        ('web', fetch_web_text, 0.10),
        ('wiki', fetch_wikipedia_text, 0.08),
        ('stack', fetch_stackexchange_text, 0.06),
        ('arxiv', fetch_arxiv_text, 0.06),
        ('github', fetch_github_text, 0.04),
        ('hn', fetch_hackernews_text, 0.04),
        ('reddit', fetch_reddit_text, 0.04),
        ('wiktionary', fetch_wiktionary_text, 0.04),
        ('wikiquote', fetch_wikiquote_text, 0.04),
        ('wikidata', fetch_wikidata_text, 0.04),
        ('openlibrary', fetch_openlibrary_text, 0.04),
        ('pubmed', fetch_pubmed_text, 0.04),
        ('crossref', fetch_crossref_text, 0.03),
        ('europepmc', fetch_europepmc_text, 0.03),
        ('nominatim', fetch_nominatim_text, 0.03),
        ('restcountries', fetch_restcountries_text, 0.03),
        ('wikipediarandom', fetch_wikipediarandom_text, 0.03),
        ('duckduckgo', fetch_duckduckgo_text, 0.03),
        ('opentdb', fetch_opentdb_text, 0.03),
        ('jokeapi', fetch_jokeapi_text, 0.03),
        ('commons', fetch_commons_text, 0.03),
        ('wikisource', fetch_wikisource_text, 0.03),
        ('wikinews', fetch_wikinews_text, 0.03),
        ('wikivoyage', fetch_wikivoyage_text, 0.03),
        ('opennotify', fetch_opennotify_text, 0.02),
        ('sunrise', fetch_sunrise_text, 0.02),
        ('catfacts', fetch_catfacts_text, 0.02),
        ('dogfacts', fetch_dogfacts_text, 0.02),
        ('bored', fetch_bored_text, 0.02),
        ('advice', fetch_advice_text, 0.02),
        ('kanye', fetch_kanye_text, 0.02),
        ('randomuser', fetch_randomuser_text, 0.02),
        ('randomdata', fetch_randomdata_text, 0.02),
        ('numbersapi', fetch_numbersapi_text, 0.02),
        ('ipapi', fetch_ipapi_text, 0.02),
        ('timezone', fetch_timezone_text, 0.02),
        ('holidays', fetch_holidays_text, 0.02),
        ('exchangerate', fetch_exchangerate_text, 0.02),
        ('coingecko', fetch_coingecko_text, 0.02),
        ('coincap', fetch_coincap_text, 0.02),
        ('metaweather', fetch_metaweather_text, 0.02),
        ('mealdb', fetch_mealdb_text, 0.02),
        ('cocktaildb', fetch_cocktaildb_text, 0.02),
        ('openfoodfacts', fetch_openfoodfacts_text, 0.02),
        ('pubchem', fetch_pubchem_text, 0.02),
        ('chembl', fetch_chembl_text, 0.02),
        ('clinicaltrials', fetch_clinicaltrials_text, 0.02),
        ('launchlibrary', fetch_launchlibrary_text, 0.02),
        ('spacex', fetch_spacex_text, 0.02),
        ('iss', fetch_iss_text, 0.02),
        ('earthquake', fetch_earthquake_text, 0.02),
    ]

    parts: list[str] = []
    seen_normalized: set[str] = set()

    for source_name, fetcher, budget_frac in sources:
        budget = max(1000, int(max_chars * budget_frac))
        if sum(len(p) for p in parts) >= max_chars:
            break
        log(f'[data] fetching from {source_name} (budget={budget})')
        try:
            text, fetched_count = fetcher(queries, max_chars=budget)
            if text:
                normalized = ' '.join(text.lower().split())[:200]
                if normalized not in seen_normalized:
                    seen_normalized.add(normalized)
                    parts.append(text)
                    log(f'[data] {source_name}: added {len(text)} chars from {fetched_count} items')
                else:
                    log(f'[data] {source_name}: skipped (duplicate content)')
        except Exception as exc:
            log(f'[warn] {source_name} fetch failed: {exc}')

    combined = '\n\n'.join(parts)
    return combined[:max_chars]

def make_progress_logger():
    epoch_start = None
    def progress_callback(event, **kwargs):
        nonlocal epoch_start
        if event == 'epoch_start':
            epoch = kwargs['epoch']
            epochs = kwargs['epochs']
            total_texts = kwargs['total_texts']
            epoch_start = time.time()
            log('-' * 72)
            log(f'[train] epoch {epoch}/{epochs} started | texts={total_texts}')
            log('-' * 72)
        elif event == 'step':
            epoch = kwargs['epoch']
            epochs = kwargs['epochs']
            text_index = kwargs['text_index']
            total_texts = kwargs['total_texts']
            loss = kwargs['loss']
            step_time = kwargs.get('step_time', 0.0)
            avg_step = kwargs.get('avg_step_time', 0.0)
            pct = text_index / total_texts * 100
            log(f'  [train] epoch={epoch}/{epochs} step={text_index}/{total_texts} ({pct:.0f}%) loss={loss:.4f} step={step_time:.2f}s avg={avg_step:.2f}s')
        elif event == 'epoch_end':
            epoch = kwargs['epoch']
            epochs = kwargs['epochs']
            loss = kwargs['loss']
            elapsed = kwargs['elapsed']
            steps = kwargs['steps']
            log('-' * 72)
            log(f'[train] epoch={epoch}/{epochs} complete | loss={loss:.4f} | steps={steps} | time={elapsed:.1f}s')
            log('-' * 72)
    return progress_callback

def main() -> None:
    log('=' * 72)
    log('[pipeline] training started')
    log('=' * 72)

    config = load_config(ROOT / 'config.json')
    model_cfg = config.get('model', {})
    model_path = ROOT / model_cfg.get('path', 'models/local_model.bin')
    tokenizer_path = ROOT / model_cfg.get('tokenizer', 'models/tokenizer.json')

    queries_raw = os.environ.get('TRAINING_QUERIES', '').strip()
    if queries_raw:
        queries = [q.strip() for q in queries_raw.split(',') if q.strip()]
    else:
        queries = DEFAULT_QUERIES

    epochs_raw = os.environ.get('EPOCHS', '5').strip()
    try:
        epochs = max(1, int(epochs_raw))
    except ValueError:
        epochs = 5

    lr_raw = os.environ.get('LEARNING_RATE', '0.05').strip()
    try:
        learning_rate = max(1e-6, float(lr_raw))
    except ValueError:
        learning_rate = 0.05

    max_chars_raw = os.environ.get('MAX_CHARS', '20000').strip()
    try:
        max_chars = max(1000, int(max_chars_raw))
    except ValueError:
        max_chars = 20000

    time_limit_raw = os.environ.get('TIME_LIMIT_MINUTES', '120').strip()
    try:
        time_limit_minutes = int(time_limit_raw)
    except ValueError:
        time_limit_minutes = 120

    log('[config]')
    log(f'  queries={len(queries)}')
    log(f'  epochs={epochs}')
    log(f'  learning_rate={learning_rate}')
    log(f'  max_chars={max_chars}')
    log(f'  time_limit_minutes={time_limit_minutes}')

    start_time = time.time()

    log('[tokenizer] loading...')
    tokenizer = ByteBPETokenizer.from_json(tokenizer_path)
    log(f'[tokenizer] loaded vocab_size={tokenizer.vocabulary_size}')

    log('[data] fetching training text...')
    text = fetch_training_text(queries, max_chars=max_chars)
    elapsed = time.time() - start_time
    log(f'[data] fetched {len(text)} chars in {elapsed:.1f}s')
    log(f'[data] source=multi-source')

    if not text:
        log('[warn] no training text fetched; using fallback text')
        text = '\n'.join([
            'Python is a programming language.',
            'Machine learning is a subset of artificial intelligence.',
            'Software engineering involves designing and building software.',
            'Data structures include arrays, lists, trees, and graphs.',
            'Algorithms are step-by-step procedures for solving problems.',
            'Web development uses HTML, CSS, and JavaScript.',
            'Computer science studies computation and information.',
        ] * 50)

    texts = [t for t in text.split('\n\n') if len(t.strip()) > 10]
    log(f'[data] training texts={len(texts)}')

    log('[train] starting')
    train_start = time.time()
    try:
        progress = make_progress_logger()
        train_on_text(
            model_path=model_path,
            tokenizer=tokenizer,
            texts=texts,
            epochs=epochs,
            lr=learning_rate,
            seed=42,
            progress_callback=progress,
        )
    except Exception as exc:
        log(f'[error] training failed: {exc}')
        raise

    train_elapsed = time.time() - train_start
    total_elapsed = time.time() - start_time
    log(f'[train] completed in {train_elapsed:.1f}s | total={total_elapsed:.1f}s')
    log(f'[model] saved to: {model_path}')

    if total_elapsed > time_limit_minutes * 60:
        log(f'[warn] exceeded time limit of {time_limit_minutes} minutes')

    log('=' * 72)
    log('[pipeline] training completed successfully')
    log('=' * 72)

if __name__ == '__main__':
    main()
