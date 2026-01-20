import json
import os

DATA_FILE = "tournoi.json"


def default_data():
    return {
        "phase": "players",
        "embeds": {
            "players": None,
            "teams": None,
            "upcoming": None,
            "history": None,
        },
        "players": [],
        "teams": [],
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        data = default_data()
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
