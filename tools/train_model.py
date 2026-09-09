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

    print('Fetching training text...')
    text = fetch_training_text(queries, max_chars=20000)
    print(f'Fetched {len(text)} characters')
    if not text:
        print('No training text fetched. Using fallback text.')
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

if __name__ == '__main__':
    main()
