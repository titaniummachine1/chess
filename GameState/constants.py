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

# Board dimension
BOARD_SIZE = 8

# Initial piece positions
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
