"""
solver.py — Held-Karp TSP with time windows.

Nodes are 0-indexed.  Node 0 is always the depot/start.
Time is measured in minutes from midnight.

A stop has:
    name        str
    lat, lon    float
    earliest    int | None   (open time, minutes from midnight)
    latest      int | None   (deadline, minutes from midnight)

If arrival is before earliest the vehicle *waits* until earliest.
If arrival is after latest the stop is considered infeasible but we
still return the best we found (flagged).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

# ── data structures ──────────────────────────────────────────────────────────

@dataclass
class Stop:
    name: str
    lat: float
    lon: float
    earliest: Optional[int] = None   # minutes from midnight
    latest:   Optional[int] = None   # minutes from midnight
    duration: int = 10               # service time at stop, minutes


@dataclass
class RouteStep:
    stop: Stop
    arrival_min: int      # minutes from midnight
    wait_min: int         # waited at this stop
    depart_min: int       # = arrival + wait + duration
    travel_min: int       # travel from previous stop


@dataclass
class Solution:
    order: List[int]          # indices into stops list (0 = depot)
    steps: List[RouteStep]
    total_distance_km: float
    feasible: bool            # False if any time-window violated


# ── distance helpers ─────────────────────────────────────────────────────────

def _haversine(a: Stop, b: Stop) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def _travel_minutes(a: Stop, b: Stop, speed_kmh: float = 30.0) -> int:
    """Estimated travel time in minutes (straight-line × 1.3 detour factor)."""
    dist = _haversine(a, b) * 1.3
    return max(1, int(dist / speed_kmh * 60))


# ── Held-Karp ────────────────────────────────────────────────────────────────

def _held_karp(stops: List[Stop], depot_idx: int, start_min: int) -> Solution:
    """
    Exact TSP-with-time-windows via bitmask DP.
    Works for up to ~20 stops (2^20 states × n).

    dp[mask][i] = (earliest_finish_time, parent_mask, parent_node)
    mask bit j is set when stop j has been visited.
    We always start and end at depot_idx.
    """
    n = len(stops)
    if n == 0:
        return Solution([], [], 0.0, True)

    INF = 10 ** 9
    full = (1 << n) - 1

    # Pre-compute travel times
    tm = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            tm[i][j] = _travel_minutes(stops[i], stops[j])

    # dp[mask][i] = (time when we finish stop i having visited mask, prev_mask, prev_i)
    dp   = [[(INF, -1, -1)] * n for _ in range(1 << n)]
    dep0 = start_min + stops[depot_idx].duration
    dp[1 << depot_idx][depot_idx] = (dep0, -1, -1)

    for mask in range(1 << n):
        for i in range(n):
            if not (mask >> i & 1):
                continue
            cur_time, _, _ = dp[mask][i]
            if cur_time == INF:
                continue
            for j in range(n):
                if mask >> j & 1:
                    continue
                arr = cur_time + tm[i][j]
                wait = max(0, (stops[j].earliest or 0) - arr)
                depart = arr + wait + stops[j].duration
                new_mask = mask | (1 << j)
                if depart < dp[new_mask][j][0]:
                    dp[new_mask][j] = (depart, mask, i)

    # Find best finishing node (return to depot)
    best_time = INF
    best_last = -1
    for i in range(n):
        if i == depot_idx:
            continue
        if not (full >> i & 1):
            continue
        t, _, _ = dp[full][i]
        if t == INF:
            continue
        total = t + tm[i][depot_idx]
        if total < best_time:
            best_time = total
            best_last = i

    if best_last == -1:
        # Only one stop (the depot itself)
        order = [depot_idx]
    else:
        # Backtrack
        order = []
        mask = full
        cur = best_last
        while cur != -1:
            order.append(cur)
            _, prev_mask, prev_node = dp[mask][cur]
            mask = prev_mask
            cur = prev_node
        order.reverse()

    # Build RouteStep list
    steps: List[RouteStep] = []
    feasible = True
    cur_time = start_min
    prev_stop = stops[order[0]]

    for idx, si in enumerate(order):
        s = stops[si]
        if idx == 0:
            arr = start_min
            travel = 0
        else:
            travel = tm[order[idx - 1]][si]
            arr = cur_time + travel

        wait = max(0, (s.earliest or 0) - arr)
        depart = arr + wait + s.duration
        cur_time = depart

        if s.latest is not None and arr > s.latest:
            feasible = False

        steps.append(RouteStep(
            stop=s,
            arrival_min=arr,
            wait_min=wait,
            depart_min=depart,
            travel_min=travel,
        ))

    # Add return leg
    if len(order) > 1:
        last = stops[order[-1]]
        ret_travel = tm[order[-1]][depot_idx]
        ret_arr = cur_time + ret_travel
        steps.append(RouteStep(
            stop=stops[depot_idx],
            arrival_min=ret_arr,
            wait_min=0,
            depart_min=ret_arr,
            travel_min=ret_travel,
        ))

    total_km = sum(
        _haversine(stops[order[i]], stops[order[i + 1]]) * 1.3
        for i in range(len(order) - 1)
    )
    if len(order) > 1:
        total_km += _haversine(stops[order[-1]], stops[depot_idx]) * 1.3

    return Solution(order=order, steps=steps, total_distance_km=round(total_km, 2), feasible=feasible)


# ── public API ────────────────────────────────────────────────────────────────

def plan_route(stops: List[Stop], start_time_min: int = 9 * 60) -> Solution:
    """
    Plan the best route visiting all stops starting from stops[0] (depot).
    Returns to depot at the end.
    """
    if len(stops) == 0:
        return Solution([], [], 0.0, True)
    if len(stops) == 1:
        s = stops[0]
        step = RouteStep(stop=s, arrival_min=start_time_min, wait_min=0,
                         depart_min=start_time_min + s.duration, travel_min=0)
        return Solution([0], [step], 0.0, True)

    return _held_karp(stops, depot_idx=0, start_min=start_time_min)
