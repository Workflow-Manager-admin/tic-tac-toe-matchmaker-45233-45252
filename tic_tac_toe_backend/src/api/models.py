"""Models and business logic for Tic Tac Toe backend."""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal, Dict
import uuid
import hashlib
from datetime import datetime

# In-memory stores (to be replaced with database in production)
USERS: Dict[str, "UserInDB"] = {}
GAMES: Dict[str, "Game"] = {}
MATCH_HISTORY: List["MatchHistoryRecord"] = []

# Helpers for password hashing (demo purposes)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# User schema for API
class UserBase(BaseModel):
    username: str = Field(..., description="Unique user name")
    email: EmailStr = Field(..., description="User email")

class UserCreate(UserBase):
    password: str = Field(..., min_length=4, description="Password")

class UserLogin(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

class UserPublic(UserBase):
    id: str

class UserInDB(UserBase):
    hashed_password: str
    id: str

    @classmethod
    def create(cls, username: str, email: str, password: str) -> "UserInDB":
        return cls(
            username=username,
            email=email,
            id=str(uuid.uuid4()),
            hashed_password=hash_password(password),
        )

# Board cell type: 'X', 'O', or ''
Cell = Literal['X', 'O', '']

class GameState(BaseModel):
    board: List[List[Cell]]
    current_player: Cell = Field(..., description="'X' or 'O'")
    status: Literal["active", "finished", "waiting"]
    winner: Optional[Cell] = None

class GameCreate(BaseModel):
    opponent: Literal["player", "ai"]
    player_symbol: Optional[Cell] = "X"

class GameMove(BaseModel):
    row: int = Field(..., ge=0, le=2)
    col: int = Field(..., ge=0, le=2)
    player: Cell

class Game(BaseModel):
    id: str
    state: GameState
    player_x: str
    player_o: str
    start_time: datetime
    moves: List[GameMove]
    is_vs_ai: bool

class MatchHistoryRecord(BaseModel):
    game_id: str
    player_x: str
    player_o: str
    winner: Optional[str]
    moves: List[GameMove]
    finished_at: datetime

class LeaderboardEntry(BaseModel):
    username: str
    wins: int
    losses: int
    draws: int

def create_new_game(player_x: str, opponent_type: str, player_symbol: Cell) -> Game:
    if opponent_type == "ai":
        player_x_name = player_x if player_symbol == "X" else "AI_BOT"
        return Game(
            id=str(uuid.uuid4()),
            state=GameState(
                board=[['', '', ''], ['', '', ''], ['', '', '']],
                current_player='X',
                status="active",
            ),
            player_x=player_x_name,
            player_o="AI_BOT" if player_x_name == player_x else player_x,
            start_time=datetime.utcnow(),
            moves=[],
            is_vs_ai=True,
        )
    else:
        return Game(
            id=str(uuid.uuid4()),
            state=GameState(
                board=[['', '', ''], ['', '', ''], ['', '', '']],
                current_player='X',
                status="waiting",
            ),
            player_x=player_x,
            player_o="",
            start_time=datetime.utcnow(),
            moves=[],
            is_vs_ai=False,
        )

def check_winner(board: List[List[Cell]]) -> Optional[Cell]:
    """Check winner for the given board."""
    lines = board + [list(col) for col in zip(*board)]
    lines.append([board[i][i] for i in range(3)])
    lines.append([board[i][2-i] for i in range(3)])
    for line in lines:
        if line[0] != '' and all(cell == line[0] for cell in line):
            return line[0]
    return None

def is_draw(board: List[List[Cell]]) -> bool:
    return all(cell != '' for row in board for cell in row)

def ai_move(board: List[List[Cell]], symbol: Cell) -> (int, int):
    """Very basic AI: first available spot."""
    for i in range(3):
        for j in range(3):
            if board[i][j] == '':
                return (i, j)
    raise Exception("No empty cells!")

def record_match_result(game: Game):
    MATCH_HISTORY.append(
        MatchHistoryRecord(
            game_id=game.id,
            player_x=game.player_x,
            player_o=game.player_o,
            winner=game.state.winner,
            moves=game.moves,
            finished_at=datetime.utcnow(),
        )
    )

def get_leaderboard() -> List[LeaderboardEntry]:
    stats = {}
    for user in USERS.values():
        stats[user.username] = {"wins": 0, "losses": 0, "draws": 0}
    for record in MATCH_HISTORY:
        px = record.player_x
        po = record.player_o
        if record.winner == "X":
            stats[px]["wins"] += 1
            stats[po]["losses"] += 1
        elif record.winner == "O":
            stats[px]["losses"] += 1
            stats[po]["wins"] += 1
        else:
            stats[px]["draws"] += 1
            stats[po]["draws"] += 1
    leaderboard = [
        LeaderboardEntry(username=username, **stat) for username, stat in stats.items()
    ]
    leaderboard.sort(key=lambda e: e.wins, reverse=True)
    return leaderboard
