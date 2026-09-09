"""Train the local model on web-fetched text."""
from __future__ import annotations
import json
import os
import random
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

def fetch_training_text(queries: list[str], max_chars: int = 20000) -> str:
    search = WebSearch(allow_network=True, timeout=20)
    reader = WebReader(allow_network=True, timeout=20)
    seen_urls: set[str] = set()
    parts: list[str] = []

    for query in queries:
        log(f'🔍 Searching: {query}')
        try:
            result = search.run({'query': query, 'num_results': 5})
            if not result.ok:
                log(f'  ⚠️ Search failed: {result.error}')
                continue
            log(f'  ✅ Got search results')
            for line in result.output.splitlines():
                if line.startswith('   ') and not line.startswith('   http'):
                    parts.append(line.strip())
                elif line.startswith('http'):
                    url = line.strip()
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    try:
                        log(f'  📄 Reading: {url}')
                        read_result = reader.run({'url': url, 'max_chars': 2000})
                        if read_result.ok and read_result.output:
                            parts.append(read_result.output)
                            log(f'  ✅ Read {len(read_result.output)} chars')
                            if sum(len(p) for p in parts) >= max_chars:
                                break
                        else:
                            log(f'  ⚠️ Read failed: {read_result.error}')
                    except Exception as exc:
                        log(f'  ⚠️ Read error: {exc}')
                        continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception as exc:
            log(f'  ⚠️ Search error: {exc}')
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars]

def main() -> None:
    log('=' * 60)
    log('🚀 Starting training pipeline')
    log('=' * 60)

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

    log('📋 Configuration:')
    log(f'   Queries: {len(queries)} topics')
    log(f'   Epochs: {epochs}')
    log(f'   Learning rate: {learning_rate}')
    log(f'   Max chars: {max_chars}')
    log(f'   Time limit: {time_limit_minutes} minutes')

    start_time = time.time()

    log('📚 Loading tokenizer...')
    tokenizer = ByteBPETokenizer.from_json(tokenizer_path)
    log(f'✅ Tokenizer loaded (vocab size: {tokenizer.vocabulary_size})')

    log('🌐 Fetching training text...')
    text = fetch_training_text(queries, max_chars=max_chars)
    elapsed = time.time() - start_time
    log(f'✅ Fetched {len(text)} characters in {elapsed:.1f}s')

    if not text:
        log('⚠️ No training text fetched. Using fallback text.')
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
    log(f'📊 Training on {len(texts)} text chunks')

    log('🧠 Training model...')
    train_start = time.time()
    try:
        train_on_text(
            model_path=model_path,
            tokenizer=tokenizer,
            texts=texts,
            epochs=epochs,
            lr=learning_rate,
            seed=42,
        )
    except Exception as exc:
        log(f'❌ Training failed: {exc}')
        raise

    train_elapsed = time.time() - train_start
    total_elapsed = time.time() - start_time
    log(f'✅ Training completed in {train_elapsed:.1f}s (total: {total_elapsed:.1f}s)')
    log(f'💾 Model saved to: {model_path}')

    if total_elapsed > time_limit_minutes * 60:
        log(f'⚠️ Training exceeded time limit of {time_limit_minutes} minutes')

    log('=' * 60)
    log('🎉 Training pipeline completed successfully')
    log('=' * 60)

if __name__ == '__main__':
    main()
