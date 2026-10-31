"""
geocode.py — Lightweight geocoding with Nominatim + offline fallback.
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import requests

# ── Offline landmark data (Kozhikode, Kerala) ─────────────────────────────────
# Approximate coordinates. Used when network is unavailable.

_OFFLINE: Dict[str, Tuple[float, float]] = {
    # Kozhikode landmarks
    'railway station': (11.2588, 75.7804),
    'calicut railway station': (11.2588, 75.7804),
    'kozhikode railway station': (11.2588, 75.7804),
    'beach': (11.2494, 75.7711),
    'kozhikode beach': (11.2494, 75.7711),
    'mananchira': (11.2507, 75.7761),
    'medical college': (11.1333, 75.8019),
    'kozhikode medical college': (11.1333, 75.8019),
    'calicut university': (11.1352, 75.9415),
    'university': (11.1352, 75.9415),
    'mavoor road': (11.2615, 75.7890),
    'sm street': (11.2520, 75.7744),
    'sweet meat street': (11.2520, 75.7744),
    'palayam': (11.2501, 75.7803),
    'nadakkavu': (11.2711, 75.7755),
    'west hill': (11.2719, 75.7888),
    'feroke': (11.1767, 75.8260),
    'ramanattukara': (11.2098, 75.8196),
    'airport': (11.1368, 75.9526),
    'calicut airport': (11.1368, 75.9526),
    'kozhikode airport': (11.1368, 75.9526),
    'emu junction': (11.2638, 75.7853),
    'thondayad': (11.2838, 75.8016),
    'chevarambalam': (11.2912, 75.8193),
    'arayidathupalam': (11.2562, 75.7935),
    # Generic / other cities
    'delhi': (28.6139, 77.2090),
    'mumbai': (19.0760, 72.8777),
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'chennai': (13.0827, 80.2707),
    'hyderabad': (17.3850, 78.4867),
    'pune': (18.5204, 73.8567),
    'kochi': (9.9312, 76.2673),
    'cochin': (9.9312, 76.2673),
    'thrissur': (10.5276, 76.2144),
    'trivandrum': (8.5241, 76.9366),
    'thiruvananthapuram': (8.5241, 76.9366),
    'a': (11.2650, 75.7850),
    'b': (11.2550, 75.7950),
    'c': (11.2450, 75.8050),
    'd': (11.2750, 75.8150),
}

_cache: Dict[str, Optional[Tuple[float, float]]] = {}
_last_call: float = 0.0


def _nominatim(name: str) -> Optional[Tuple[float, float]]:
    """Call Nominatim with a 1-second rate limit."""
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_call = time.time()
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': name, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'RouteMind/1.0 (routemind-app)'},
            timeout=5,
        )
        data = resp.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as exc:
        print(f'[geocode] Nominatim error for "{name}": {exc}')
    return None


def geocode(name: str) -> Optional[Tuple[float, float]]:
    """
    Return (lat, lon) for a place name.
    Order: cache → offline table → Nominatim.
    """
    key = name.strip().lower()
    if key in _cache:
        return _cache[key]

    # Offline
    for k, v in _OFFLINE.items():
        if k in key or key in k:
            _cache[key] = v
            return v

    # Network
    result = _nominatim(name)
    _cache[key] = result
    return result
