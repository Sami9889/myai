"""Train the local model on web-fetched text."""
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

def fetch_wikipedia_text(queries: list[str], max_chars: int = 12000) -> str:
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

    for query in queries:
        log(f'  [wiki] searching articles for: {query}')
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
                log(f'  [warn] no Wikipedia articles found for: {query}')
                continue
            for page in pages:
                title = page.get('title', '')
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                try:
                    article_url = 'https://en.wikipedia.org/wiki/' + urlencode({'title': title})[7:]
                    article_url = 'https://en.wikipedia.org/wiki/' + title.replace(' ', '_')
                    log(f'  [wiki] fetching article: {title}')
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
                        log(f'  [info] Wikipedia article fetched: {len(text)} chars')
                    else:
                        log(f'  [warn] Wikipedia article empty: {title}')
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                except Exception as exc:
                    log(f'  [warn] Wikipedia article fetch failed: {title} | {exc}')
                    continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  [warn] Wikipedia search failed: {query} | {exc}')
            continue

    result = '\n\n'.join(parts)
    return result[:max_chars]

def fetch_training_text(queries: list[str], max_chars: int = 20000) -> str:
    search = WebSearch(allow_network=True, timeout=20)
    reader = WebReader(allow_network=True, timeout=20)
    seen_urls: set[str] = set()
    parts: list[str] = []

    web_budget = max(1000, max_chars // 2)
    wiki_budget = max_chars - web_budget

    for query in queries:
        log(f'[search] query="{query}"')
        try:
            result = search.run({'query': query, 'num_results': 5})
            if not result.ok:
                log(f'  [warn] search failed: {result.error}')
                continue
            log(f'  [info] search results received')
            for line in result.output.splitlines():
                if line.startswith('   ') and not line.startswith('   http'):
                    parts.append(line.strip())
                elif line.startswith('http'):
                    url = line.strip()
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    try:
                        log(f'  [fetch] url="{url}"')
                        read_result = reader.run({'url': url, 'max_chars': 2000})
                        if read_result.ok and read_result.output:
                            parts.append(read_result.output)
                            log(f'  [info] fetched {len(read_result.output)} chars')
                            if sum(len(p) for p in parts) >= web_budget:
                                break
                        else:
                            log(f'  [warn] fetch failed: {read_result.error}')
                    except Exception as exc:
                        log(f'  [warn] fetch error: {exc}')
                        continue
            if sum(len(p) for p in parts) >= web_budget:
                break
        except Exception as exc:
            log(f'  [warn] search error: {exc}')
            continue

    web_text = '\n\n'.join(parts)
    log(f'[data] web source chars={len(web_text)}')

    log('[data] fetching Wikipedia articles...')
    wiki_text = fetch_wikipedia_text(queries, max_chars=wiki_budget)
    log(f'[data] wikipedia source chars={len(wiki_text)}')

    combined = '\n\n'.join(filter(None, [web_text, wiki_text]))
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
            pct = text_index / total_texts * 100
            log(f'  [train] epoch={epoch}/{epochs} step={text_index}/{total_texts} ({pct:.0f}%) loss={loss:.4f}')
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
    log(f'[data] source=web+wikipedia')

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
