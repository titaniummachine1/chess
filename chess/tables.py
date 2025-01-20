##tables.py
import numpy as np
from bitboard import Bitboard as bitboard
from square import Square
from GameState.constants import Rank, File, Color

"""
This file contains various precomputed bitboards for move generation.
"""

# Empty bitboard
EMPTY_BB = np.uint64(0)

# Rank and file bitboards
RANKS = np.array(
    [np.uint64(0x00000000000000FF) << np.uint64(8 * i) for i in range(8)],
    dtype=np.uint64
)
FILES = np.array(
    [np.uint64(0x0101010101010101) << np.uint64(i) for i in range(8)],
    dtype=np.uint64
)

# Masks for individual ranks and files
RANK_MASKS = np.array([RANKS[i // 8] for i in range(64)], dtype=np.uint64)
FILE_MASKS = np.array([FILES[i % 8] for i in range(64)], dtype=np.uint64)

# Diagonal masks
A1H8_DIAG = np.uint64(0x8040201008040201)
H1A8_ANTIDIAG = np.uint64(0x0102040810204080)

# Center squares
CENTER = np.uint64(0x00003C3C3C3C0000)

def compute_diag_mask(i):
    """
    Computes diagonal attack mask for a square.
    """
    file = i % 8
    rank = i // 8
    diag = file - rank
    return np.uint64(A1H8_DIAG) >> np.uint64(abs(diag) * 8)

DIAG_MASKS = np.array([compute_diag_mask(i) for i in range(64)], dtype=np.uint64)

def compute_antidiag_mask(i):
    """
    Computes anti-diagonal attack mask for a square.
    """
    file = i % 8
    rank = i // 8
    antidiag = file + rank
    return np.uint64(H1A8_ANTIDIAG) >> np.uint64(abs(antidiag - 7) * 8)

ANTIDIAG_MASKS = np.array([compute_antidiag_mask(i) for i in range(64)], dtype=np.uint64)


# KING MOVES
def compute_king_moves(i):
    """
    Computes king moves for a square.
    """
    bb = Square(i).to_bitboard()
    moves = (
        (bb & ~FILES[File.A]) << np.uint64(7) |
        bb << np.uint64(8) |
        (bb & ~FILES[File.H]) << np.uint64(9) |
        (bb & ~FILES[File.H]) << np.uint64(1) |
        (bb & ~FILES[File.H]) >> np.uint64(7) |
        bb >> np.uint64(8) |
        (bb & ~FILES[File.A]) >> np.uint64(9) |
        (bb & ~FILES[File.A]) >> np.uint64(1)
    )
    return moves

KING_MOVES = np.array([compute_king_moves(i) for i in range(64)], dtype=np.uint64)


# KNIGHT MOVES
def compute_knight_moves(i):
    """
    Computes knight moves for a square.
    """
    bb = Square(i).to_bitboard()
    moves = (
        (bb & ~(FILES[File.A] | FILES[File.B])) << np.uint64(6) |
        (bb & ~FILES[File.A]) << np.uint64(15) |
        (bb & ~FILES[File.H]) << np.uint64(17) |
        (bb & ~(FILES[File.H] | FILES[File.G])) << np.uint64(10) |
        (bb & ~(FILES[File.H] | FILES[File.G])) >> np.uint64(6) |
        (bb & ~FILES[File.H]) >> np.uint64(15) |
        (bb & ~FILES[File.A]) >> np.uint64(17) |
        (bb & ~(FILES[File.A] | FILES[File.B])) >> np.uint64(10)
    )
    return moves

KNIGHT_MOVES = np.array([compute_knight_moves(i) for i in range(64)], dtype=np.uint64)


# PAWN QUIETS
def compute_pawn_quiet_moves(color, i):
    """
    Computes pawn quiet moves for a square.
    """
    bb = Square(i).to_bitboard()
    rank = RANKS[Rank.TWO] if color == Color.WHITE else RANKS[Rank.SEVEN]

    moves = (
        (bb << np.uint64(8)) if color == Color.WHITE else (bb >> np.uint64(8))
    )
    
    if (bb & rank) != 0:
        moves |= (
            (bb << np.uint64(16)) if color == Color.WHITE else (bb >> np.uint64(16))
        )

    return moves

PAWN_QUIETS = np.array([
    [compute_pawn_quiet_moves(color, i) for i in range(64)]
    for color in Color
], dtype=np.uint64)


# PAWN ATTACKS
def compute_pawn_attack_moves(color, i):
    """
    Computes pawn attack bitboard for a square.
    """
    bb = Square(i).to_bitboard()
    if color == Color.WHITE:
        moves = ((bb & ~FILES[File.A]) << np.uint64(7)) | ((bb & ~FILES[File.H]) << np.uint64(9))
    else:
        moves = ((bb & ~FILES[File.A]) >> np.uint64(9)) | ((bb & ~FILES[File.H]) >> np.uint64(7))
    
    return moves

PAWN_ATTACKS = np.array([
    [compute_pawn_attack_moves(color, i) for i in range(64)]
    for color in Color
], dtype=np.uint64)


# FIRST RANK MOVES
def compute_first_rank_moves(i, occ):
    """Computes rank attack bitboard."""
    x = np.uint8(1) << np.uint8(i)
    occ = np.uint8(occ)

    left = (x - np.uint8(1)) & occ
    if left != 0:
        leftmost = np.uint8(1) << bitboard.msb_bitscan(np.uint64(left))
        left ^= (leftmost - np.uint8(1))

    right = (~x) & (~(x - np.uint8(1))) & occ
    if right != 0:
        rightmost = np.uint8(1) << bitboard.lsb_bitscan(np.uint64(right))
        right ^= (~rightmost) & (~(rightmost - np.uint8(1)))

    return np.uint8(left ^ right)  # ✅ Ensure proper shape
