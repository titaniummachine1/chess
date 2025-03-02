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
        """Improved evaluation function with proper piece-square table values"""
        # Check cache first
        key = board.fen()
        if key in self.eval_cache:
            return self.eval_cache[key]
        
        # Game ending positions
        if not any(piece.piece_type == chess.KING and piece.color == chess.WHITE for piece in board.piece_map().values()):
            return -MATE_UPPER  # White king is captured
        if not any(piece.piece_type == chess.KING and piece.color == chess.BLACK for piece in board.piece_map().values()):
            return MATE_UPPER  # Black king is captured
        
        # Compute game phase for piece-square table interpolation
        phase = compute_game_phase(board)
        
        # Material + piece-square evaluation
        score = 0
        
        # Process each piece on the board
        for square, piece in board.piece_map().items():
            piece_symbol = piece.symbol().upper()
            piece_color = piece.color
            
            # Get material value from PIECE_VALUES
            material_value = PIECE_VALUES.get(piece_symbol, (0, 0))
            mg_value, eg_value = material_value
            
            # Get piece-square table bonus for this piece at this square
            psq_score = interpolate_piece_square(piece_symbol, square, piece_color, board)
            
            # Interpolate between midgame and endgame values based on phase
            combined_value = (mg_value + psq_score) * phase + eg_value * (1 - phase)
            
            # Add to score based on piece color
            if piece_color == chess.WHITE:
                score += combined_value
            else:
                score -= combined_value
        
        # ENHANCEMENT: Pawn structure analysis
        pawn_score = 0
        white_pawns = list(board.pieces(chess.PAWN, chess.WHITE))
        black_pawns = list(board.pieces(chess.PAWN, chess.BLACK))
        
        # Doubled pawns penalty
        for file in range(8):
            white_pawns_on_file = sum(1 for p in white_pawns if chess.square_file(p) == file)
            black_pawns_on_file = sum(1 for p in black_pawns if chess.square_file(p) == file)
            if white_pawns_on_file > 1:
                pawn_score -= 15 * (white_pawns_on_file - 1)  # Penalty for doubled pawns
            if black_pawns_on_file > 1:
                pawn_score += 15 * (black_pawns_on_file - 1)  # Penalty for opponent
        
        # Isolated pawns penalty
        files_with_white_pawns = [chess.square_file(p) for p in white_pawns]
        files_with_black_pawns = [chess.square_file(p) for p in black_pawns]
        for p in white_pawns:
            file = chess.square_file(p)
            if (file > 0 and file-1 not in files_with_white_pawns and 
                file < 7 and file+1 not in files_with_white_pawns):
                pawn_score -= 20  # Isolated pawn penalty
        for p in black_pawns:
            file = chess.square_file(p)
            if (file > 0 and file-1 not in files_with_black_pawns and 
                file < 7 and file+1 not in files_with_black_pawns):
                pawn_score += 20  # Isolated pawn penalty for opponent
        
        score += pawn_score
        
        # Add mobility bonus with proper phase scaling
        mobility_bonus = 0
        mobility_weight = 7 * phase + 3 * (1 - phase)  # More important in middlegame
        
        original_turn = board.turn
        
        # White mobility
        board.turn = chess.WHITE
        white_mobility = len(list(board.legal_moves))
        
        # Black mobility
        board.turn = chess.BLACK
        black_mobility = len(list(board.legal_moves))
        
        # Restore original turn
        board.turn = original_turn
        
        mobility_bonus = (white_mobility - black_mobility) * mobility_weight
        score += mobility_bonus
        
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
        """Negamax search with alpha-beta pruning"""
        self.nodes += 1
        alpha_orig = alpha
        
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
        
        # Move ordering:
        # 1. TT move
        # 2. Good captures (MVV/LVA)
        # 3. Killer moves
        # 4. History heuristic
        moves = list(board.legal_moves)
        if not moves:
            # No legal moves - in our variant, might be a win for the opponent
            if board.is_variant_end():
                if board.is_variant_win():
                    return MATE_UPPER - ply
                elif board.is_variant_loss():
                    return -MATE_UPPER + ply
                else:
                    return 0  # Draw
            else:
                return -MATE_UPPER + ply  # Assume loss if no legal moves
        
        # Get the TT move if available
        tt_move = tt_entry.move if tt_entry else None
        
        # Score moves for ordering
        scored_moves = []
        for move in moves:
            score = 0
            
            # TT move gets highest priority
            if tt_move and move == tt_move:
                score = 20000
            # Capturing moves scored by MVV-LVA
            elif board.is_capture(move):
                victim = board.piece_at(move.to_square)
                aggressor = board.piece_at(move.from_square)
                if victim and aggressor:
                    victim_symbol = victim.symbol().upper()
                    aggressor_symbol = aggressor.symbol().upper()
                    victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                    aggressor_value = PIECE_VALUES.get(aggressor_symbol, (0, 0))[0]
                    score = 10 * victim_value - aggressor_value + 10000
            # Killer moves
            if move == self.killers[ply][0]:
                score = 9000
            elif move == self.killers[ply][1]:
                score = 8000
            # History heuristic
            score += self.history.get((board.turn, move.from_square, move.to_square), 0)
            
            scored_moves.append((score, move))
        
        # FIX: Sort moves by score (first element in tuple) rather than comparing the tuples directly
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
        """Iterative deepening search with time limit"""
        try:
            self.nodes = 0
            self.tt.clear()
            self.history.clear()
            self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]
            self.eval_cache.clear()
            
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
def best_move(board, depth):
    try:
        engine = DrawbackSunfish()
        return engine.search(board.copy(), depth)
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
