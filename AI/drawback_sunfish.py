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
from AI.book_parser import OPENING_BOOK

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
        
    def evaluate(self, board):
        """Evaluate the position - positive is good for the side to move"""
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
        for square, piece in board.piece_map().items():
            # Get piece-square table value
            piece_symbol = piece.symbol().upper()
            psq_score = interpolate_piece_square(piece_symbol, square, piece.color, board)
            
            # Get material value
            material_value = PIECE_VALUES.get(piece_symbol, (0, 0))
            mg_value, eg_value = material_value
            material_score = mg_value * phase + eg_value * (1 - phase)
            
            # Combine material and piece-square scores
            value = material_score + psq_score
            
            # Add to total based on piece color
            if piece.color == chess.WHITE:
                score += value
            else:
                score -= value
        
        # Mobility bonus
        mobility_white = len(list(board.generate_legal_moves()))
        board.turn = not board.turn  # Temporarily switch side to get opponent mobility
        mobility_black = len(list(board.generate_legal_moves()))
        board.turn = not board.turn  # Switch back
        
        # Add mobility score (5 centipawns per move difference)
        score += (mobility_white - mobility_black) * 5
        
        # Cache and return score, adjusted for side to move
        self.eval_cache[key] = score if board.turn == chess.WHITE else -score
        return self.eval_cache[key]
    
    def quiescence(self, board, alpha, beta, depth=0, max_depth=5):
        """Quiescence search to only evaluate quiet positions"""
        self.nodes += 1
        stand_pat = self.evaluate(board)
        
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
    
    def order_moves(self, board, moves):
        """Order moves for better pruning with book knowledge integration"""
        scored_moves = []
        
        # Check if we have book moves for this position
        book_moves = OPENING_BOOK.get_book_moves(board)
        book_move_dict = {move: freq for move, freq in book_moves}
        
        for move in moves:
            score = 0
            
            # Check if this is a book move - highest priority
            if move in book_move_dict:
                # Base score of 30000 plus frequency weighting
                book_freq = book_move_dict[move]
                score = 30000 + min(book_freq * 10, 1000)  # Cap at 1000 for very common moves
                print(f"Found book move {move} with frequency {book_freq}")
            
            # ...existing ordering logic...
            
            # Store move and score
            scored_moves.append((score, move))
        
        # Sort by score
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [move for _, move in scored_moves]
    
    def negamax(self, board, depth, alpha, beta, ply=0, null_ok=True):
        """Negamax search with alpha-beta pruning and book integration"""
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
        
        # Check if we have book moves for this position
        book_moves = OPENING_BOOK.get_book_moves(board)
        if book_moves and len(board.move_stack) < 20:  # Only use book in first 20 moves
            # Find the most popular book move
            best_book_move = max(book_moves, key=lambda item: item[1])[0]
            if best_book_move in board.legal_moves:
                # Return immediately with a strong positive score
                print(f"Using book move: {best_book_move}")
                return 100, best_book_move
        
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
        """Iterative deepening search with time limit and book integration"""
        try:
            self.nodes = 0
            self.tt.clear()
            self.history.clear()
            self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]
            self.eval_cache.clear()
            
            start_time = time.time()
            best_move = None
            
            # First, check the opening book for exact position matches
            book_moves = OPENING_BOOK.get_book_moves(board)
            if book_moves and len(board.move_stack) < 20:  # Only use book in first 20 moves
                # Select from book moves, with probability weighted by frequency
                total_freq = sum(freq for _, freq in book_moves)
                if total_freq > 0:
                    # Filter to ensure only legal moves
                    legal_book_moves = [(move, freq) for move, freq in book_moves if move in board.legal_moves]
                    if legal_book_moves:
                        # Use weighted random selection
                        move_weights = [freq/total_freq for _, freq in legal_book_moves]
                        selected_move = random.choices(
                            [move for move, _ in legal_book_moves],
                            weights=move_weights,
                            k=1
                        )[0]
                        print(f"Selected book move: {selected_move}")
                        return selected_move
            
            # If no book move found or selected, try opening principles
            if len(board.move_stack) < 10:
                # Apply opening principles based on color
                if board.turn == chess.WHITE:
                    # White opening principles
                    best_move = self.apply_white_opening_principles(board)
                    if best_move:
                        print(f"Using opening principle move for White: {best_move}")
                        return best_move
                else:
                    # Black opening principles
                    best_move = self.apply_black_opening_principles(board)
                    if best_move:
                        print(f"Using opening principle move for Black: {best_move}")
                        return best_move
            
            # Normal iterative deepening
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
        
    def apply_white_opening_principles(self, board):
        """Apply basic opening principles for white"""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
            
        # First move preferences: e4 or d4
        if len(board.move_stack) == 0:
            for uci in ["e2e4", "d2d4"]:
                move = chess.Move.from_uci(uci)
                if move in legal_moves:
                    return move
        
        # Develop knights before bishops
        knight_moves = []
        for move in legal_moves:
            if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type == chess.KNIGHT:
                from_rank = chess.square_rank(move.from_square)
                from_file = chess.square_file(move.from_square)
                # Knight from starting position to good development square
                if from_rank == 0 and (from_file == 1 or from_file == 6):  # b1 or g1
                    to_rank = chess.square_rank(move.to_square)
                    to_file = chess.square_file(move.to_square)
                    # Good knight development squares (c3, f3)
                    if to_rank == 2 and (to_file == 2 or to_file == 5):
                        return move
                    # Also accept d2, e2 as development
                    if to_rank == 1 and (to_file == 3 or to_file == 4):
                        knight_moves.append(move)
        
        # If we found any reasonable knight development moves, use one
        if knight_moves:
            return random.choice(knight_moves)
            
        # Develop center pawns if not moved yet
        for from_square in [chess.E2, chess.D2]:
            if board.piece_at(from_square) and board.piece_at(from_square).piece_type == chess.PAWN:
                push1 = chess.Move(from_square, from_square + 8)  # One square push
                push2 = chess.Move(from_square, from_square + 16)  # Two square push
                if push2 in legal_moves:
                    return push2
                elif push1 in legal_moves:
                    return push1
                    
        # Avoid moving flank pawns in the opening
        for move in legal_moves:
            if not (board.piece_at(move.from_square) and 
                    board.piece_at(move.from_square).piece_type == chess.PAWN and
                    chess.square_file(move.from_square) in [0, 1, 6, 7]):  # a, b, g, h files
                return move
                
        return None  # Let regular search decide
        
    def apply_black_opening_principles(self, board):
        """Apply basic opening principles for black"""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
            
        # First move preferences: e5 or d5 (respond to e4/d4)
        if len(board.move_stack) == 1:
            last_move = board.move_stack[0]
            if last_move.to_square == chess.E4:
                # Respond to e4 with e5
                move = chess.Move.from_uci("e7e5")
                if move in legal_moves:
                    return move
            elif last_move.to_square == chess.D4:
                # Respond to d4 with d5
                move = chess.Move.from_uci("d7d5")
                if move in legal_moves:
                    return move
        
        # Develop knights before bishops
        knight_moves = []
        for move in legal_moves:
            if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type == chess.KNIGHT:
                from_rank = chess.square_rank(move.from_square)
                from_file = chess.square_file(move.from_square)
                # Knight from starting position to good development square
                if from_rank == 7 and (from_file == 1 or from_file == 6):  # b8 or g8
                    to_rank = chess.square_rank(move.to_square)
                    to_file = chess.square_file(move.to_square)
                    # Good knight development squares (c6, f6)
                    if to_rank == 5 and (to_file == 2 or to_file == 5):
                        return move
                    # Also accept d7, e7 as development
                    if to_rank == 6 and (to_file == 3 or to_file == 4):
                        knight_moves.append(move)
        
        # If we found any reasonable knight development moves, use one
        if knight_moves:
            return random.choice(knight_moves)
            
        # Develop center pawns if not moved yet
        for from_square in [chess.E7, chess.D7]:
            if board.piece_at(from_square) and board.piece_at(from_square).piece_type == chess.PAWN:
                push1 = chess.Move(from_square, from_square - 8)  # One square push
                push2 = chess.Move(from_square, from_square - 16)  # Two square push
                if push2 in legal_moves:
                    return push2
                elif push1 in legal_moves:
                    return push1
                    
        # Avoid moving flank pawns in the opening
        for move in legal_moves:
            if not (board.piece_at(move.from_square) and 
                    board.piece_at(move.from_square).piece_type == chess.PAWN and
                    chess.square_file(move.from_square) in [0, 1, 6, 7]):  # a, b, g, h files
                return move
                
        return None  # Let regular search decide

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
