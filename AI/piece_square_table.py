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
    "white": {
        "mg": {
            "P": [
                  0,   0,   0,   0,   0,   0,   0,   0,
                 50,  50,  50,  50,  50,  50,  50,  50,
                 10,  10,  20,  35,  35,  20,  10,  10,
                 10,  15,  30,  70,  70,  30,  15,  10,  # Significantly increased d4/e4 values
                  5,  10,  25,  55,  55,  25,  10,   5,  # Increased d3/e3 values
                  5,   5,   5,   0,   0,   5,   5,   5,
                  0,   0,   0, -30, -30,   0,   0,   0,  # Stronger penalty for not moving central pawns
                  0,   0,   0,   0,   0,   0,   0,   0
            ],
            "N": [
                -80, -50,  -30,  -30,  -30,  -30, -50, -80,  # Much stronger penalty for edge knights
                -50, -20,    0,    0,    0,    0, -20, -50,
                -30,   0,   15,   20,   20,   15,   0, -30,
                -30,   5,   20,   25,   25,   20,   5, -30,
                -30,   0,   15,   20,   20,   15,   0, -30,
                -30,   5,   10,   15,   15,   10,   5, -30,
                -50, -20,    0,    5,    5,    0, -20, -50,
                -80, -50,  -30,  -30,  -30,  -30, -50, -80   # Much stronger penalty for edge knights
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
                -10,   0,   5,  -5,  -5,   0,   0, -10,
                -20, -10, -10,  -2,  -5, -10, -10, -20
            ],
            "K": [
                -120, -120, -120, -120, -120, -120, -120, -120,  # Increased penalties for moving king
                -100, -100, -100, -100, -100, -100, -100, -100,
                -80, -80, -80, -80, -80, -80, -80, -80,
                -70, -70, -70, -70, -70, -70, -70, -70,
                -60, -60, -60, -60, -60, -60, -60, -60,
                -40, -40, -40, -40, -40, -40, -40, -40,
                  0,   0, -10, -30, -30, -10,   0,   0,
                 20,  50,  10,   0,   0,  10,  50,  20
            ]
        },
        "eg": {
            "P": [
                  0,   0,   0,   0,   0,   0,   0,   0,
                400, 400, 400, 400, 400, 400, 400, 400,
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
    },
    "black": {}  # We'll populate this with precomputed values
}

# Pre-compute the black piece tables by mirroring white tables
def precompute_black_tables():
    """Create flipped tables for black pieces to avoid runtime transformations"""
    piece_square_tables["black"]["mg"] = {}
    piece_square_tables["black"]["eg"] = {}
    
    for piece in piece_square_tables["white"]["mg"]:
        piece_square_tables["black"]["mg"][piece] = []
        piece_square_tables["black"]["eg"][piece] = []
        
        # For each position in the 8x8 board
        for rank in range(8):
            for file in range(8):
                # Get original square index
                sq = rank * 8 + file
                # Get mirrored square index (flip rank)
                mirror_rank = 7 - rank
                mirror_sq = mirror_rank * 8 + file
                
                # Copy the value from the mirrored position
                mg_value = piece_square_tables["white"]["mg"][piece][mirror_sq]
                eg_value = piece_square_tables["white"]["eg"][piece][mirror_sq]
                
                # Add to black's table
                piece_square_tables["black"]["mg"][piece].append(mg_value)
                piece_square_tables["black"]["eg"][piece].append(eg_value)

# Run the precomputation during module initialization
precompute_black_tables()

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

def interpolate_piece_square(piece, square, color, phase):
    """
    Get the piece-square table value using precomputed tables for each color.
    Much faster than computing during evaluation.
    """
    key = piece  # The piece symbol ('P', 'N', etc.)
    color_key = "white" if color == chess.WHITE else "black"
    
    # Direct lookup without any transformation
    mg_value = piece_square_tables[color_key]["mg"].get(key, [0]*64)[square]
    eg_value = piece_square_tables[color_key]["eg"].get(key, [0]*64)[square]
    
    # Interpolate between phases
    return mg_value * phase + eg_value * (1 - phase)
