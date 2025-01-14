from AI.piece_square_table import piece_square_tables, piece_values, flipped_piece_square_tables

# Points for game outcome (in centipawns).
checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)

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
    """Evaluates the board to return a score using material and positional value."""
    if game_state.checkmate:
        if game_state.white_to_move:
            return -checkmate_points  # Black wins
        else:
            return checkmate_points  # White wins

    early_game_score, late_game_score = 0, 0  # Material and piece-square evaluation
    phase = calculate_phase(game_state)  # Phase between 0 (late game) and 1 (early game)

    for row in range(8):
        for col in range(8):
            piece = game_state.board[row][col]
            if piece != '--':  # Ignore empty squares
                piece_type = piece[1].upper()  # 'P', 'N', etc.
                color = 'w' if piece[0] == 'w' else 'b'
                index = row * 8 + col  # Convert 2D board index to 1D

                if color == 'w':
                    early_game_score += piece_values[piece_type][0]  # Add material value
                    early_game_score += piece_square_tables['eg'][piece_type][index]  # Early game positional bonus
                    late_game_score += piece_values[piece_type][1]  # Add material value (endgame)
                    late_game_score += piece_square_tables['mg'][piece_type][index]  # Late game positional bonus
                else:
                    early_game_score -= piece_values[piece_type][0]  # Subtract opponent's material
                    early_game_score -= flipped_piece_square_tables['eg'][piece_type][index]  # Early game positional penalty
                    late_game_score -= piece_values[piece_type][1]  # Subtract opponent's endgame value
                    late_game_score -= flipped_piece_square_tables['mg'][piece_type][index]  # Late game positional penalty

    # Interpolate between early and late game scores
    final_score = (early_game_score * (1 - phase) + late_game_score * phase)
    return int(final_score)