from app.utils.transcript import TranscriptEntry, build_chunks


def test_chunk_timestamps_match_source_entries(sample_entries):
    """Every chunk's start/end must come directly from real entry timestamps
    (not an estimated ratio), and must never exceed the transcript's bounds."""
    chunks = build_chunks(sample_entries, video_id="abc123", max_chars=80, overlap_entries=1)

    assert len(chunks) > 1

    valid_starts = {e.start for e in sample_entries}
    valid_ends = {round(e.start + e.duration, 2) for e in sample_entries}

    for chunk in chunks:
        assert chunk.metadata["video_id"] == "abc123"
        assert round(chunk.metadata["start"], 2) in valid_starts
        assert round(chunk.metadata["end"], 2) in valid_ends
        assert chunk.metadata["start"] < chunk.metadata["end"]
        assert chunk.metadata["start"] >= sample_entries[0].start
        assert chunk.metadata["end"] <= sample_entries[-1].start + sample_entries[-1].duration


def test_chunks_are_in_chronological_order(sample_entries):
    chunks = build_chunks(sample_entries, video_id="abc123", max_chars=80)
    starts = [c.metadata["start"] for c in chunks]
    assert starts == sorted(starts)


def test_single_long_entry_still_produces_a_chunk():
    entries = [TranscriptEntry(text="A" * 2000, start=10.0, duration=5.0)]
    chunks = build_chunks(entries, video_id="x", max_chars=100)
    assert len(chunks) == 1
    assert chunks[0].metadata["start"] == 10.0
    assert chunks[0].metadata["end"] == 15.0


def test_overlap_carries_real_timestamps_forward(sample_entries):
    chunks = build_chunks(sample_entries, video_id="abc123", max_chars=30, overlap_entries=1)
    # With overlap, consecutive chunks may share content, but the next chunk's
    # start must still be a genuine entry timestamp, not derived/interpolated.
    valid_starts = {e.start for e in sample_entries}
    for c in chunks:
        assert c.metadata["start"] in valid_starts
