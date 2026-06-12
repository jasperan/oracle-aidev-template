"""Document chunking with overlap for real-world document ingestion.

Splits large texts into overlapping chunks that each get their own embedding.
Sentence-boundary aware: won't cut mid-sentence when possible.

Inspired by oci-genai-service's RecursiveChunker and cAST-efficient-ollama's
random_chunker patterns.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    """A chunk of text and its sequential index."""

    text: str
    index: int


# Splitting hierarchy: try paragraph breaks first, then sentences, then words
_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]


def _split_at_separator(text: str, sep: str) -> list[str]:
    """Split text at a separator, keeping the separator attached to each preceding piece.

    Every piece (except possibly the last) retains its trailing separator, so the
    pieces can be rejoined with ``""`` to reconstruct the original text without
    duplicating the separator.
    """
    pieces = []
    start = 0
    sep_len = len(sep)
    idx = text.find(sep)
    while idx != -1:
        pieces.append(text[start : idx + sep_len])
        start = idx + sep_len
        idx = text.find(sep, start)
    if start < len(text):
        pieces.append(text[start:])
    return [p for p in pieces if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_size: int = 50,
) -> list[Chunk]:
    """Split text into overlapping chunks, respecting sentence boundaries.

    Args:
        text: The text to chunk.
        chunk_size: Target size for each chunk (in characters).
        chunk_overlap: Number of characters to overlap between consecutive chunks.
        min_chunk_size: Minimum chunk size. Chunks smaller than this merge into neighbors.

    Returns:
        List of Chunk objects with text and a sequential index.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # If text fits in one chunk, return it directly
    if len(text) <= chunk_size:
        return [Chunk(text=text, index=0)]

    raw_chunks = _recursive_split(text, chunk_size)

    # Merge tiny chunks into their neighbors, but never past the target chunk_size
    merged: list[str] = []
    for piece in raw_chunks:
        if (
            merged
            and (len(merged[-1]) < min_chunk_size or len(piece) < min_chunk_size)
            and len(merged[-1]) + 1 + len(piece) <= chunk_size
        ):
            merged[-1] = merged[-1] + " " + piece
        else:
            merged.append(piece)

    # Apply overlap: prepend tail of previous chunk to current chunk
    chunks: list[Chunk] = []
    for i, piece in enumerate(merged):
        if i > 0 and chunk_overlap > 0:
            prev = merged[i - 1]
            overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            # Find word boundary in overlap
            space_idx = overlap_text.find(" ")
            if space_idx > 0:
                overlap_text = overlap_text[space_idx + 1 :]
            piece = overlap_text + " " + piece

        chunks.append(Chunk(text=piece.strip(), index=i))

    return chunks


def _recursive_split(text: str, chunk_size: int) -> list[str]:
    """Recursively split text using progressively finer separators."""
    if len(text) <= chunk_size:
        return [text]

    for sep in _SEPARATORS:
        if sep in text:
            pieces = _split_at_separator(text, sep)
            if len(pieces) > 1:
                result: list[str] = []
                current = ""
                for piece in pieces:
                    # Pieces already carry their trailing separator, so join with "".
                    candidate = current + piece
                    if len(candidate.strip()) <= chunk_size:
                        current = candidate
                    else:
                        if current.strip():
                            result.append(current.strip())
                        # If single piece exceeds chunk_size, recurse with next separator
                        if len(piece.strip()) > chunk_size:
                            result.extend(_recursive_split(piece, chunk_size))
                            current = ""
                        else:
                            current = piece
                if current.strip():
                    result.append(current.strip())
                return result

    # Last resort: hard split at chunk_size
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
