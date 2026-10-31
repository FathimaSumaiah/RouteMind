"""
app.py — RouteMind Flask application.
"""

from __future__ import annotations

import json
import os

from flask import Flask, jsonify, render_template, request

from geocode import geocode
from solver import plan_route
from trip_parser import parse_trip

app = Flask(__name__)


def _fmt_time(minutes: int) -> str:
    """Convert minutes-from-midnight to HH:MM AM/PM."""
    h, m = divmod(minutes, 60)
    h = h % 24
    ampm = 'AM' if h < 12 else 'PM'
    h12 = h % 12 or 12
    return f'{h12}:{m:02d} {ampm}'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/plan', methods=['POST'])
def plan():
    data = request.get_json(force=True)
    text = (data.get('trip') or '').strip()

    if not text:
        return jsonify({'error': 'No trip text provided.'}), 400

    try:
        stops, start_min, mode = parse_trip(text, geocode)
    except Exception as exc:
        return jsonify({'error': f'Parsing failed: {exc}'}), 500

    if len(stops) < 1:
        return jsonify({'error': 'Could not identify any stops. Try adding city/landmark names.'}), 400

    if len(stops) < 2:
        return jsonify({'error': 'Need at least 2 stops (start + one destination).'}), 400

    try:
        solution = plan_route(stops, start_time_min=start_min)
    except Exception as exc:
        return jsonify({'error': f'Solver failed: {exc}'}), 500

    # Build response
    waypoints = []
    for step in solution.steps:
        s = step.stop
        waypoints.append({
            'name': s.name,
            'lat': s.lat,
            'lon': s.lon,
            'arrival': _fmt_time(step.arrival_min),
            'wait': step.wait_min,
            'depart': _fmt_time(step.depart_min),
            'travel_min': step.travel_min,
        })

    return jsonify({
        'waypoints': waypoints,
        'total_km': solution.total_distance_km,
        'feasible': solution.feasible,
        'mode': mode,
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
