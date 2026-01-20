from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

@dataclass
class Player:
    user_id: int
    cls: Optional[str] = None

@dataclass
class Team:
    id: int
    players: Tuple[Player, Player]
    eliminated: bool = False
    eliminated_round: Optional[int] = None

@dataclass
class Match:
    id: int
    round_no: int
    team1_id: int
    team2_id: int
    date_str: str
    time_str: str
    channel_id: int
    created_message_id: Optional[int] = None  # embed match message id
    map_name: Optional[str] = None
    map_image: Optional[str] = None
    status: str = "WAITING_AVAIL"  # WAITING_AVAIL / NEED_ORGA_VALIDATE / VALIDATED / DONE
    thumbs: Set[int] = field(default_factory=set)
    winner_team_id: Optional[int] = None

@dataclass
class EmbedsState:
    players_msg_id: Optional[int] = None
    teams_msg_id: Optional[int] = None
    upcoming_msg_id: Optional[int] = None
    history_msg_id: Optional[int] = None

@dataclass
class TournamentState:
    # Lobby
    players: List[Player] = field(default_factory=list)

    # Tournament
    teams: List[Team] = field(default_factory=list)
    matches: List[Match] = field(default_factory=list)
    current_round: int = 0

    # Embed messages in the main embeds channel
    embeds: EmbedsState = field(default_factory=EmbedsState)

    def reset(self):
        self.players.clear()
        self.teams.clear()
        self.matches.clear()
        self.current_round = 0
        self.embeds = EmbedsState()

STATE = TournamentState()