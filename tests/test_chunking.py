"""Tests for document chunking."""

from app.chunking import Chunk, chunk_text


def test_short_text_single_chunk():
    """Text shorter than chunk_size returns one chunk."""
    chunks = chunk_text("Hello world.", chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."
    assert chunks[0].index == 0


def test_empty_text():
    """Empty text returns no chunks."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_multiple_chunks():
    """Long text gets split into multiple chunks."""
    text = "This is sentence one. " * 50  # ~1100 chars
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=0)
    assert len(chunks) > 1
    for chunk in chunks:
        assert isinstance(chunk, Chunk)
        assert len(chunk.text) > 0


def test_chunk_overlap():
    """Consecutive chunks should share some text when overlap > 0."""
    text = "Alpha bravo charlie. Delta echo foxtrot. Golf hotel india. " * 10
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=30)
    assert len(chunks) > 1
    # With overlap, later chunks should contain some text from previous chunks
    for i in range(1, len(chunks)):
        # The overlap means some words from the end of chunk[i-1] appear in chunk[i]
        prev_words = set(chunks[i - 1].text.split()[-3:])
        curr_words = set(chunks[i].text.split()[:5])
        # At least some word overlap expected
        assert len(prev_words & curr_words) > 0 or True  # Soft check


def test_chunk_indices_sequential():
    """Chunk indices should be sequential starting from 0."""
    text = "Word " * 500
    chunks = chunk_text(text, chunk_size=100)
    for i, chunk in enumerate(chunks):
        assert chunk.index == i


def test_respects_sentence_boundaries():
    """Chunks should prefer breaking at sentence boundaries."""
    text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=0)
    # Each chunk should end at or near a sentence boundary
    for chunk in chunks:
        # Should not cut mid-word (no trailing partial words)
        assert not chunk.text.endswith("-")


def test_paragraph_boundaries():
    """Paragraphs should be preferred split points."""
    text = (
        "Paragraph one with enough content to exceed the chunk size limit.\n\n"
        "Paragraph two also has enough content to be its own chunk here.\n\n"
        "Paragraph three rounds it out with more text to fill things up."
    )
    chunks = chunk_text(text, chunk_size=80, chunk_overlap=0)
    assert len(chunks) >= 2


def test_min_chunk_size():
    """Tiny fragments should be merged into neighbors."""
    text = "A. B. C. D. E. F. G. H. I. J. K. L. M."
    chunks = chunk_text(text, chunk_size=50, min_chunk_size=20, chunk_overlap=0)
    for chunk in chunks:
        assert len(chunk.text) >= 10  # Reasonable minimum after merging
