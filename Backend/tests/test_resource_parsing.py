import pytest

from app.utils.resource import InvalidResourceError, parse_resource


@pytest.mark.parametrize(
    "raw,expected_type,expected_id",
    [
        ("dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=30", "video", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/playlist?list=PLabc123", "playlist", "PLabc123"),
        ("PLabc123def456", "playlist", "PLabc123def456"),
        # Regression test: an 11-char video ID that happens to start with "PL"
        # must still be classified as a VIDEO when there's no `list=` param.
        ("PLdQw4w9Wg1", "video", "PLdQw4w9Wg1"),
        # A watch URL that also carries a playlist context should resolve to
        # the playlist, since that's what "list=" means.
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc123", "playlist", "PLabc123"),
    ],
)
def test_parse_resource_valid(raw, expected_type, expected_id):
    resource_type, resource_id = parse_resource(raw)
    assert resource_type == expected_type
    assert resource_id == expected_id


@pytest.mark.parametrize("raw", ["", "   ", "not a url or id", "https://example.com/foo"])
def test_parse_resource_invalid(raw):
    with pytest.raises(InvalidResourceError):
        parse_resource(raw)
