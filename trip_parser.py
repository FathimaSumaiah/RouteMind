"""
trip_parser.py — Convert plain-English trip descriptions into structured Stop objects.

Two modes:
  1. Claude (Anthropic API)  — uses ANTHROPIC_API_KEY env var.
  2. Fallback regex parser   — no external calls; handles common patterns.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from solver import Stop


# ── time helpers ──────────────────────────────────────────────────────────────

_TIME_RE = re.compile(
    r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b',
    re.IGNORECASE,
)

def _parse_time(text: str) -> Optional[int]:
    """Return minutes-from-midnight or None."""
    m = _TIME_RE.search(text)
    if not m:
        return None
    h, mn, ampm = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or '').lower()
    if ampm == 'pm' and h != 12:
        h += 12
    elif ampm == 'am' and h == 12:
        h = 0
    return h * 60 + mn


# ── keyword extraction for time-window hints ─────────────────────────────────

def _extract_time_window(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Look for patterns like:
      "after 11am"   → earliest=11*60
      "before 1pm"   → latest=13*60
      "by 3pm"       → latest=15*60
      "at 9am"       → earliest = latest = 9*60
    """
    earliest = latest = None
    for pat, kind in [
        (r'after\s+' + _TIME_RE.pattern,       'earliest'),
        (r'from\s+'  + _TIME_RE.pattern,       'earliest'),
        (r'before\s+'+ _TIME_RE.pattern,       'latest'),
        (r'by\s+'    + _TIME_RE.pattern,       'latest'),
        (r'at\s+'    + _TIME_RE.pattern,       'exact'),
    ]:
        for m in re.finditer(pat, text, re.IGNORECASE):
            h  = int(m.group(1))
            mn = int(m.group(2) or 0)
            ap = (m.group(3) or '').lower()
            if ap == 'pm' and h != 12:
                h += 12
            elif ap == 'am' and h == 12:
                h = 0
            t = h * 60 + mn
            if kind == 'earliest':
                earliest = t
            elif kind == 'latest':
                latest = t
            elif kind == 'exact':
                earliest = latest = t
    return earliest, latest


# ── regex fallback parser ─────────────────────────────────────────────────────

_START_RE = re.compile(
    r'start(?:ing)?\s+(?:from|at)?\s+(.+?)(?:\s+at\s+\d|\s*[.,]|\s*$)',
    re.IGNORECASE,
)
_RETURN_RE = re.compile(r'return', re.IGNORECASE)


def _regex_parse(text: str) -> List[Dict[str, Any]]:
    """
    Best-effort extraction.  Returns a list of dicts:
      {name, earliest, latest, is_depot}
    """
    stops: List[Dict[str, Any]] = []

    # Detect start
    start_name = "Start"
    start_time = 9 * 60
    sm = _START_RE.search(text)
    if sm:
        start_name = sm.group(1).strip().rstrip('.,')
        t = _parse_time(text[:sm.end() + 20])
        if t is not None:
            start_time = t
    else:
        t = _parse_time(text.split('.')[0])
        if t is not None:
            start_time = t

    stops.append({'name': start_name, 'earliest': start_time,
                  'latest': start_time, 'is_depot': True})

    # Split on delimiters: ., ; and then look for named places
    # Simple heuristic: capitalised words not in stop-words
    STOPWORDS = {
        'start', 'starting', 'from', 'at', 'to', 'the', 'and',
        'deliver', 'visit', 'stop', 'go', 'then', 'after', 'before',
        'by', 'return', 'back', 'am', 'pm',
        # NOTE: single letters A, B, C intentionally omitted — valid as labels
    }

    # Pre-process: split on sentence ends AND commas that precede an uppercase
    # word/letter (handles "B after 11am, C by 1pm" style lists).
    raw_parts = re.split(r'[.;]+', text)
    parts: List[str] = []
    for rp in raw_parts:
        sub = re.split(r',\s*(?=[A-Z0-9])', rp)
        parts.extend(sub)

    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        if _RETURN_RE.search(part):
            continue   # return-to-depot is implicit

        # Try to find a place name: title-case sequence or ALL-CAPS
        name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z]{2,})\b', part)
        if not name_match:
            # single-letter labels like A, B, C
            name_match = re.search(r'\b([A-Z])\b', part)
        if not name_match:
            continue

        name = name_match.group(1)
        if name.lower() in STOPWORDS:
            continue

        earliest, latest = _extract_time_window(part)
        stops.append({'name': name, 'earliest': earliest,
                      'latest': latest, 'is_depot': False})

    return stops


# ── Claude parser ─────────────────────────────────────────────────────────────

_CLAUDE_PROMPT = """\
You are a trip-planning assistant. Extract all stops from the user's trip description.
Return ONLY valid JSON — a list of objects with these fields:
  name      : string (place name)
  earliest  : int or null  (open time, minutes from midnight)
  latest    : int or null  (deadline, minutes from midnight)
  is_depot  : bool  (true only for the first/last location the vehicle returns to)

Rules:
- "after X" → earliest = X, latest = null
- "by X" or "before X" → latest = X, earliest = null  
- "at X" → earliest = latest = X
- Return-to-start means is_depot=true already exists; do NOT add a second depot.
- Output the depot first in the list.
- No explanation, no markdown fences — raw JSON array only.
"""

def _claude_parse(text: str) -> Optional[List[Dict[str, Any]]]:
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=1024,
            messages=[
                {'role': 'user', 'content': _CLAUDE_PROMPT + '\n\nTrip: ' + text},
            ],
        )
        raw = msg.content[0].text.strip()
        # Strip accidental markdown fences
        raw = re.sub(r'^```[a-z]*\n?', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```$', '', raw, flags=re.MULTILINE)
        return json.loads(raw)
    except Exception as exc:
        print(f'[trip_parser] Claude API error: {exc}')
        return None


# ── public API ────────────────────────────────────────────────────────────────

def parse_trip(text: str, geocode_fn) -> Tuple[List[Stop], int, str]:
    """
    Returns (stops, start_time_minutes, parser_mode).

    geocode_fn(name: str) -> (lat, float) | None
    """
    # Try Claude first
    raw = _claude_parse(text)
    mode = 'claude' if raw else 'regex'
    if raw is None:
        raw = _regex_parse(text)

    # Determine start time from depot
    start_min = 9 * 60
    stops: List[Stop] = []

    for item in raw:
        name = item.get('name', 'Unknown')
        coords = geocode_fn(name)
        if coords is None:
            # Skip stops we can't locate
            print(f'[trip_parser] Could not geocode "{name}", skipping.')
            continue
        lat, lon = coords
        earliest = item.get('earliest')
        latest   = item.get('latest')
        if item.get('is_depot'):
            start_min = earliest if earliest is not None else 9 * 60
        stops.append(Stop(
            name=name,
            lat=lat,
            lon=lon,
            earliest=earliest,
            latest=latest,
        ))

    return stops, start_min, mode
