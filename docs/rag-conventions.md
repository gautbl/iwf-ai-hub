# RAG Conventions - IWF AI Hub

## Embedding model (Ollama)
- Model: (to define, e.g. nomic-embed-text)
- Dimension: (to define, e.g. 768)
- Endpoint: http://localhost:11434/api/embeddings

## Chunking strategy
- Split by IWF regulatory article
- Target size: 300-500 tokens per chunk
- Overlap: 50 tokens

## Similarity threshold
- Minimum cosine score for retrieval: 0.75 (to tune)