"""API routers for user, game, leaderboard, history, and websocket for Tic Tac Toe."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List
from .models import (
    UserCreate, UserLogin, UserPublic, UserInDB, USERS,
    GameCreate, GameMove, Game, GAMES, create_new_game,
    check_winner, is_draw, ai_move, record_match_result,
    get_leaderboard, MATCH_HISTORY
)

router = APIRouter()
active_connections = {}

# PUBLIC_INTERFACE
@router.post("/register", response_model=UserPublic, tags=["auth"], summary="Register new user")
async def register(user: UserCreate):
    """Register a new user."""
    if user.username in USERS:
        raise HTTPException(status_code=400, detail="Username already registered")
    for existing in USERS.values():
        if existing.email == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    user_db = UserInDB.create(user.username, user.email, user.password)
    USERS[user_db.username] = user_db
    return UserPublic(id=user_db.id, username=user_db.username, email=user_db.email)

# PUBLIC_INTERFACE
@router.post("/login", response_model=UserPublic, tags=["auth"], summary="Login existing user")
async def login(login: UserLogin):
    """Login a user (username or email)."""
    for user in USERS.values():
        if user.username == login.username or user.email == login.username:
            if user.hashed_password == user.hashed_password.__class__(login.password):
                # <- not right, we'll fix below
                pass
            if user.hashed_password == user.hashed_password:
                # Placeholder. Fix logic
                pass
    # Real check:
    user = USERS.get(login.username)
    if user and user.hashed_password and user.hashed_password == user.hashed_password.__class__(login.password):
        pass  # Placeholder
    # Fix for demo:
    user = None
    for u in USERS.values():
        if (u.username == login.username or u.email == login.username) and u.hashed_password:
            from .models import verify_password
            if verify_password(login.password, u.hashed_password):
                user = u
                break
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return UserPublic(id=user.id, username=user.username, email=user.email)

# PUBLIC_INTERFACE
@router.post("/games/start", response_model=Game, tags=["games"], summary="Start a new game")
async def start_game(game: GameCreate, player: str):
    """
    Start a new Tic Tac Toe game.
    - opponent: 'player' or 'ai'
    - player_symbol: 'X' or 'O' (optional, default X)
    """
    new_game = create_new_game(player, game.opponent, game.player_symbol)
    GAMES[new_game.id] = new_game
    return new_game

# PUBLIC_INTERFACE
@router.post("/games/move", response_model=Game, tags=["games"], summary="Make a move in a game")
async def game_move(game_id: str, move: GameMove):
    """
    Make a move in the Tic Tac Toe game.
    """
    game = GAMES.get(game_id)
    if not game or game.state.status != "active":
        raise HTTPException(status_code=404, detail="Game not found or inactive")
    board = game.state.board

    if board[move.row][move.col] != '':
        raise HTTPException(status_code=400, detail="Cell already occupied")
    if game.state.current_player != move.player:
        raise HTTPException(status_code=400, detail="Not your turn")

    board[move.row][move.col] = move.player
    game.moves.append(move)
    winner = check_winner(board)
    if winner:
        game.state.status = "finished"
        game.state.winner = winner
        record_match_result(game)
    elif is_draw(board):
        game.state.status = "finished"
        game.state.winner = None
        record_match_result(game)
    else:
        next_player = "O" if move.player == "X" else "X"
        game.state.current_player = next_player
        # If vs AI and next_player is AI, make AI move
        if game.is_vs_ai and ((next_player == "O" and game.player_o == "AI_BOT") or (next_player == "X" and game.player_x == "AI_BOT")):
            ai_r, ai_c = ai_move(board, next_player)
            board[ai_r][ai_c] = next_player
            game.moves.append(GameMove(row=ai_r, col=ai_c, player=next_player))
            winner = check_winner(board)
            if winner:
                game.state.status = "finished"
                game.state.winner = winner
                record_match_result(game)
            elif is_draw(board):
                game.state.status = "finished"
                game.state.winner = None
                record_match_result(game)
            else:
                game.state.current_player = "O" if next_player == "X" else "X"
    return game

# PUBLIC_INTERFACE
@router.get("/games/{id}", response_model=Game, tags=["games"], summary="Get game state")
async def get_game(id: str):
    """Retrieve the current game state."""
    game = GAMES.get(id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

# PUBLIC_INTERFACE
@router.get("/leaderboard", response_model=List, tags=["leaderboard"], summary="Get leaderboard")
async def leaderboard():
    """Return list of top players."""
    return get_leaderboard()

# PUBLIC_INTERFACE
@router.get("/history", response_model=List, tags=["history"], summary="Get match history for all games")
async def match_history(username: str = None):
    """Show match history for one user or all."""
    if username:
        return [h for h in MATCH_HISTORY if h.player_x == username or h.player_o == username]
    return MATCH_HISTORY

# PUBLIC_INTERFACE
@router.websocket("/ws/game/{game_id}")
async def websocket_game(websocket: WebSocket, game_id: str):
    """
    WebSocket endpoint for live updates to the game board.
    - Connect with a valid game_id.
    Receives/forwards game updates.
    """
    await websocket.accept()
    if game_id not in active_connections:
        active_connections[game_id] = []
    active_connections[game_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Forward incoming update to all (like broadcast)
            for ws in active_connections[game_id]:
                if ws is not websocket:
                    await ws.send_text(data)
    except WebSocketDisconnect:
        active_connections[game_id].remove(websocket)
        if not active_connections[game_id]:
            del active_connections[game_id]
