from typing import List, Dict, Optional

class JuridicalChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, 
                 separators: Optional[List[str]] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ".", " ", ""]
    
    def chunk_text(self, text: str, source: str) -> List[Dict[str, object]]:
        """Chunk le texte avec chevauchement"""
        chunks = []
        current_pos = 0
        chunk_id = 0
        
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
            
            chunks.append({
                "id": f"{source}_{chunk_id}",
                "text": chunk_text.strip(),
                "source": source,
                "position": chunk_id,
                "char_start": current_pos,
                "char_end": end_pos
            })
            
            # Avancer avec chevauchement
            current_pos = end_pos - self.chunk_overlap
            chunk_id += 1
        
        return chunks