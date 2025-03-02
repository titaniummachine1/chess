"""
Drawback Sunfish - A chess engine inspired by Sunfish but adapted for Drawback Chess.
Uses the DrawbackBoard move generation and existing piece square tables.
"""
import chess
import time
import random
from collections import namedtuple, defaultdict
from GameState.movegen import DrawbackBoard
from AI.piece_square_table import PIECE_VALUES, interpolate_piece_square, compute_game_phase

# Constants for search
MATE_LOWER = 10000
MATE_UPPER = 20000
QS_LIMIT = 200  # Limit for quiescence search
EVAL_ROUGHNESS = 15
MAX_DEPTH = 20

# Transposition table entry
Entry = namedtuple('Entry', 'lower upper move')

class DrawbackSunfish:
    """Chess engine inspired by Sunfish but using DrawbackBoard for move generation"""
    
    def __init__(self):
        self.nodes = 0
        self.tt = {}  # Transposition table: position -> (depth, score, flag, move)
        self.history = {}  # Move history heuristic
        self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]  # Killer moves
        self.eval_cache = {}  # Cache for position evaluations
        
    def evaluate_position(self, board, drawbacks=None):
        """Improved evaluation function with better opening development strategy"""
        # Check cache first
        key = board.fen()
        if key in self.eval_cache:
            return self.eval_cache[key]
        
        # Handle game-ending positions (king captures)
        white_has_king = False
        black_has_king = False
        
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.KING:
                if piece.color == chess.WHITE:
                    white_has_king = True
                else:
                    black_has_king = True
        
        if not white_has_king:
            return -MATE_UPPER  # White's king is gone - loss for white
        if not black_has_king:
            return MATE_UPPER   # Black's king is gone - win for white
        
        # Calculate game phase once per position
        phase = compute_game_phase(board)
        
        # Material + piece-square evaluation
        score = 0
        
        # Process each piece on the board
        for square, piece in board.piece_map().items():
            piece_symbol = piece.symbol().upper()
            piece_color = piece.color
            
            # Get material value
            material_value = PIECE_VALUES.get(piece_symbol, (0, 0))
            mg_value, eg_value = material_value
            
            # Get piece-square table bonus with optimized lookup
            psq_score = interpolate_piece_square(piece_symbol, square, piece_color, phase)
            
            # Material value
            material_score = mg_value * phase + eg_value * (1 - phase)
            total_value = material_score + psq_score
            
            # Add to score based on piece color
            if piece_color == chess.WHITE:
                score += total_value
            else:
                score -= total_value
        
        # Additional opening/middlegame heuristics
        if len(board.move_stack) < 20:  # Early game
            # Development bonus (knights and bishops)
            white_knights = list(board.pieces(chess.KNIGHT, chess.WHITE))
            black_knights = list(board.pieces(chess.KNIGHT, chess.BLACK))
            white_bishops = list(board.pieces(chess.BISHOP, chess.WHITE))
            black_bishops = list(board.pieces(chess.BISHOP, chess.BLACK))
            
            # Knights should be developed from their original squares
            knight_development = 0
            for knight in white_knights:
                if knight != chess.B1 and knight != chess.G1:
                    knight_development += 15
            for knight in black_knights:
                if knight != chess.B8 and knight != chess.G8:
                    knight_development -= 15
            score += knight_development
            
            # Bishops should be developed from their original squares
            bishop_development = 0
            for bishop in white_bishops:
                if bishop != chess.C1 and bishop != chess.F1:
                    bishop_development += 15
            for bishop in black_bishops:
                if bishop != chess.C8 and bishop != chess.F8:
                    bishop_development -= 15
            score += bishop_development
            
            # Enhanced central pawn structure evaluation
            white_center_control = 0
            black_center_control = 0
            
            # Core center squares
            core_center = [chess.D4, chess.E4, chess.D5, chess.E5]
            # Extended center squares
            extended_center = [chess.C3, chess.D3, chess.E3, chess.F3, 
                              chess.C4, chess.F4, chess.C5, chess.F5,
                              chess.C6, chess.D6, chess.E6, chess.F6]
            
            # Bonus for occupying center with pawns (specifically)
            for square in core_center:
                piece = board.piece_at(square)
                if piece:
                    if piece.color == chess.WHITE:
                        if piece.piece_type == chess.PAWN:
                            white_center_control += 25  # Increased bonus for pawns in center
                        else:
                            white_center_control += 15
                    else:
                        if piece.piece_type == chess.PAWN:
                            black_center_control += 25
                        else:
                            black_center_control += 15
                else:
                    # Check if this square is pawn-attacked
                    if board.is_attacked_by(chess.WHITE, square):
                        white_center_control += 10  # Increased pawn attack bonus
                    if board.is_attacked_by(chess.BLACK, square):
                        black_center_control += 10

            # Bonus for extended center control
            for square in extended_center:
                if board.is_attacked_by(chess.WHITE, square):
                    white_center_control += 5
                if board.is_attacked_by(chess.BLACK, square):
                    black_center_control += 5
                    
            # Opening penalty for undeveloped pawns
            if len(board.move_stack) < 10:
                # Check if d2/e2 pawns are still in place
                if board.piece_at(chess.D2) and board.piece_at(chess.D2).piece_type == chess.PAWN:
                    score -= 20  # Penalty for not moving d-pawn
                if board.piece_at(chess.E2) and board.piece_at(chess.E2).piece_type == chess.PAWN:
                    score -= 20  # Penalty for not moving e-pawn
                    
                # Same for black
                if board.piece_at(chess.D7) and board.piece_at(chess.D7).piece_type == chess.PAWN:
                    score += 20  # Penalty for not moving d-pawn (black perspective)
                if board.piece_at(chess.E7) and board.piece_at(chess.E7).piece_type == chess.PAWN:
                    score += 20  # Penalty for not moving e-pawn (black perspective)
            
            score += (white_center_control - black_center_control)
        
        # Return score from perspective of side to move
        final_score = score if board.turn == chess.WHITE else -score
        self.eval_cache[key] = final_score
        return final_score
    
    def quiescence(self, board, alpha, beta, depth=0, max_depth=5):
        """Quiescence search to only evaluate quiet positions"""
        self.nodes += 1
        stand_pat = self.evaluate_position(board)
        
        # Stand pat cutoff
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
            
        # Maximum depth check
        if depth >= max_depth:
            return alpha
            
        # Generate and filter only captures
        captures = []
        for move in board.legal_moves:
            if board.is_capture(move):
                # Score captures by MVV-LVA
                target = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if target and attacker:  # Make sure pieces exist
                    target_symbol = target.symbol().upper()
                    attacker_symbol = attacker.symbol().upper()
                    target_value = PIECE_VALUES.get(target_symbol, (0, 0))[0]
                    attacker_value = PIECE_VALUES.get(attacker_symbol, (0, 0))[0]
                    score = target_value - attacker_value/10
                    captures.append((score, move))
        
        # FIXED: Sort captures by score using key parameter
        captures.sort(key=lambda x: x[0], reverse=True)
        
        # Search captures
        for _, move in captures:
            try:
                # Skip bad captures in late quiescence
                if depth > 0:
                    # Skip capturing with higher value piece
                    victim = board.piece_at(move.to_square)
                    aggressor = board.piece_at(move.from_square)
                    if victim and aggressor:
                        victim_symbol = victim.symbol().upper()
                        aggressor_symbol = aggressor.symbol().upper()
                        victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                        aggressor_value = PIECE_VALUES.get(aggressor_symbol, (0, 0))[0]
                        if aggressor_value > victim_value + 50:
                            continue  # Skip obviously bad captures
                
                board_copy = board.copy()
                board_copy.push(move)
                score = -self.quiescence(board_copy, -beta, -alpha, depth + 1, max_depth)
                
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
            except Exception as e:
                print(f"Error in quiescence search with move {move}: {str(e)}")
                continue  # Skip problematic moves instead of crashing
                
        return alpha
    
    def negamax(self, board, depth, alpha, beta, ply=0, null_ok=True):
        """Enhanced negamax with improved move ordering and checkmate detection"""
        self.nodes += 1
        alpha_orig = alpha
        
        # Check for checkmate opportunity - do this early to find mates quickly!
        opponent_king_square = None
        for sq, piece in board.piece_map().items():
            if piece.piece_type == chess.KING and piece.color != board.turn:
                opponent_king_square = sq
                break
                
        # If we found the opponent's king, check if it can be captured directly
        if opponent_king_square:
            for move in board.legal_moves:
                if move.to_square == opponent_king_square:
                    return MATE_UPPER - ply  # Immediate king capture (checkmate)
        
        # Check transposition table
        key = board.fen()
        tt_entry = self.tt.get((key, depth))
        if tt_entry:
            if tt_entry.lower >= beta:
                return tt_entry.lower
            if tt_entry.upper <= alpha:
                return tt_entry.upper
            alpha = max(alpha, tt_entry.lower)
            beta = min(beta, tt_entry.upper)
            
        # Check for checkmate/stalemate/variant end
        if depth == 0 or board.is_variant_end():
            return self.quiescence(board, alpha, beta)
            
        # Null move pruning
        if depth > 2 and null_ok and not board.is_check():
            # Try a null move to see if we can get a beta cutoff
            board_copy = board.copy()
            board_copy.push(chess.Move.null())
            null_value = -self.negamax(board_copy, depth - 3, -beta, -beta + 1, ply + 1, False)
            if null_value >= beta:
                return beta
        
        # Move ordering with explicit prioritization for captures and checks
        scored_moves = []
        for move in list(board.legal_moves):
            score = 0
            
            # TT move gets high priority
            if tt_entry and move == tt_entry.move:
                score = 10000000
                
            # King captures get highest priority
            if opponent_king_square and move.to_square == opponent_king_square:
                score = 20000000
                
            # Improve move ordering for opening: prioritize central pawn moves
            if len(board.move_stack) < 15:  # Only in opening
                from_piece = board.piece_at(move.from_square)
                if from_piece and from_piece.piece_type == chess.PAWN:
                    # Central pawn advances get a bonus
                    from_file = chess.square_file(move.from_square)
                    if from_file in [3, 4]:  # d and e files
                        score += 400000
                    elif from_file in [2, 5]:  # c and f files
                        score += 300000
            
            # Check if this is a capture move
            capture_value = 0
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    victim_symbol = victim.symbol().upper()
                    attacker_symbol = attacker.symbol().upper()
                    victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                    attacker_value = PIECE_VALUES.get(attacker_symbol, (0, 0))[0]
                    capture_value = victim_value - (attacker_value // 10)
                score += 1000000 + capture_value
                
            # Checks get priority too
            if board.gives_check(move):
                score += 500000
                
            # Killer moves
            if move == self.killers[ply][0]:
                score = 9000
            elif move == self.killers[ply][1]:
                score = 8000
                
            # History heuristic
            score += self.history.get((board.turn, move.from_square, move.to_square), 0)
            
            scored_moves.append((score, move))
        
        # Sort moves by score in descending order
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        
        # Variables to track best move and score
        best_score = -MATE_UPPER
        best_move = None
        
        # Try each move
        for _, move in scored_moves:
            board_copy = board.copy()
            board_copy.push(move)
            
            # Recursive search with full window
            score = -self.negamax(board_copy, depth - 1, -beta, -alpha, ply + 1)
            
            # Update best score and move
            if score > best_score:
                best_score = score
                best_move = move
                
            # Alpha-beta pruning
            alpha = max(alpha, score)
            if alpha >= beta:
                # Store killer move for non-captures
                if not board.is_capture(move):
                    if move != self.killers[ply][0]:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                
                # Update history heuristic
                if not board.is_capture(move):
                    key = (board.turn, move.from_square, move.to_square)
                    self.history[key] = self.history.get(key, 0) + depth * depth
                
                break
        
        # Store in transposition table
        if best_score <= alpha_orig:
            flag = 'upper'
            self.tt[(key, depth)] = Entry(best_score, beta, best_move)
        elif best_score >= beta:
            flag = 'lower'
            self.tt[(key, depth)] = Entry(alpha, best_score, best_move)
        else:
            flag = 'exact'
            self.tt[(key, depth)] = Entry(best_score, best_score, best_move)
        
        return best_score
    
    def search(self, board, depth, time_limit=5):
        """Improved search with better checkmate detection"""
        try:
            self.nodes = 0
            self.tt.clear()
            self.history.clear()
            self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]
            self.eval_cache.clear()
            
            # Check for immediate checkmate moves first (king captures in drawback chess)
            opponent_king_square = None
            for sq, piece in board.piece_map().items():
                if piece.piece_type == chess.KING and piece.color != board.turn:
                    opponent_king_square = sq
                    break
                    
            if opponent_king_square:
                for move in board.legal_moves:
                    if move.to_square == opponent_king_square:
                        print("Found immediate checkmate (king capture)!")
                        return move  # Return king capture immediately
            
            start_time = time.time()
            best_move = None
            
            # Iterative deepening
            for d in range(1, depth + 1):
                print(f"Searching at depth {d}...")
                
                try:
                    # Aspiration window
                    alpha = -MATE_UPPER
                    beta = MATE_UPPER
                    score = self.negamax(board, d, alpha, beta)
                    
                    # Get the best move from the TT
                    key = (board.fen(), d)
                    if key in self.tt and self.tt[key].move:
                        best_move = self.tt[key].move
                        
                    # Print info
                    print(f"Depth: {d}, Score: {score}, Nodes: {self.nodes}, Best move: {best_move}")
                except Exception as e:
                    import traceback
                    print(f"Error at depth {d}: {str(e)}")
                    print(traceback.format_exc())
                    # Don't break - continue to next depth
                
                # Check if we're out of time
                elapsed = time.time() - start_time
                if elapsed >= time_limit:
                    print(f"Time limit reached: {elapsed:.2f}s")
                    break
            
            # Need a minimum result or we're in trouble
            if best_move is None:
                print("Warning: No best move found! Selecting safest available move...")
                moves = list(board.legal_moves)
                
                # Try to find a reasonable move
                if moves:
                    # First try non-pawn moves to start developing
                    non_pawn_moves = [m for m in moves if board.piece_at(m.from_square) and 
                                     board.piece_at(m.from_square).piece_type != chess.PAWN]
                    if non_pawn_moves and len(board.move_stack) < 10:
                        # Prioritize development in opening
                        best_move = random.choice(non_pawn_moves)
                    else:
                        # Safe central pawn moves
                        pawn_moves = [m for m in moves if board.piece_at(m.from_square) and 
                                     board.piece_at(m.from_square).piece_type == chess.PAWN]
                        central_pawn_moves = [m for m in pawn_moves if chess.square_file(m.to_square) in [2, 3, 4, 5]]
                        
                        if central_pawn_moves:
                            best_move = random.choice(central_pawn_moves)
                        else:
                            best_move = random.choice(moves)
                
                print(f"Selected fallback move: {best_move}")
                
            return best_move
        except Exception as e:
            import traceback
            print(f"CRITICAL ERROR in search function: {str(e)}")
            print(traceback.format_exc())
            
            # Last-resort fallback - pick any legal move
            moves = list(board.legal_moves)
            if moves:
                fallback_move = random.choice(moves)
                print(f"Emergency fallback move: {fallback_move}")
                return fallback_move
            return None

# For use as the main AI interface
def best_move(board, depth, time_limit=5):
    try:
        engine = DrawbackSunfish()
        return engine.search(board.copy(), depth, time_limit)
    except Exception as e:
        import traceback
        print(f"ENGINE ERROR: {str(e)}")
        print(traceback.format_exc())
        
        # Emergency fallback
        try:
            moves = list(board.legal_moves)
            if moves:
                return random.choice(moves)
        except:
            pass
        return None
