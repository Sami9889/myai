"""Train the local model on web-fetched text."""
from __future__ import annotations
import random
import time
from pathlib import Path
from core_engine.tokenizer import ByteBPETokenizer
from core_engine.trainer import train_on_text
from tools.web_search import WebSearch
from tools.web_reader import WebReader
from utils.config_loader import load_config

ROOT = Path(__file__).resolve().parent.parent
random.seed(42)

def fetch_training_text(queries: list[str], max_chars: int = 20000) -> str:
    search = WebSearch(allow_network=True, timeout=20)
    reader = WebReader(allow_network=True, timeout=20)
    seen_urls: set[str] = set()
    parts: list[str] = []

    for query in queries:
        try:
            result = search.run({'query': query, 'num_results': 5})
            if not result.ok:
                continue
            for line in result.output.splitlines():
                if line.startswith('   ') and not line.startswith('   http'):
                    parts.append(line.strip())
                elif line.startswith('http'):
                    url = line.strip()
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    try:
                        read_result = reader.run({'url': url, 'max_chars': 2000})
                        if read_result.ok and read_result.output:
                            parts.append(read_result.output)
                            if sum(len(p) for p in parts) >= max_chars:
                                break
                    except Exception:
                        continue
            if sum(len(p) for p in parts) >= max_chars:
                break
        except Exception:
            continue

    text = '\n\n'.join(parts)
    return text[:max_chars]

def main() -> None:
    config = load_config(ROOT / 'config.json')
    model_cfg = config.get('model', {})
    model_path = ROOT / model_cfg.get('path', 'models/local_model.bin')
    tokenizer_path = ROOT / model_cfg.get('tokenizer', 'models/tokenizer.json')

    tokenizer = ByteBPETokenizer.from_json(tokenizer_path)
    queries = [
        'Python programming language',
        'artificial intelligence',
        'machine learning',
        'software engineering',
        'data structures algorithms',
        'web development',
        'computer science',
    ]

<<<<<<< ours
    print('Fetching training text...')
    text = fetch_training_text(queries, max_chars=20000)
    print(f'Fetched {len(text)} characters')
    if not text:
        print('No training text fetched. Using fallback text.')
=======
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
>>>>>>> theirs
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
<<<<<<< ours
    print(f'Training on {len(texts)} text chunks')

    print('Training model...')
    start = time.time()
    train_on_text(
        model_path=model_path,
        tokenizer=tokenizer,
        texts=texts,
        epochs=5,
        lr=0.05,
        seed=42,
    )
    elapsed = time.time() - start
    print(f'Training completed in {elapsed:.1f}s')
    print(f'Model saved to: {model_path}')
=======
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
>>>>>>> theirs

if __name__ == '__main__':
    main()
