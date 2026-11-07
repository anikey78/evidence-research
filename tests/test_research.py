from app.research import extract_response


def test_extracts_flat_citations_and_inline_spans() -> None:
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Fact [1].",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "start_index": 5,
                                "end_index": 8,
                                "url": "https://example.org/fact",
                                "title": "Example source",
                            }
                        ],
                    }
                ],
            }
        ]
    }

    result = extract_response(payload)

    assert result["answer"] == "Fact [1]."
    assert result["citations"] == [
        {"url": "https://example.org/fact", "title": "Example source"}
    ]
    assert result["citation_spans"] == [
        {
            "url": "https://example.org/fact",
            "title": "Example source",
            "start": 5,
            "end": 8,
        }
    ]
    assert result["refusal"] is False


def test_offsets_follow_joined_output_text_parts() -> None:
    citation = {
        "type": "url_citation",
        "start_index": 5,
        "end_index": 8,
        "url": "https://example.org/source",
        "title": "Example",
    }
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Fact [1].", "annotations": [citation]},
                    {"type": "output_text", "text": "More [2].", "annotations": [citation]},
                ],
            }
        ]
    }

    result = extract_response(payload)

    assert result["answer"] == "Fact [1].\nMore [2]."
    assert [(span["start"], span["end"]) for span in result["citation_spans"]] == [
        (5, 8),
        (15, 18),
    ]
    assert len(result["citations"]) == 1


def test_rejects_unsafe_citation_urls_and_bad_offsets() -> None:
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Claim [1].",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "start_index": 6,
                                "end_index": 9,
                                "url": "javascript:alert(1)",
                                "title": "Unsafe",
                            },
                            {
                                "type": "url_citation",
                                "start_index": None,
                                "end_index": "bad",
                                "url": "https://example.org/ok",
                                "title": "Bad annotation",
                            },
                        ],
                    }
                ],
            }
        ]
    }

    result = extract_response(payload)

    assert result["answer"] == "Claim [1]."
    assert result["citations"] == []
    assert result["citation_spans"] == []
