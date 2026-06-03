# ⚽ FIFA World Cup 2026 Sweepstakes Generator

A fair team draw and prize tracker for office/friend group sweepstakes. Python Flask backend with a browser-based frontend.

## How It Works

- **48 teams** split into **4 pots of 12** (matching the official FIFA draw seedings)
- **2–12 players** supported with fair distribution (max 1 team difference between any two players)
- **8 prize categories** that split **100% of the pot** based on weighted percentages
- **Buy-in system** — enter amount per person, see actual £ winnings per category
- **Save profiles** — come back throughout the tournament to track results

## Prize Categories

| % of Pot | Category | Definition |
|----------|----------|------------|
| 35% | 🏆 World Cup Winner | Team that wins the final |
| 15% | 🥈 Runner-Up | Team that loses the final |
| 10% | 🥉 Third Place | Team that wins the 3rd-place match |
| 10% | 🟥 Most Red Cards | Team that receives the most red cards across all their matches |
| 10% | 🟨 Most Yellow Cards (Group Stage) | Team that receives the most yellow cards during the group stage |
| 10% | 😵 Most Goals Conceded (Group Stage) | Team that concedes the most goals during the group stage |
| 5% | 💨 Fastest Goal | Team that scores the earliest goal (fewest minutes) in any single match |
| 5% | ⏱️ Latest Goal | Team that scores the latest goal within 90 mins (excluding extra time) in any single match |

## Quick Start

```bash
# Install Flask
pip install flask

# Run the server
cd worldcup-sweepstakes
python3 app.py

# Open in browser
open http://localhost:5050
```

## Usage

1. Enter a **profile name** (e.g. "Office Sweepstakes 2026")
2. Enter **player names** (comma-separated)
3. Enter **buy-in per person** (e.g. £10)
4. Hit **Draw & Save** — teams are randomly assigned from each pot
5. As the tournament progresses, assign winning teams to each prize category
6. The **leaderboard** updates automatically showing % of pot and £ winnings

## Project Structure

```
worldcup-sweepstakes/
├── app.py              # Flask backend (API + serves frontend)
├── static/
│   └── index.html      # Browser frontend
├── data/
│   └── profiles.json   # Auto-created, persists all saved profiles
└── README.md
```

## API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/pots` | Get seeded pots |
| GET | `/api/prizes` | Get prize categories with % and descriptions |
| GET | `/api/profiles` | List saved profiles |
| GET | `/api/profiles/<name>` | Get a specific profile |
| POST | `/api/draw` | Create draw and save profile |
| POST | `/api/profiles/<name>/prizes` | Assign a prize winner |
| DELETE | `/api/profiles/<name>` | Delete a profile |

## Team Distribution

| Players | Teams each |
|---------|-----------|
| 2 | 24 |
| 3 | 16 |
| 4 | 12 |
| 5 | 9–10 |
| 6 | 8 |
| 7 | 6–7 |
| 8 | 6 |
| 9 | 5–6 |
| 10 | 4–5 |
| 11 | 4–5 |
| 12 | 4 |

When teams don't divide evenly, remainder teams are distributed using a fairness algorithm that ensures no player gets more than 1 extra team compared to anyone else.
