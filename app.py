#!/usr/bin/env python3
"""World Cup 2026 Sweepstakes — Flask Backend API"""
from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

DATA_FILE = Path(__file__).parent / "data" / "profiles.json"

POTS = {
    "Pot 1 – Top Seeds": ["United States", "Mexico", "Canada", "Spain", "Argentina", "France", "England", "Brazil", "Portugal", "Netherlands", "Belgium", "Germany"],
    "Pot 2 – Strong": ["Croatia", "Morocco", "Colombia", "Uruguay", "Switzerland", "Japan", "Senegal", "Iran", "South Korea", "Ecuador", "Austria", "Australia"],
    "Pot 3 – Competitive": ["Norway", "Panama", "Egypt", "Algeria", "Scotland", "Paraguay", "Tunisia", "Ivory Coast", "Uzbekistan", "Qatar", "Saudi Arabia", "South Africa"],
    "Pot 4 – Underdogs": ["Jordan", "Cape Verde", "Ghana", "Curaçao", "Haiti", "New Zealand", "Bosnia and Herzegovina", "Czech Republic", "Sweden", "Turkey", "DR Congo", "Iraq"],
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
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}


def save_profiles(profiles: dict):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(profiles, indent=2))


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
    profiles = load_profiles()
    if name not in profiles:
        return jsonify({"error": "Not found"}), 404
    return jsonify(profiles[name])


@app.route("/api/profiles/<name>", methods=["DELETE"])
def delete_profile(name):
    err = require_admin()
    if err: return err
    profiles = load_profiles()
    if name not in profiles:
        return jsonify({"error": "Not found"}), 404
    del profiles[name]
    save_profiles(profiles)
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

    profiles = load_profiles()
    profiles[name] = profile
    save_profiles(profiles)
    return jsonify(profile)


@app.route("/api/profiles/<name>/prizes", methods=["POST"])
def update_prizes(name):
    profiles = load_profiles()
    if name not in profiles:
        return jsonify({"error": "Not found"}), 404
    data = request.json  # {"prizeIndex": 0, "team": "Argentina"} or {"team": ""} to clear
    idx = str(data.get("prizeIndex"))
    team = data.get("team", "").strip()
    if team:
        profiles[name]["prizeWinners"][idx] = team
    else:
        profiles[name]["prizeWinners"].pop(idx, None)
    save_profiles(profiles)
    return jsonify(profiles[name])


if __name__ == "__main__":
    app.run(debug=True, port=5050)
