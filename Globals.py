"""
Global variables used across the application
"""

# Game Settings
FPS = 60
AI_DEPTH = 7
WHITE_AI = True
BLACK_AI = True
TIME_LIMIT = 7  # Default AI time limit in seconds

# Game State Globals
GAME_OVER = False
WINNER_COLOR = None
FLIPPED_BOARD = False
AI_MOVE_COOLDOWN = 0
SEARCH_IN_PROGRESS = False

# Available drawbacks for use in the game
DRAWBACKS = [
    "no_knight_moves",
    "no_bishop_captures",
    "no_knight_captures",
    "punching_down",
    "professional_courtesy",
    "just_passing_through", 
    "forward_march",
    "get_down_mr_president",
    "vegan",
    "chivalry",
    "blinded_by_the_sun",
    "leaps_and_bounds",
    "friendly_fire",
    "covering_fire",
    "atomic_bomb",
    "closed_book",
    "true_gentleman",
    "pack_mentality"
]

# UI constants
TINKER_PANEL_WIDTH = 800
TINKER_PANEL_HEIGHT = 600
TINKER_BUTTON_WIDTH = 100
TINKER_BUTTON_HEIGHT = 35
TINKER_BUTTON_TOP = 10
TINKER_BUTTON_COLOR = (100, 100, 150)

# Text colors
TEXT_COLOR_WHITE = (255, 255, 255)
TEXT_COLOR_BLACK = (0, 0, 0)
HIGHLIGHT_COLOR = (255, 255, 0, 100)
GOLD_COLOR = (255, 215, 0)
STATUS_BG_COLOR = (0, 0, 139)  # Dark blue

# Game board colors
WHITE_SQUARE = (255, 255, 255)
DARK_SQUARE = (128, 128, 128)  # Gray

# UI display options
SHOW_MOVE_HISTORY = True
MOVE_HISTORY_X = 700
MOVE_HISTORY_Y = 100
MOVE_HISTORY_FONT_SIZE = 16

# Help text
HELP_TEXT = [
    "R - Restart game", 
    "T - Tinker panel", 
    "Z - Undo move"
]