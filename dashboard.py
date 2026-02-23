#!/usr/bin/env python3
import json
import os
from urllib.parse import unquote

from flask import Flask, jsonify, render_template, request

import database

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

app = Flask(__name__)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


@app.route("/")
def index():
    config = load_config()
    return render_template("index.html", sites=config["sites"])


@app.route("/api/status")
def api_status():
    config = load_config()
    results = []
    for site in config["sites"]:
        url = site["url"]
        current = database.get_current_status(url)
        results.append({
            "name": site.get("name", url),
            "url": url,
            "is_up": bool(current["is_up"]) if current else None,
            "status_code": current["status_code"] if current else None,
            "response_time_ms": current["response_time_ms"] if current else None,
            "last_check": current["checked_at"] if current else None,
            "uptime_24h": database.get_uptime_percent(url, 24),
            "uptime_7d": database.get_uptime_percent(url, 168),
            "uptime_30d": database.get_uptime_percent(url, 720),
        })
    return jsonify(results)


@app.route("/api/response-times/<path:url_encoded>")
def api_response_times(url_encoded):
    url = unquote(url_encoded)
    hours = request.args.get("hours", 24, type=int)
    data = database.get_response_times(url, hours)
    return jsonify(data)


@app.route("/api/events")
def api_events():
    limit = request.args.get("limit", 20, type=int)
    events = database.get_recent_events(limit)
    return jsonify(events)


if __name__ == "__main__":
    database.init_db()
    app.run(host="0.0.0.0", port=5000)
