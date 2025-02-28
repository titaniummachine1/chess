# Piece values in centipawns for midgame and endgame (for reference)
piece_values = {
    'P': (94, 100),   # Pawn
    'N': (337, 281),  # Knight
    'B': (365, 297),  # Bishop
    'R': (479, 512),  # Rook
    'Q': (1025, 929), # Queen
    'K': (10000, 10000)  # King
}

# Midgame piece-square tables: lists of 64 values (from White's perspective)
piece_square_tables = {
    "mg": {
        "P": [
             0,   0,   0,   0,   0,   0,   0,   0,
            50,  50,  50,  50,  50,  50,  50,  50,
            10,  10,  20,  30,  30,  20,  10,  10,
             5,   5,  10,  25,  25,  10,   5,   5,
             0,   0,   0,  20,  20,   0,   0,   0,
             5,  -5, -10,   0,   0, -10,  -5,   5,
             5,  10,  10, -20, -20,  10,  10,   5,
             0,   0,   0,   0,   0,   0,   0,   0
        ],
        "N": [
            -50, -40, -30, -30, -30, -30, -40, -50,
            -40, -20,   0,   0,   0,   0, -20, -40,
            -30,   0,  10,  15,  15,  10,   0, -30,
            -30,   5,  15,  20,  20,  15,   5, -30,
            -30,   0,  15,  20,  20,  15,   0, -30,
            -30,   5,  10,  15,  15,  10,   5, -30,
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
            -10,   5,   0,   0,   0,   0,   5, -10,
            -20, -10, -10, -10, -10, -10, -10, -20
        ],
        "R": [
              0,   0,   0,   0,   0,   0,   0,   0,
              5,  10,  10,  10,  10,  10,  10,   5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
              0,   0,   0,   5,   5,   0,   0,   0
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
            -80, -70, -70, -70, -70, -70, -70, -80, 
            -60, -60, -60, -60, -60, -60, -60, -60, 
            -40, -50, -50, -60, -60, -50, -50, -40, 
            -30, -40, -40, -50, -50, -40, -40, -30, 
            -20, -30, -30, -40, -40, -30, -30, -20, 
            -10, -20, -20, -20, -20, -20, -20, -10, 
             20,  20,  -5,  -5,  -5,  -5,  20,  20, 
             20,  30,  10,   0,   0,  10,  30,  20
        ]
    },
    "eg": {
        "P": [
              0,   0,   0,   0,   0,   0,   0,   0,
            80,  80,  80,  80,  80,  80,  80,  80,
            50,  50,  50,  50,  50,  50,  50,  50,
            30,  30,  30,  30,  30,  30,  30,  30,
            20,  20,  20,  20,  20,  20,  20,  20,
            10,  10,  10,  10,  10,  10,  10,  10,
            10,  10,  10,  10,  10,  10,  10,  10,
             0,   0,   0,   0,   0,   0,   0,   0
        ],
        "N": [
            -50, -40, -30, -30, -30, -30, -40, -50,
            -40, -20,   0,   0,   0,   0, -20, -40,
            -30,   0,  10,  15,  15,  10,   0, -30,
            -30,   5,  15,  20,  20,  15,   5, -30,
            -30,   0,  15,  20,  20,  15,   0, -30,
            -30,   5,  10,  15,  15,  10,   5, -30,
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
            -10,   5,   0,   0,   0,   0,   5, -10,
            -20, -10, -10, -10, -10, -10, -10, -20
        ],
        "R": [
              0,   0,   0,   0,   0,   0,   0,   0,
              5,  10,  10,  10,  10,  10,  10,   5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
             -5,   0,   0,   0,   0,   0,   0,  -5,
              0,   0,   0,   5,   5,   0,   0,   0
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
            -20, -10, -10, -10, -10, -10, -10, -20,
             -5,   0,   5,   5,   5,   5,   0,  -5,
            -10,  -5,  20,  30,  30,  20,  -5, -10,
            -15, -10,  35,  45,  45,  35, -10, -15,
            -20, -15,  30,  40,  40,  30, -15, -20,
            -25, -20,  20,  25,  25,  20, -20, -25,
            -30, -25,   0,   0,   0,   0, -25, -30,
            -50, -30, -30, -30, -30, -30, -30, -50
        ]
    }
}

# New helper to flip a table (list of 64 values)
def flip_table_for_black(table):
    # Split into 8 rows, reverse the row order, and flatten back
    rows = [table[i*8:(i+1)*8] for i in range(8)]
    rows.reverse()
    return [val for row in rows for val in row]

# Build flipped tables for Black using the new helper:
flipped_piece_square_tables = {
    "mg": {piece: flip_table_for_black(piece_square_tables["mg"][piece])
           for piece in piece_square_tables["mg"]},
    "eg": {piece: flip_table_for_black(piece_square_tables["eg"][piece])
           for piece in piece_square_tables["eg"]}
}

# Phase weights for non-king pieces.
piece_phase = {
    'P': 0,
    'N': 1,
    'B': 1,
    'R': 2,
    'Q': 4,
    'K': 0
}

def compute_game_phase(board):
    """
    Compute the game phase as a fraction between 0 (endgame) and 1 (midgame)
    based on the material (non-king pieces) remaining.
    In the starting position, the phase sum is 24.
    """
    phase = 0
    for square, piece in board.piece_map().items():
        symbol = piece.symbol().upper()
        if symbol in piece_phase:
            phase += piece_phase[symbol]
    max_phase = 24.0
    phase = min(phase, max_phase)
    # Return a fraction: 1 for full midgame, 0 for endgame.
    return phase / max_phase

def interpolate_piece_square(piece, square, color, board):
    """
    Returns an interpolated piece-square value based on the game phase.
    Expects 'piece' to be a string like 'P', 'N', etc.
    'square' should be an integer index (0-63).
    """
    phase_factor = compute_game_phase(board)
    key = piece.upper()  # Ensure uppercase key.
    # Use default table of 64 zeros if key not found.
    if color == chess.WHITE:
        mg = piece_square_tables["mg"].get(key, [0]*64)[square]
        eg = piece_square_tables["eg"].get(key, [0]*64)[square]
    else:
        mg = flipped_piece_square_tables["mg"].get(key, [0]*64)[square]
        eg = flipped_piece_square_tables["eg"].get(key, [0]*64)[square]
    return mg * phase_factor + eg * (1 - phase_factor)