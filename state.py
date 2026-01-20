class TournamentState:
    def __init__(self):
        self.players = []
        self.teams = []
        self.matches = []
        self.embeds = {
            "players": None,
            "teams": None,
            "upcoming": None,
        }

STATE = TournamentState()