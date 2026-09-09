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

def log_memory(label: str = '') -> None:
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_kb = usage.ru_maxrss
        if sys.platform == 'linux':
            mem_mb = mem_kb / 1024
        else:
            mem_mb = mem_kb / 1024 / 1024
        log(f'[mem] {label} rss={mem_mb:.1f} MB')
    except Exception:
        pass

# --------------------------------------------------------------
# Source 1: Web search + webpage read
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Source 2: Wikipedia articles
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Source 3: Stack Exchange / Stack Overflow
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Source 4: arXiv papers
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Source 5: GitHub repositories
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Source 6: Hacker News
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Source 7: Reddit posts
# --------------------------------------------------------------
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

# --------------------------------------------------------------
# Main fetcher: combines all sources
# --------------------------------------------------------------
def fetch_training_text(queries: list[str], max_chars: int = 20000) -> str:
    sources = [
        ('web', fetch_web_text, 0.20),
        ('wiki', fetch_wikipedia_text, 0.20),
        ('stack', fetch_stackexchange_text, 0.15),
        ('arxiv', fetch_arxiv_text, 0.15),
        ('github', fetch_github_text, 0.10),
        ('hn', fetch_hackernews_text, 0.10),
        ('reddit', fetch_reddit_text, 0.10),
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

    log_memory('start')

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

    log_memory('end')

    if total_elapsed > time_limit_minutes * 60:
        log(f'[warn] exceeded time limit of {time_limit_minutes} minutes')

    log('=' * 72)
    log('[pipeline] training completed successfully')
    log('=' * 72)

if __name__ == '__main__':
    main()
