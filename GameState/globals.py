"""
Global game state variables that can change during execution.
These are mutable values that represent the current game state.
"""
import chess

# Game State Variables (mutable during gameplay)
GAME_OVER = False
WINNER_COLOR = None
FLIPPED_BOARD = False
AI_MOVE_COOLDOWN = 0
SEARCH_IN_PROGRESS = False

# AI Configuration (can be modified during gameplay)
WHITE_AI = False
BLACK_AI = False
AI_DEPTH = 7
TIME_LIMIT = 10  # Default AI time limit in seconds

# Available drawbacks for use in the game
DRAWBACKS = [
    "atomic_bomb",
    "blinded_by_the_sun", 
    "chivalry",
    "covering_fire",
    "forward_march",
    "get_down_mr_president",
    "just_passing_through", 
    "pack_mentality",
    "professional_courtesy",
    "punching_down", 
    "true_gentleman",
    "vegan"
] 