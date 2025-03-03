import chess
from AI.piece_square_table import PIECE_VALUES, piece_square_tables, compute_game_phase

# Constants for special evaluations
CHECKMATE_SCORE = 10000
DRAW_SCORE = 0

def evaluate_position(board):
    """
    Core evaluation function that correctly applies material values and piece-square tables.
    Returns a score from the perspective of the side to move.
    """
    # Check for special game endings
    if not any(True for _ in board.legal_moves):
        if board.is_check():
            return -CHECKMATE_SCORE  # Checkmate
        return DRAW_SCORE  # Stalemate
    
    # Check for kings - special case in Drawback Chess where king can be captured
    white_has_king = False
    black_has_king = False
    
    for square, piece in board.piece_map().items():
        if piece.piece_type == chess.KING:
            if piece.color == chess.WHITE:
                white_has_king = True
            else:
                black_has_king = True
    
    if not white_has_king:
        return -CHECKMATE_SCORE if board.turn == chess.WHITE else CHECKMATE_SCORE
    if not black_has_king:
        return CHECKMATE_SCORE if board.turn == chess.WHITE else -CHECKMATE_SCORE
    
    # Calculate game phase for interpolation between midgame and endgame
    phase = compute_game_phase(board)
    
    # Evaluate material and piece positioning
    score = 0
    
    # Process each piece on the board
    for square, piece in board.piece_map().items():
        piece_symbol = piece.symbol().upper()
        piece_color = piece.color
        
        # Get base material value from lookup table (midgame, endgame)
        material_values = PIECE_VALUES.get(piece_symbol, (0, 0))
        mg_material, eg_material = material_values
        
        # Get piece-square table bonuses - already precomputed for both colors
        color_key = "white" if piece_color == chess.WHITE else "black"
        mg_psqt = piece_square_tables[color_key]["mg"].get(piece_symbol, [0]*64)[square]
        eg_psqt = piece_square_tables[color_key]["eg"].get(piece_symbol, [0]*64)[square]
        
        # Interpolate between midgame and endgame values based on phase
        material_value = mg_material * phase + eg_material * (1 - phase)
        position_value = mg_psqt * phase + eg_psqt * (1 - phase)
        
        # Add to score based on piece color
        if piece_color == chess.WHITE:
            score += material_value + position_value
        else:
            score -= material_value + position_value
    
    # Additional evaluation features
    score += evaluate_pawn_structure(board, phase)
    score += evaluate_development(board, phase)
    score += evaluate_center_control(board)
    
    # Return score from the perspective of the side to move
    return score if board.turn == chess.WHITE else -score

def evaluate_pawn_structure(board, phase):
    """Evaluate pawn structure features"""
    score = 0
    
    # Pawn structure only matters less in the endgame
    if phase < 0.8:  # More important in midgame
        return score
    
    # Doubled pawns penalty
    files = {}
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN:
            file_idx = chess.square_file(square)
            if file_idx not in files:
                files[file_idx] = {'white': 0, 'black': 0}
            
            if piece.color == chess.WHITE:
                files[file_idx]['white'] += 1
            else:
                files[file_idx]['black'] += 1
    
    # Penalize doubled pawns
    doubled_pawn_penalty = 15
    for file_data in files.values():
        if file_data['white'] > 1:
            score -= (file_data['white'] - 1) * doubled_pawn_penalty
        if file_data['black'] > 1:
            score += (file_data['black'] - 1) * doubled_pawn_penalty
            
    return score

def evaluate_development(board, phase):
    """Evaluate piece development in the opening and middlegame"""
    score = 0
    move_count = len(board.move_stack)
    
    # Only consider development in the opening
    if phase < 0.7 or move_count > 15:
        return 0
        
    # Stronger development incentives
    development_bonus = 25  # Higher bonus for development
        
    # Knights should be developed from their starting squares
    for knight in board.pieces(chess.KNIGHT, chess.WHITE):
        if knight != chess.B1 and knight != chess.G1:
            # Much better if knights are centralized, not on edges
            knight_file = chess.square_file(knight)
            if knight_file in [2, 3, 4, 5]:  # Files c through f
                score += development_bonus
            else:
                # Small bonus for just moving, but not to the edge
                score += 5
    
    for knight in board.pieces(chess.KNIGHT, chess.BLACK):
        if knight != chess.B8 and knight != chess.G8:
            knight_file = chess.square_file(knight)
            if knight_file in [2, 3, 4, 5]:  # Files c through f
                score -= development_bonus
            else:
                score -= 5
    
    # Bishops should be developed
    for bishop in board.pieces(chess.BISHOP, chess.WHITE):
        if bishop != chess.C1 and bishop != chess.F1:
            score += development_bonus
    
    for bishop in board.pieces(chess.BISHOP, chess.BLACK):
        if bishop != chess.C8 and bishop != chess.F8:
            score -= development_bonus
    
    # Central pawn development
    if board.piece_at(chess.E4) and board.piece_at(chess.E4).piece_type == chess.PAWN and board.piece_at(chess.E4).color == chess.WHITE:
        score += 30  # e4 is very strong for center control
    if board.piece_at(chess.D4) and board.piece_at(chess.D4).piece_type == chess.PAWN and board.piece_at(chess.D4).color == chess.WHITE:
        score += 30  # d4 is very strong for center control
        
    if board.piece_at(chess.E5) and board.piece_at(chess.E5).piece_type == chess.PAWN and board.piece_at(chess.E5).color == chess.BLACK:
        score -= 30  # e5 is very strong for center control
    if board.piece_at(chess.D5) and board.piece_at(chess.D5).piece_type == chess.PAWN and board.piece_at(chess.D5).color == chess.BLACK:
        score -= 30  # d5 is very strong for center control
    
    return score

def evaluate_center_control(board):
    """Evaluate control of the center squares"""
    score = 0
    
    # Center squares
    center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
    
    # For each center square, add score for attacking it
    for square in center_squares:
        if board.is_attacked_by(chess.WHITE, square):
            score += 10
        if board.is_attacked_by(chess.BLACK, square):
            score -= 10
    
    return score
