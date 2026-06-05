#!/usr/bin/env python3
"""World Cup 2026 Sweepstakes — Flask Backend API"""
from __future__ import annotations

import json
import os
import random
from collections import defaultdict

import requests as http_client
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
TURSO_URL = os.environ.get("TURSO_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")


# --- Turso DB ---
def _turso(statements):
    url = TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    reqs = [{"type": "execute", "stmt": s} for s in statements] + [{"type": "close"}]
    r = http_client.post(url, headers=headers, json={"requests": reqs})
    return r.json()["results"]


def init_db():
    _turso([{"sql": "CREATE TABLE IF NOT EXISTS profiles (name TEXT PRIMARY KEY, data TEXT NOT NULL)"}])


init_db()

POTS = {
    "Pot 1 – Top Seeds": ["France", "Spain", "Argentina", "England", "Portugal", "Brazil", "Netherlands", "Morocco", "Belgium", "Germany", "Croatia", "Colombia"],
    "Pot 2 – Strong": ["Senegal", "Mexico", "United States", "Uruguay", "Japan", "Switzerland", "Iran", "Austria", "South Korea", "Ecuador", "Australia", "Egypt"],
    "Pot 3 – Competitive": ["Canada", "Ivory Coast", "Qatar", "Algeria", "Sweden", "Tunisia", "Czech Republic", "Turkey", "Norway", "Scotland", "DR Congo", "Bosnia and Herzegovina"],
    "Pot 4 – Underdogs": ["Panama", "Saudi Arabia", "South Africa", "Iraq", "Uzbekistan", "Paraguay", "Ghana", "Jordan", "Cape Verde", "Curaçao", "Haiti", "New Zealand"],
}

PRIZES = [
    ("🏆 World Cup Winner", "Team that wins the final", 35),
    ("🥈 Runner-Up", "Team that loses the final", 15),
    ("🥉 Third Place", "Team that wins the 3rd-place match", 10),
    ("🟥 Most Red Cards", "Team that receives the most red cards across all their matches", 10),
    ("🟨 Most Yellow Cards (Group Stage)", "Team that receives the most yellow cards during the group stage", 10),
    ("😵 Most Goals Conceded (Group Stage)", "Team that concedes the most goals during the group stage", 10),
    ("💨 Fastest Goal", "Team that scores the earliest goal (fewest minutes) in any single match of the tournament", 5),
    ("⏱️ Latest Goal", "Team that scores the latest goal within 90 minutes (excluding extra time) in any single match of the tournament", 5),
]


# --- Auth ---
def require_admin():
    pw = request.headers.get("X-Admin-Password", "")
    if pw != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    return None


# --- Data persistence ---
def load_profiles() -> dict:
    results = _turso([{"sql": "SELECT name, data FROM profiles"}])
    rows = results[0]["response"]["result"]["rows"]
    return {row[0]["value"]: json.loads(row[1]["value"]) for row in rows}


def load_profile(name: str):
    results = _turso([{"sql": "SELECT data FROM profiles WHERE name = ?", "args": [{"type": "text", "value": name}]}])
    rows = results[0]["response"]["result"]["rows"]
    return json.loads(rows[0][0]["value"]) if rows else None


def save_profile(name: str, profile: dict):
    _turso([{"sql": "INSERT OR REPLACE INTO profiles (name, data) VALUES (?, ?)", "args": [{"type": "text", "value": name}, {"type": "text", "value": json.dumps(profile)}]}])


def delete_profile_db(name: str):
    _turso([{"sql": "DELETE FROM profiles WHERE name = ?", "args": [{"type": "text", "value": name}]}])


# --- Draw logic ---
def perform_draw(players: list[str]) -> dict:
    num_players = len(players)
    allocation = {p: [] for p in players}
    bonus_count = defaultdict(int)

    for pot_idx, (pot_name, teams) in enumerate(POTS.items()):
        pot_size = len(teams)
        base = pot_size // num_players
        remainder = pot_size % num_players
        shuffled = teams[:]
        random.shuffle(shuffled)
        idx = 0
        for player in players:
            for _ in range(base):
                allocation[player].append({"team": shuffled[idx], "pot": pot_idx + 1})
                idx += 1
        if remainder > 0:
            sorted_players = sorted(players, key=lambda p: (bonus_count[p], random.random()))
            for player in sorted_players[:remainder]:
                allocation[player].append({"team": shuffled[idx], "pot": pot_idx + 1})
                bonus_count[player] += 1
                idx += 1
    return allocation


# --- Routes ---
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/pots")
def get_pots():
    return jsonify(POTS)


@app.route("/api/prizes")
def get_prizes():
    return jsonify([{"name": name, "description": desc, "pct": pct} for name, desc, pct in PRIZES])


@app.route("/api/profiles", methods=["GET"])
def list_profiles():
    profiles = load_profiles()
    return jsonify({name: {"players": p["players"], "createdAt": p.get("createdAt", "")} for name, p in profiles.items()})


@app.route("/api/profiles/<name>", methods=["GET"])
def get_profile(name):
    profile = load_profile(name)
    if not profile:
        return jsonify({"error": "Not found"}), 404
    return jsonify(profile)


@app.route("/api/profiles/<name>", methods=["DELETE"])
def delete_profile(name):
    err = require_admin()
    if err: return err
    profile = load_profile(name)
    if not profile:
        return jsonify({"error": "Not found"}), 404
    delete_profile_db(name)
    return jsonify({"ok": True})


@app.route("/api/draw", methods=["POST"])
def draw():
    err = require_admin()
    if err: return err
    data = request.json
    name = data.get("name", "").strip()
    players = [p.strip() for p in data.get("players", []) if p.strip()]

    if not name:
        return jsonify({"error": "Profile name required"}), 400
    if len(players) < 2:
        return jsonify({"error": "Need at least 2 players"}), 400
    if len(players) > 12:
        return jsonify({"error": "Max 12 players"}), 400

    allocation = perform_draw(players)
    buy_in = data.get("buyIn", 0)
    profile = {"players": players, "allocation": allocation, "prizeWinners": {}, "buyIn": buy_in, "createdAt": __import__("datetime").datetime.now().isoformat()}

    save_profile(name, profile)
    return jsonify(profile)


@app.route("/api/profiles/<name>/prizes", methods=["POST"])
def update_prizes(name):
    profile = load_profile(name)
    if not profile:
        return jsonify({"error": "Not found"}), 404
    data = request.json
    idx = str(data.get("prizeIndex"))
    team = data.get("team", "").strip()
    if team:
        profile["prizeWinners"][idx] = team
    else:
        profile["prizeWinners"].pop(idx, None)
    save_profile(name, profile)
    return jsonify(profile)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
