# evaluation.py
from AI.piece_square_table import piece_square_tables, piece_values

# Points for game outcome (in centipawns).
checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)

def score_board(game_state):
    """Evaluates the board to return a score using PeSTO's evaluation."""
    if game_state.checkmate:
        if game_state.white_to_move:
            return -checkmate_points  # Black wins
        else:
            return checkmate_points  # White wins

    mg_score, eg_score = 0, 0
    phase = 0  # Game phase indicator for tapering

    for row in range(8):
        for col in range(8):
            piece = game_state.board[row][col]
            if piece != '--':  # Ignore empty squares
                piece_type = piece[1].upper()  # 'P', 'N', etc.
                color = 'w' if piece[0] == 'w' else 'b'
                index = row * 8 + col  # Convert 2D board index to 1D

                if color == 'w':
                    mg_score += piece_values[piece_type][0] + piece_square_tables['mg'][piece_type][index]
                    eg_score += piece_values[piece_type][1] + piece_square_tables['eg'][piece_type][index]
                    phase += 1 if piece_type not in ["P", "K"] else 0  # Add phase for non-pawns
                else:
                    mg_score -= piece_values[piece_type][0] + piece_square_tables['mg'][piece_type][63 - index]
                    eg_score -= piece_values[piece_type][1] + piece_square_tables['eg'][piece_type][63 - index]
                    phase += 1 if piece_type not in ["P", "K"] else 0  # Add phase for non-pawns

    # Tapered evaluation between midgame and endgame
    mg_phase = min(phase, 24)  # Midgame phase indicator (max 24)
    eg_phase = 24 - mg_phase  # Endgame phase is inverse of midgame phase

    # Weighted average of midgame and endgame scores
    return (mg_score * mg_phase + eg_score * eg_phase) // 24
