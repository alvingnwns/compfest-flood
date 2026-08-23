from __future__ import annotations


def routing_edge_record(
    *, source: int | str, target: int | str, segment_id: str, oneway: bool
) -> dict[str, str | bool]:
    """Build a compact routing edge without losing normalized OSMnx directionality."""
    return {
        "fromNode": str(source),
        "toNode": str(target),
        "segmentId": segment_id,
        "bidirectional": not bool(oneway),
    }
