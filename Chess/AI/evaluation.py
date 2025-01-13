# evaluation.py
from AI.piece_square_table import piece_square_tables, piece_values, flipped_piece_square_tables

# Points for game outcome (in centipawns).
checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)

# Castling point adjustments (in centipawns)
CASTLING_PENALTY = 30  # Penalty for losing own castling rights (early game).
OPPONENT_CASTLING_LOSS_BONUS = 35  # Bonus for forcing opponent to lose castling rights.
ENDGAME_CASTLING_IMPORTANCE_REDUCTION = 0.5  # Reduction in importance during the late game.

def calculate_phase(game_state):
    """Calculates the phase of the game based on remaining pieces."""
    max_phase_score = sum(piece_values[piece][0] * 2 for piece in ['N', 'B', 'R', 'Q'])  # Max phase based on all major pieces
    current_phase_score = 0

    for row in game_state.board:
        for cell in row:
            if cell != '--':  # Not empty
                piece_type = cell[1].upper()  # 'P', 'N', etc.
                if piece_type in ['N', 'B', 'R', 'Q']:  # Count major and minor pieces (not pawns or kings)
                    current_phase_score += piece_values[piece_type][0]

    # Calculate phase as a fraction of max phase score
    phase_fraction = current_phase_score / max_phase_score
    return max(0, min(1, phase_fraction))  # Ensure phase is between 0 (late game) and 1 (early game)

def score_board(game_state):
    """Evaluates the board to return a score using PeSTO's evaluation."""
    if game_state.checkmate:
        if game_state.white_to_move:
            return -checkmate_points  # Black wins
        else:
            return checkmate_points  # White wins

    early_game_score, late_game_score = 0, 0  # Updated to reflect correct game phases
    phase = calculate_phase(game_state)  # Phase between 0 (late game) and 1 (early game)

    for row in range(8):
        for col in range(8):
            piece = game_state.board[row][col]
            if piece != '--':  # Ignore empty squares
                piece_type = piece[1].upper()  # 'P', 'N', etc.
                color = 'w' if piece[0] == 'w' else 'b'
                index = row * 8 + col  # Convert 2D board index to 1D

                if color == 'w':
                    early_game_score += piece_values[piece_type][0] + piece_square_tables['eg'][piece_type][index]
                    late_game_score += piece_values[piece_type][1] + piece_square_tables['mg'][piece_type][index]
                else:
                    early_game_score -= piece_values[piece_type][0] + flipped_piece_square_tables['eg'][piece_type][index]
                    late_game_score -= piece_values[piece_type][1] + flipped_piece_square_tables['mg'][piece_type][index]

    # Castling rights adjustment
    castling_penalty_white = 0
    castling_penalty_black = 0

    if not game_state.white_castle_king_side and not game_state.white_castle_queen_side:
        # Apply penalty if white lost both castling rights
        castling_penalty_white += CASTLING_PENALTY * phase + CASTLING_PENALTY * (1 - phase) * ENDGAME_CASTLING_IMPORTANCE_REDUCTION
    if not game_state.black_castle_king_side and not game_state.black_castle_queen_side:
        # Apply penalty if black lost both castling rights
        castling_penalty_black += CASTLING_PENALTY * phase + CASTLING_PENALTY * (1 - phase) * ENDGAME_CASTLING_IMPORTANCE_REDUCTION

    # Bonus for forcing opponent to lose castling rights
    if not game_state.white_castle_king_side and not game_state.white_castle_queen_side:
        early_game_score += OPPONENT_CASTLING_LOSS_BONUS * phase
    if not game_state.black_castle_king_side and not game_state.black_castle_queen_side:
        early_game_score -= OPPONENT_CASTLING_LOSS_BONUS * phase

    # Apply penalties and bonuses to the total score
    early_game_score -= castling_penalty_white
    early_game_score += castling_penalty_black

    # Interpolate between early game and late game scores
    final_score = (early_game_score * (1 - phase) + late_game_score * phase)
    return int(final_score)
