from enum import Enum, IntEnum

class Color(IntEnum):
    WHITE = 0
    BLACK = 1
    
    def opposite(self):
        return Color.BLACK if self == Color.WHITE else Color.WHITE

class PieceType(IntEnum):
    PAWN = 0
    KNIGHT = 1
    BISHOP = 2
    ROOK = 3
    QUEEN = 4
    KING = 5
    
    def symbol(self, color):
        """Returns Unicode chess symbol for the piece"""
        symbols = {
            (Color.WHITE, PieceType.PAWN): '♙',
            (Color.WHITE, PieceType.KNIGHT): '♘',
            (Color.WHITE, PieceType.BISHOP): '♗',
            (Color.WHITE, PieceType.ROOK): '♖',
            (Color.WHITE, PieceType.QUEEN): '♕',
            (Color.WHITE, PieceType.KING): '♔',
            (Color.BLACK, PieceType.PAWN): '♟',
            (Color.BLACK, PieceType.KNIGHT): '♞',
            (Color.BLACK, PieceType.BISHOP): '♝',
            (Color.BLACK, PieceType.ROOK): '♜',
            (Color.BLACK, PieceType.QUEEN): '♛',
            (Color.BLACK, PieceType.KING): '♚',
        }
        return symbols.get((color, self), '?')
    
    def char(self, color):
        """Returns character representation for FEN notation"""
        chars = {
            (Color.WHITE, PieceType.PAWN): 'P',
            (Color.WHITE, PieceType.KNIGHT): 'N',
            (Color.WHITE, PieceType.BISHOP): 'B',
            (Color.WHITE, PieceType.ROOK): 'R',
            (Color.WHITE, PieceType.QUEEN): 'Q',
            (Color.WHITE, PieceType.KING): 'K',
            (Color.BLACK, PieceType.PAWN): 'p',
            (Color.BLACK, PieceType.KNIGHT): 'n',
            (Color.BLACK, PieceType.BISHOP): 'b',
            (Color.BLACK, PieceType.ROOK): 'r',
            (Color.BLACK, PieceType.QUEEN): 'q',
            (Color.BLACK, PieceType.KING): 'k',
        }
        return chars.get((color, self), '?')

class MoveType(Enum):
    NORMAL = 0
    CAPTURE = 1
    CASTLE = 2
    EN_PASSANT = 3
    PROMOTION = 4
    KING_EN_PASSANT = 5  # Special move for catching a king after castling

# Game constants
FPS = 60

# Board dimension
BOARD_SIZE = 8

# Test positions for different scenarios
# Simple endgame position (King and rook vs king)
endgame_Fen = "8/8/2k1K3/8/4r3/8/8/8 w - - 0 1"

# Middle game position with material imbalance
middlegame_Fen = "r3k2r/ppp2ppp/2n5/2bqp3/2bP4/2P2N2/PP3PPP/RNBQR1K1 b kq - 0 10"

# Position with capture opportunities for testing atomic bomb
capture_test_Fen = "r1bqkbnr/ppp2ppp/2n5/3pp3/2B5/4P3/PPPP1PPP/RNBQK1NR w KQkq - 0 1"

# Complex middle game position
complex_Fen = "r1b1k1nr/pp3ppp/2n1p3/q1bpP3/8/P1N2N2/1PPB1PPP/R2QKB1R w KQkq - 0 1"

# Position with kings near each other (for atomic bomb testing)
kings_adjacent_Fen = "8/8/8/3pk3/4K3/8/8/8 w - - 0 1"

# Position specifically designed for testing atomic bomb drawback
atomic_bomb_test_Fen = "r1bqkbnr/ppp2ppp/2n5/3pp3/3P4/2N1P3/PPP2PPP/R1BQKBNR w KQkq - 0 1"

# Initial piece positions (standard starting position)
INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Piece values for evaluation
PIECE_VALUES = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 320,
    PieceType.BISHOP: 330,
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.KING: 20000  # High value since king must be captured to win
}

# Direction vectors
DIRECTIONS = {
    "N": (0, 1),   # North
    "S": (0, -1),  # South
    "E": (1, 0),   # East
    "W": (-1, 0),  # West
    "NE": (1, 1),  # Northeast
    "SE": (1, -1), # Southeast
    "SW": (-1, -1), # Southwest
    "NW": (-1, 1)  # Northwest
}

# Knight move offsets
KNIGHT_MOVES = [
    (2, 1), (1, 2), (-1, 2), (-2, 1),
    (-2, -1), (-1, -2), (1, -2), (2, -1)
]

# UI constants (truly constant values)
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
