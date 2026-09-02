from __future__ import annotations

import html as htmlmod
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def extract_caption_tracks(page: str) -> list[dict]:
    match = re.search(r'"captionTracks":(\[.*?\])', page)
    if not match:
        return []
    return json.loads(match.group(1))


def parse_caption_payload(payload: str) -> str:
    if payload.lstrip().startswith("{"):
        data = json.loads(payload)
        parts: list[str] = []
        for event in data.get("events", []):
            for segment in event.get("segs", []):
                parts.append(segment.get("utf8", ""))
        return "".join(parts)

    root = ET.fromstring(payload)
    parts = [htmlmod.unescape("".join(elem.itertext())) for elem in root.iter("text")]
    return " ".join(parts)


def with_query_param(url: str, key: str, value: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
    )


def main() -> int:
    video_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=EP1GtsZ2VfM"
    page = fetch_text(video_url)
    tracks = extract_caption_tracks(page)
    print(f"caption_tracks_found={bool(tracks)}")
    for track in tracks[:5]:
        name = track.get("name", {}).get("simpleText", "")
        print(f"track={track.get('languageCode', '?')} kind={track.get('kind', '')} name={name}")

    if not tracks:
        return 2

    if "--diagnose" in sys.argv:
        track = tracks[0].copy()
        base_url = track.pop("baseUrl", "")
        print(json.dumps(track, ensure_ascii=False, indent=2))
        split = urllib.parse.urlsplit(base_url)
        print(f"caption_host={split.netloc}")
        print(f"caption_path={split.path}")
        print(
            "caption_query_keys="
            + ",".join(key for key, _ in urllib.parse.parse_qsl(split.query, keep_blank_values=True))
        )
        print(f"caption_url_start={base_url[:500]}")

    caption_url = with_query_param(tracks[0]["baseUrl"], "fmt", "json3")
    payload = fetch_text(caption_url)
    print(f"caption_payload_chars={len(payload)}")
    if not payload.strip():
        print("caption_payload_empty=true")
        return 3
    transcript = re.sub(r"\s+", " ", parse_caption_payload(payload)).strip()
    print(f"transcript_chars={len(transcript)}")
    print(transcript[:16000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
