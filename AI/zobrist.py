import chess
import random

# Global Zobrist tables and constants.
ZOBRIST_TABLE = {}
ZOBRIST_CASTLING = { right: random.getrandbits(64) for right in "KQkq" }
ZOBRIST_EP = [random.getrandbits(64) for _ in range(64)]
ZOBRIST_WHITE_TURN = 0xF0F0F0F0F0F0F0F0
ZOBRIST_BLACK_TURN = 0x0F0F0F0F0F0F0F0F

def compute_zobrist_key(board):
    key = 0
    # Incorporate pieces.
    for square, piece in board.piece_map().items():
        symbol = piece.symbol()
        if (square, symbol) not in ZOBRIST_TABLE:
            ZOBRIST_TABLE[(square, symbol)] = random.getrandbits(64)
        key ^= ZOBRIST_TABLE[(square, symbol)]
    # Incorporate turn.
    key ^= ZOBRIST_WHITE_TURN if board.turn == chess.WHITE else ZOBRIST_BLACK_TURN
    # Incorporate castling rights (if any).
    castling = board.castling_xfen()  # e.g. "KQkq" or "-"
    for char in castling:
        if char in ZOBRIST_CASTLING:
            key ^= ZOBRIST_CASTLING[char]
    # Incorporate en passant.
    if board.ep_square is not None:
        key ^= ZOBRIST_EP[board.ep_square]
    return key

def get_zobrist_key(board):
    """
    Returns the Zobrist hash key for the board. If the board already
    has a 'zobrist_key' attribute, that is assumed up to date.
    """
    if hasattr(board, "zobrist_key"):
        return board.zobrist_key
    return compute_zobrist_key(board)
