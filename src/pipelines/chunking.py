import re
from uuid import NAMESPACE_URL, uuid5

# Heuristic patterns to detect IWF articles and sections.
ARTICLE_PATTERNS = [
    re.compile(r"Article\s+\d+", re.IGNORECASE),
    re.compile(r"Rule\s+\d+", re.IGNORECASE),
    re.compile(r"Section\s+\d+", re.IGNORECASE),
    re.compile(r"§\s*\d+"),
]


class JuridicalChunker:
    """Splits IWF regulation text into overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ".", " ", ""]

    def _detect_article(self, text: str) -> str | None:
        """Detects the first IWF article/section in a text.

        Args:
            text: candidate text.

        Returns:
            The detected article label (e.g. "Article 5"), or None.
        """
        for pattern in ARTICLE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0).strip()
        return None

    def chunk_text(self, text: str, source: str, page: int) -> list[dict[str, object]]:
        """Splits page text into overlapping chunks.

        Args:
            text: raw page text.
            source: source PDF file name.
            page: page number (1-indexed) the text comes from.

        Returns:
            List of dicts {id, source, article, page, chunk_text}.
            Embedding is added later by embeddings.py.
        """
        chunks: list[dict[str, object]] = []
        current_pos = 0
        chunk_index = 0
        current_article: str | None = None

        while current_pos < len(text):
            # Extract a chunk of chunk_size length
            end_pos = min(current_pos + self.chunk_size, len(text))
            chunk_text = text[current_pos:end_pos]

            # Adjust to sentence end if possible
            for sep in self.separators:
                last_sep = chunk_text.rfind(sep)
                if last_sep > self.chunk_size * 0.5:  # At least 50% of the chunk
                    end_pos = current_pos + last_sep + len(sep)
                    chunk_text = text[current_pos:end_pos]
                    break

            # Article detection: store the last article found
            # to propagate to subsequent chunks in the same section.
            detected_article = self._detect_article(chunk_text)
            if detected_article:
                current_article = detected_article

            chunks.append(
                {
                    "id": str(uuid5(NAMESPACE_URL, f"{source}_{chunk_index}")),
                    "source": source,
                    "article": current_article,
                    "page": page,
                    "chunk_text": chunk_text.strip(),
                }
            )
            chunk_index += 1

            # Advance with overlap, with infinite-loop guard:
            # stop at end of text or if position does not advance.
            next_pos = end_pos - self.chunk_overlap
            if end_pos >= len(text) or next_pos <= current_pos:
                break
            current_pos = next_pos

        return chunks