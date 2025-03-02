# AI/piece_square_table.py
import chess

# Base piece values as tuples: (midgame, endgame)
PIECE_VALUES = {
    'P': (94, 100),
    'N': (337, 281),
    'B': (365, 297),
    'R': (479, 512),
    'Q': (1025, 929),
    'K': (10000, 10000)  # King's base is fixed; positional bonus is added later.
}

# Midgame piece–square tables (white perspective), 64 values each.
piece_square_tables = {
    "mg": {
        "P": [
              0,   0,   0,   0,   0,   0,   0,   0,
             50,  50,  50,  50,  50,  50,  50,  50,
             10,  10,  20,  35,  35,  20,  10,  10,
              0,   5,  10,  40,  40,  10,   5,   0,  # Increased d4/e4 values
              0,   0,  20,  40,  40,  20,   0,   0,  # Increased d4/e4 values
              5,  -5,  -5, -20, -20,  -5,  -5,   5,
            -10,  10,  10, -50, -50,  10,  10, -10,  # Stronger penalty for not moving central pawns
              0,   0,   0,   0,   0,   0,   0,   0
        ],
        "N": [
            -40, -20,  -10,  -10,  -10,  -10, -20, -40,
            -20,   0,    5,    5,    5,    5,   0, -20,
            -10,   5,   10,   10,   10,   10,   5, -10,
            -10,   5,   10,   15,   15,   10,   5, -10,
            -10,   5,   10,   15,   15,   10,   5, -10,
            -10,   5,   15,   10,   10,   15,   5, -10,
            -20,   0,    5,    5,    5,    5,   0, -20,
            -40, -20,  -10,  -10,  -10,  -10, -20, -40
        ],
        "B": [
            -20, -10, -10, -10, -10, -10, -10, -20,
            -10,   0,   0,   0,   0,   0,   0, -10,
            -10,   0,   5,  10,  10,   5,   0, -10,
            -10,   5,   5,  10,  10,   5,   5, -10,
            -10,   0,  10,  10,  10,  10,   0, -10,
            -10,  10,  10,  10,  10,  10,  10, -10,
            -10,  15,   0,   0,   0,   0,  15, -10,
            -20, -10, -10, -10, -10, -10, -10, -20
        ],
        "R": [
             40, 40,  40,   0,   0,  40,  40, 40,
             5,  15,  15,  50,  50,  15,  50,  5,
             5,   0,   0,   0,   0,   0,   0,  5,
             5,   0,   0,   0,   0,   0,   0,  5,
             5,   0,   0,   0,   0,   0,   0,  5,
             5,   0,   0,   0,   0,   0,   0,  5,
             5,   0,   0,   0,   0,   0,   0,  5,
             0,  -5,   5,   5,   5,   10,  -5,  0
        ],
        "Q": [
            -20, -10, -10,  -5,  -5, -10, -10, -20,
            -10,   0,   0,   0,   0,   0,   0, -10,
            -10,   0,   5,   5,   5,   5,   0, -10,
             -5,   0,   5,   5,   5,   5,   0,  -5,
              0,   0,   5,   5,   5,   5,   0,  -5,
            -10,   5,   5,   5,   5,   5,   0, -10,
            -10,   0,   5,   0,   0,   0,   0, -10,
            -20, -10, -10,  -5,  -5, -10, -10, -20
        ],
        "K": [
            -120, -120, -120, -120, -120, -120, -120, -120,  # Increased penalties for moving king
            -100, -100, -100, -100, -100, -100, -100, -100,
            -80, -80, -80, -80, -80, -80, -80, -80,
            -70, -70, -70, -70, -70, -70, -70, -70,
            -60, -60, -60, -60, -60, -60, -60, -60,
            -40, -40, -40, -40, -40, -40, -40, -40,
              0,   0, -10, -30, -30, -10,   0,   0,
             20,  40,  10,   0,   0,  10,  40,  20
        ]
    },
    "eg": {
        "P": [
              0,   0,   0,   0,   0,   0,   0,   0,
            80,  85,  80,  80,  80,  80,  85,  80,
            50,  55,  50,  50,  50,  50,  55,  50,
            30,  35,  30,  30,  30,  30,  35,  30,
            25,  20,  20,  20,  20,  20,  20,  25,
            15,  10,  10,  10,  10,  10,  10,  15,
            10,  10,  10,  10,  10,  10,  10,  10,
             0,   0,   0,   0,   0,   0,   0,   0
        ],
        "N": [
            -50, -40, -30, -30, -30, -30, -40, -50,
            -40, -20,   0,   0,   0,   0, -20, -40,
            -30,   0,  10,  15,  15,  10,   0, -30,
            -30,  10,  15,  20,  20,  15,  10, -30,
            -30,   0,  15,  20,  20,  15,   0, -30,
            -30,   5,  15,  15,  15,  15,   5, -30,
            -40, -20,   0,   5,   5,   0, -20, -40,
            -50, -40, -30, -30, -30, -30, -40, -50
        ],
        "B": [
            -20, -10, -10, -10, -10, -10, -10, -20,
            -10,   0,   0,   0,   0,   0,   0, -10,
            -10,   0,   5,  10,  10,   5,   0, -10,
            -10,   5,   5,  10,  10,   5,   5, -10,
            -10,   0,  10,  10,  10,  10,   0, -10,
            -10,  10,  10,  10,  10,  10,  10, -10,
            -10,  10,   0,   0,   0,   0,  10, -10,
            -20, -10, -10, -10, -10, -10, -10, -20
        ],
        "R": [
             40,  40,  40,   0,   0,  40,  40,  40,
              5,  10,  10,  10,  10,  10,  10,   5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
              0,   0,  10,   5,   5,   10,  0,   0
        ],
        "Q": [
            -20, -10, -10,  -5,  -5, -10, -10, -20,
            -10,   0,   0,   0,   0,   0,   0, -10,
            -10,   0,   5,   5,   5,   5,   0, -10,
             -5,   0,   5,   5,   5,   5,   0,  -5,
              0,   0,   5,   5,   5,   5,   0,  -5,
            -10,   5,   5,   5,   5,   5,   0, -10,
            -10,   0,   5,   0,   0,   0,   0, -10,
            -20, -10, -10,  -5,  -5, -10, -10, -20
        ],
        "K": [
            -50, -30, -30, -30, -30, -30, -30, -50,
            -30, -20, -20, -20, -20, -20, -20, -30,
            -30, -10,  -5,   0,   0, -5, -10, -30,
            -30, -10,   0,  10,  10,   0, -10, -30,
            -30, -10,   0,  10,  10,   0, -10, -30,
            -30, -10,  -5,   0,   0,  -5, -10, -30,
            -30, -20, -20, -20, -20, -20, -20, -30,
            -50, -30, -30, -30, -30, -30, -30, -50
        ]
    }
}

def flip_and_invert_table(table):
    """
    Flips a table vertically and inverts the values.
    This ensures black's piece square table values are correctly mirrored.
    """
    # Split into rows
    rows = [table[i*8:(i+1)*8] for i in range(8)]
    # Reverse the order of rows (flip vertically)
    rows.reverse()
    # Invert values and flatten
    return [-val for row in rows for val in row]

# Create tables for black that are both flipped AND have inverted values
flipped_piece_square_tables = {
    "mg": {piece: flip_and_invert_table(piece_square_tables["mg"][piece])
           for piece in piece_square_tables["mg"]},
    "eg": {piece: flip_and_invert_table(piece_square_tables["eg"][piece])
           for piece in piece_square_tables["eg"]}
}

# Phase weights for piece counting
piece_phase = {
    'P': 0,
    'N': 1,
    'B': 1,
    'R': 2,
    'Q': 4,
    'K': 0
}

def compute_game_phase(board):
    """Calculate game phase based on remaining pieces"""
    phase = 0
    for square, piece in board.piece_map().items():
        symbol = piece.symbol().upper()
        if symbol in piece_phase:
            phase += piece_phase[symbol]
    max_phase = 24.0
    phase = min(phase, max_phase)
    return phase / max_phase

def interpolate_piece_square(piece, square, color, board):
    """
    Get the piece-square table value for a specific piece and square.
    Properly handles both colors (white and black).
    """
    phase_factor = compute_game_phase(board)
    key = piece.upper()
    
    # For black pieces, we need to mirror the square on the board
    # and negate the resulting value to maintain correct evaluation
    if color == chess.WHITE:
        # White pieces use tables directly
        mg = piece_square_tables["mg"].get(key, [0]*64)[square]
        eg = piece_square_tables["eg"].get(key, [0]*64)[square]
    else:
        # For black pieces, use the precomputed flipped and inverted tables
        mirror_square = square ^ 56  # This flips the square vertically (a8 becomes a1, etc)
        mg = -piece_square_tables["mg"].get(key, [0]*64)[mirror_square]
        eg = -piece_square_tables["eg"].get(key, [0]*64)[mirror_square]
    
    return mg * phase_factor + eg * (1 - phase_factor)
