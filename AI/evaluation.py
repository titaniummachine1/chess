import chess
from AI.piece_square_table import PIECE_VALUES, piece_square_tables, compute_game_phase

# Constants for special evaluations
CHECKMATE_SCORE = 10000
DRAW_SCORE = 0

def evaluate_position(board, pst_weights=None):
    """
    Enhanced evaluation function that can apply PST adjustments from book moves
    """
    # Check if we have valid book weights to apply
    if pst_weights and "weights" in pst_weights and pst_weights["weights"]:
        book_weights = pst_weights["weights"]
        # Only log once per position to reduce spam
        position_key = board.fen().split(' ')[0]
        if not hasattr(evaluate_position, "logged_positions"):
            evaluate_position.logged_positions = set()
            
        if position_key not in evaluate_position.logged_positions:
            print(f"Using book weights with {len(book_weights)} book moves for position")
            evaluate_position.logged_positions.add(position_key)
        
        # Rest of existing evaluation with weights
        # Basic checks for special endings
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
        
        # Calculate game phase for interpolation
        phase = compute_game_phase(board)
        
        # Process each piece on the board with book move adjustments
        score = 0
        default_weight = pst_weights.get("default", 0.25)  # Use absolute minimum for non-book moves
        
        for square, piece in board.piece_map().items():
            piece_symbol = piece.symbol().upper()
            piece_color = piece.color
            
            # Get base material value from lookup table
            material_values = PIECE_VALUES.get(piece_symbol, (0, 0))
            mg_material, eg_material = material_values
            
            # Get piece-square table bonuses
            color_key = "white" if piece_color == chess.WHITE else "black"
            mg_psqt = piece_square_tables[color_key]["mg"].get(piece_symbol, [0]*64)[square]
            eg_psqt = piece_square_tables[color_key]["eg"].get(piece_symbol, [0]*64)[square]
            
            # Apply PST adjustment - ONLY for positive values from each color's perspective
            if (piece_color == chess.WHITE and mg_psqt > 0) or (piece_color == chess.BLACK and mg_psqt < 0):
                # Default to minimum weight for non-book moves
                square_weight = default_weight
                
                # Check if square is a target of any book move
                for book_move, weight in book_weights.items():
                    if book_move.to_square == square:
                        square_weight = max(square_weight, weight)
                        break
                
                # Apply bell curve adjustment - scaled to each side's direction
                if piece_color == chess.WHITE:
                    mg_psqt *= square_weight  # Maximum effect for white's positive values
                    eg_psqt *= square_weight
                else:
                    mg_psqt *= square_weight  # Maximum effect for black's negative values
                    eg_psqt *= square_weight
            
            # Interpolate material and position values
            material_value = mg_material * phase + eg_material * (1 - phase)
            position_value = mg_psqt * phase + eg_psqt * (1 - phase)
            
            # Add to score based on piece color
            if piece_color == chess.WHITE:
                score += material_value + position_value
            else:
                score -= material_value + position_value
        
        # Rest of evaluation remains the same
        score += evaluate_pawn_structure(board, phase)
        score += evaluate_development(board, phase)
        score += evaluate_center_control(board)
        score += evaluate_opening_structure(board)
        
        return score if board.turn == chess.WHITE else -score
    else:
        # Regular evaluation without book adjustments
        return evaluate_position_standard(board)

# Add a separate standard evaluation function with no book adjustments
def evaluate_position_standard(board):
    """Standard evaluation with no book move adjustments - avoids unnecessary work"""
    # Calculate game phase for interpolation
    phase = compute_game_phase(board)
    
    # Basic material and position evaluation
    score = 0
    
    for square, piece in board.piece_map().items():
        piece_symbol = piece.symbol().upper()
        piece_color = piece.color
        
        # Get base material value
        material_values = PIECE_VALUES.get(piece_symbol, (0, 0))
        mg_material, eg_material = material_values
        
        # Get piece-square table bonuses
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
    
    # Additional evaluations
    score += evaluate_pawn_structure(board, phase)
    score += evaluate_development(board, phase)
    score += evaluate_center_control(board)
    score += evaluate_opening_structure(board)
    
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

def evaluate_opening_structure(board):
    """Evaluate opening structure with stronger incentives for both colors"""
    score = 0
    move_count = len(board.move_stack)
    
    # Only apply in opening phase
    if move_count > 15:
        return 0
        
    # STRONGER penalties for not moving central pawns
    # White penalties
    if board.piece_at(chess.D2) and board.piece_at(chess.D2).piece_type == chess.PAWN:
        score -= 100  # Much higher penalty for not moving d-pawn
    if board.piece_at(chess.E2) and board.piece_at(chess.E2).piece_type == chess.PAWN:
        score -= 100  # Much higher penalty for not moving e-pawn
        
    # Black penalties (note: for black, we ADD to score as penalties)
    if board.piece_at(chess.D7) and board.piece_at(chess.D7).piece_type == chess.PAWN:
        score += 100  # Much higher penalty for Black not moving d-pawn
    if board.piece_at(chess.E7) and board.piece_at(chess.E7).piece_type == chess.PAWN:
        score += 100  # Much higher penalty for Black not moving e-pawn
    
    # BONUS for having actually moved the central pawns
    if board.piece_at(chess.D4) and board.piece_at(chess.D4).piece_type == chess.PAWN and board.piece_at(chess.D4).color == chess.WHITE:
        score += 80  # Bonus for having d4
    if board.piece_at(chess.E4) and board.piece_at(chess.E4).piece_type == chess.PAWN and board.piece_at(chess.E4).color == chess.WHITE:
        score += 80  # Bonus for having e4
        
    if board.piece_at(chess.D5) and board.piece_at(chess.D5).piece_type == chess.PAWN and board.piece_at(chess.D5).color == chess.BLACK:
        score -= 80  # Bonus for Black having d5
    if board.piece_at(chess.E5) and board.piece_at(chess.E5).piece_type == chess.PAWN and board.piece_at(chess.E5).color == chess.BLACK:
        score -= 80  # Bonus for Black having e5
    
    # FIX: Apply extra penalty for developing knights before central pawns
    white_central_pawns_moved = not board.piece_at(chess.D2) or not board.piece_at(chess.E2)
    black_central_pawns_moved = not board.piece_at(chess.D7) or not board.piece_at(chess.E7)
    
    # Count developed knights
    white_knights_developed = 0
    black_knights_developed = 0
    
    for knight in board.pieces(chess.KNIGHT, chess.WHITE):
        if knight != chess.B1 and knight != chess.G1:
            white_knights_developed += 1
    
    for knight in board.pieces(chess.KNIGHT, chess.BLACK):
        if knight != chess.B8 and knight != chess.G8:
            black_knights_developed += 1
    
    # Penalize if knights are developed but central pawns are not
    if not white_central_pawns_moved and white_knights_developed > 0:
        score -= white_knights_developed * 60
    
    if not black_central_pawns_moved and black_knights_developed > 0:
        score += black_knights_developed * 60
    
    return score
