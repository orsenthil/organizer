from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from PyPDF2 import PdfReader


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "you",
    "your",
    "are",
    "was",
    "were",
    "will",
    "have",
    "has",
    "had",
    "not",
    "but",
    "about",
    "into",
    "than",
    "then",
    "there",
    "their",
    "them",
    "they",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "how",
    "also",
    "pdf",
    "file",
    "document",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".rtf",
}


def sanitize_topic(topic: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", " ", topic)
    tokens = [token.strip() for token in cleaned.split() if token.strip()]
    if not tokens:
        return "Uncategorized"
    return "_".join(tokens[:4])


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    return [word for word in words if word not in STOPWORDS]


def _make_bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[idx]}_{tokens[idx + 1]}" for idx in range(len(tokens) - 1)]


def extract_keywords(text: str, max_keywords: int = 8) -> list[str]:
    tokens = _tokenize(text)
    if not tokens:
        return []
    counts: dict[str, int] = {}
    for token in tokens + _make_bigrams(tokens):
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:max_keywords]]


def label_from_keywords(keywords: list[str], max_words: int = 3) -> str:
    if not keywords:
        return "Uncategorized"
    words = [keyword.replace("_", " ") for keyword in keywords[:max_words]]
    return sanitize_topic(" ".join(words))


def infer_topic_from_text(text: str) -> str:
    keywords = extract_keywords(text, max_keywords=6)
    return label_from_keywords(keywords, max_words=3)


def infer_topic_from_filename(path: Path) -> str:
    tokens = _tokenize(path.stem.replace("-", " ").replace("_", " "))
    if not tokens:
        return "Uncategorized"
    return sanitize_topic(" ".join(tokens[:3]))


def _read_text_file(path: Path, max_chars: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(max_chars)
    except OSError:
        return ""


def _read_pdf_text(path: Path, max_pages: int, max_chars: int) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    texts: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text:
            texts.append(text)
        if sum(len(chunk) for chunk in texts) >= max_chars:
            break
    return " ".join(texts)[:max_chars]


def infer_topic_for_file(
    path: Path,
    max_pages: int = 3,
    max_chars: int = 10000,
    text_extensions: Iterable[str] | None = None,
) -> str:
    suffix = path.suffix.lower()
    text_exts = set(text_extensions or TEXT_EXTENSIONS)
    content_text = ""
    if suffix == ".pdf":
        content_text = _read_pdf_text(path, max_pages=max_pages, max_chars=max_chars)
    elif suffix in text_exts:
        content_text = _read_text_file(path, max_chars=max_chars)
    if content_text.strip():
        return infer_topic_from_text(content_text)
    return infer_topic_from_filename(path)


def infer_topic_and_keywords_for_file(
    path: Path,
    max_pages: int = 3,
    max_chars: int = 10000,
    text_extensions: Iterable[str] | None = None,
) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    text_exts = set(text_extensions or TEXT_EXTENSIONS)
    content_text = ""
    if suffix == ".pdf":
        content_text = _read_pdf_text(path, max_pages=max_pages, max_chars=max_chars)
    elif suffix in text_exts:
        content_text = _read_text_file(path, max_chars=max_chars)
    if content_text.strip():
        keywords = extract_keywords(content_text, max_keywords=10)
        return label_from_keywords(keywords, max_words=3), keywords
    topic = infer_topic_from_filename(path)
    filename_tokens = _tokenize(path.stem.replace("-", " ").replace("_", " "))
    return topic, filename_tokens[:6]
