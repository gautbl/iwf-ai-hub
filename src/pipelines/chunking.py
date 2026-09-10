import re
from typing import Dict, List, Optional
from uuid import NAMESPACE_URL, uuid5

# Patterns heuristiques de détection des articles et sections IWF.
ARTICLE_PATTERNS = [
    re.compile(r"Article\s+\d+", re.IGNORECASE),
    re.compile(r"Rule\s+\d+", re.IGNORECASE),
    re.compile(r"Section\s+\d+", re.IGNORECASE),
    re.compile(r"§\s*\d+"),
]


class JuridicalChunker:
    """Découpe le texte réglementaire IWF en chunks chevauchants."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50,
                 separators: Optional[List[str]] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ".", " ", ""]

    def _detect_article(self, text: str) -> Optional[str]:
        """Détecte le premier article/section IWF dans un texte.

        Args:
            text: texte candidat.

        Returns:
            Le libellé de l'article détecté (ex: "Article 5"), sinon None.
        """
        for pattern in ARTICLE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0).strip()
        return None

    def chunk_text(self, text: str, source: str, page: int) -> List[Dict[str, object]]:
        """Découpe le texte d'une page en chunks avec chevauchement.

        Args:
            text: texte brut de la page.
            source: nom du PDF d'origine.
            page: numéro de page (1-indexé) d'où provient le texte.

        Returns:
            Liste de dicts {id, source, article, page, chunk_text}.
            L'embedding est ajouté ultérieurement par embeddings.py.
        """
        chunks: List[Dict[str, object]] = []
        current_pos = 0
        chunk_index = 0
        current_article: Optional[str] = None

        while current_pos < len(text):
            # Extraire un chunk de taille chunk_size
            end_pos = min(current_pos + self.chunk_size, len(text))
            chunk_text = text[current_pos:end_pos]

            # Ajuster à la fin de phrase si possible
            for sep in self.separators:
                last_sep = chunk_text.rfind(sep)
                if last_sep > self.chunk_size * 0.5:  # Au moins 50% du chunk
                    end_pos = current_pos + last_sep + len(sep)
                    chunk_text = text[current_pos:end_pos]
                    break

            # Détection de l'article : on mémorise le dernier article rencontré
            # afin de le propager aux chunks suivants d'une même section.
            detected_article = self._detect_article(chunk_text)
            if detected_article:
                current_article = detected_article

            chunks.append({
                "id": str(uuid5(NAMESPACE_URL, f"{source}_{chunk_index}")),
                "source": source,
                "article": current_article,
                "page": page,
                "chunk_text": chunk_text.strip(),
            })
            chunk_index += 1

            # Avancer avec chevauchement, avec garde-fou anti-boucle infinie :
            # on s'arrête en fin de texte ou si la position n'avance plus.
            next_pos = end_pos - self.chunk_overlap
            if end_pos >= len(text) or next_pos <= current_pos:
                break
            current_pos = next_pos

        return chunks
