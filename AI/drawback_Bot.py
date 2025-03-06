"""
Drawback Bot - A custom chess engine designed specifically for Drawback Chess.
Uses the DrawbackBoard move generation and optimized for the unique rules of Drawback Chess.
Core engine logic with improved win/loss detection.
"""
import chess
import time
import random
from collections import namedtuple
from GameState.movegen import DrawbackBoard
from AI.evaluation import evaluate_position as eval_position
from AI.piece_square_table import PIECE_VALUES
from AI.search_utils import quiescence_search, negamax, Entry

# Safe imports to avoid circular references
try:
    from AI.book_parser import is_book_position
except ImportError:
    # Define a fallback function if module not available
    def is_book_position(board):
        return False

from AI.ai_utils import MATE_LOWER, MATE_UPPER, MAX_DEPTH, BOOK_MOVE_BONUS, BOOK_MOVE_BONUS_REGULAR

# Global variables to track current best move and score
current_best_move = None
current_best_score = None

class DrawbackBot:
    """Custom chess engine designed specifically for Drawback Chess rules"""
    
    def __init__(self):
        self.nodes = 0
        self.tt = {}  # Transposition table
        self.history = {}  # Move history heuristic
        self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]  # Killer moves - stores UCI strings, not Move objects
        self.eval_cache = {}  # Cache for position evaluations
        self.book_move_bonuses = {}  # Book move bonuses in centipawns (uses UCI strings as keys)
        self.depth = 0  # Current search depth - will be updated during search
        
    def evaluate_position(self, board, drawbacks=None):
        """Enhanced evaluation function that considers drawbacks"""
        # Check if the position is a variant loss due to drawbacks
        if board.is_variant_loss():
            return -MATE_UPPER  # Return worst possible score
            
        # Get active drawback for current side
        active_drawback = board.get_active_drawback(board.turn)
        
        # Initialize evaluation components
        mobility_score = 0
        safety_score = 0
        
        # Calculate mobility with consideration for active drawbacks
        if active_drawback:
            # Count legal moves - heavily penalize positions with few moves
            legal_moves = list(board.legal_moves)
            legal_count = len(legal_moves)
            
            if legal_count == 0:
                return -MATE_UPPER  # No legal moves is a loss
            
            # Calculate mobility score based on move count
            mobility_score = min(150, legal_count * 5)  # Cap at 150 to avoid overvaluing
            
            # Additional evaluations for specific drawbacks
            if active_drawback == "covering_fire":
                # Count how many pieces can be captured with covering fire
                capturable_count = 0
                for move in legal_moves:
                    if board.is_capture(move):
                        capturable_count += 1
                
                # Bonus for having more potential captures
                mobility_score += capturable_count * 10
            
            elif active_drawback == "punching_down":
                # Count how many safe captures of lower-value pieces
                safe_captures = 0
                for move in legal_moves:
                    if board.is_capture(move):
                        victim = board.piece_at(move.to_square)
                        aggressor = board.piece_at(move.from_square)
                        if victim and aggressor and victim.piece_type < aggressor.piece_type:
                            safe_captures += 1
                
                # Bonus for having pieces that can capture lower-value targets
                mobility_score += safe_captures * 15
        else:
            mobility_score = 0
        
        # Calculate king safety based on surrounding squares and attackers
        king_square = None
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.KING and piece.color == board.turn:
                king_square = square
                break
        
        if king_square:
            # Calculate king safety based on surrounding squares and attackers
            attackers = board.attackers(not board.turn, king_square)
            defenders = board.attackers(board.turn, king_square)
            
            # Penalty for each attacker, bonus for each defender
            safety_score = (len(defenders) - len(attackers)) * 30
        
        # Use regular evaluation + mobility and safety bonuses
        regular_eval = eval_position(board, drawbacks)
        
        return regular_eval + mobility_score + safety_score
        
    def search(self, board, depth, time_limit=None, use_smart_time_management=False):
        """
        Search for the best move in the current position to the specified depth.
        Delegates to the negamax function for the actual search.
        
        Args:
            board: Current position
            depth: Search depth
            time_limit: Optional time limit in seconds
            use_smart_time_management: If True, yield early if best move is stable
                and reset time when a new best move is found
            
        Returns:
            Tuple of (score, best_move)
        """
        global current_best_move, current_best_score
        
        # Reset global tracking variables
        current_best_move = None
        current_best_score = None
        
        # Reset node counter
        self.nodes = 0
        
        # Reset cached data for new search
        self.tt = {}
        self.history = {}
        self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]  # Reset killers for all depths
        self.eval_cache = {}
        
        # Starting values for search
        best_move = None
        best_score = -MATE_UPPER
        start_overall = time.time()
        
        # Smart time management variables
        last_best_move = None
        stable_move_start_time = None
        stable_move_threshold = 10.0  # Seconds to wait before accepting a stable move
        
        # Set initial depth attribute for move_value function
        self.depth = 0  # Start at 0, will be updated in the loop
        
        # Ensure we have a reasonable time limit
        if time_limit is None or time_limit <= 0:
            time_limit = 5.0  # Default to 5 seconds
        
        print(f"Starting iterative deepening search with max depth {depth} and time limit {time_limit}s")
        
        try:
            for current_depth in range(1, depth + 1):
                # Update depth attribute for killer moves in move_value
                self.depth = current_depth
                
                start_time = time.time()
                
                # More generous time allocation - allow using up to 95% of time limit
                elapsed_overall = time.time() - start_overall
                if elapsed_overall > time_limit * 0.95:  # Use 95% of time limit as cutoff
                    print(f"Time limit approaching after depth {current_depth-1}, stopping search")
                    break
                    
                # Calculate remaining time for this depth - allow more time for deeper depths
                # Give at least 25% of remaining time to the current depth
                remaining_time = max(0.2, time_limit - elapsed_overall)
                time_for_depth = max(remaining_time * 0.25, 0.2)
                
                # Use aspiration windows for deeper searches
                if current_depth >= 3:
                    # Start with previous best score plus a small window
                    alpha = max(-MATE_UPPER, best_score - 50)
                    beta = min(MATE_UPPER, best_score + 50)
                    
                    # First attempt with narrow window
                    try:
                        score = negamax(self, board, current_depth, alpha, beta, start_time=start_overall, time_limit=time_limit)
                        
                        # If score outside window, re-search with full window
                        if score <= alpha or score >= beta:
                            # Check time limit again before researching
                            if time.time() - start_overall > time_limit * 0.98:
                                print(f"Time limit nearly reached during aspiration window retry at depth {current_depth}")
                                break
                                
                            alpha = -MATE_UPPER
                            beta = MATE_UPPER
                            score = negamax(self, board, current_depth, alpha, beta, start_time=start_overall, time_limit=time_limit)
                    except TimeoutError:
                        print(f"Search timed out at depth {current_depth}")
                        break
                    except Exception as e:
                        print(f"Error in search at depth {current_depth}: {e}")
                        # If an error occurs, use previous best move/score and continue
                        continue
                else:
                    # Full window for shallow searches
                    try:
                        score = negamax(self, board, current_depth, -MATE_UPPER, MATE_UPPER, start_time=start_overall, time_limit=time_limit)
                    except TimeoutError:
                        print(f"Search timed out at depth {current_depth}")
                        break
                    except Exception as e:
                        print(f"Error in search at depth {current_depth}: {e}")
                        # If an error occurs, use previous best move/score and continue
                        continue
                
                # Get the best move from the transposition table
                current_best_move_local = None
                
                # Look for the best move in the tt
                pos_key = self.get_position_key(board)
                if pos_key in self.tt:
                    entry = self.tt[pos_key]
                    if entry.move:
                        # Convert UCI string to Move object
                        entry_move_uci = entry.move
                        for legal_move in board.legal_moves:
                            if legal_move.uci() == entry_move_uci:
                                current_best_move_local = legal_move
                                break
                
                # Calculate search time for this iteration
                elapsed = time.time() - start_time
                total_elapsed = time.time() - start_overall
                
                # Update best move and score
                if current_best_move_local:
                    # Smart time management: Check if move has changed
                    if use_smart_time_management and current_depth >= 3:
                        if current_best_move_local == last_best_move:
                            # Move is stable from previous iteration
                            if stable_move_start_time is None:
                                # First time this move is stable
                                stable_move_start_time = time.time()
                                print(f"Found stable move: {current_best_move_local.uci()}, starting stability clock")
                            else:
                                # Move has been stable for a while
                                stable_duration = time.time() - stable_move_start_time
                                if stable_duration >= stable_move_threshold:
                                    print(f"Best move {current_best_move_local.uci()} has been stable for {stable_duration:.2f}s, early termination")
                                    break
                        else:
                            # Move changed, reset stability timer and extend search time by resetting start_overall
                            stable_move_start_time = None
                            if last_best_move is not None:  # Only if we had a previous best move
                                print(f"New best move found: {current_best_move_local.uci()}, extending search time")
                                start_overall = time.time()  # Reset the overall time to extend search
                                
                                # Update global tracking variables for external access - important for time extension
                                current_best_move = current_best_move_local
                                current_best_score = score
                    
                    # Remember this move for stability tracking
                    last_best_move = current_best_move_local
                    best_move = current_best_move_local
                    best_score = score
                    
                    # Always update global variables with the current best move
                    current_best_move = best_move
                    current_best_score = best_score
                    
                    # Report progress
                    print(f"Depth: {current_depth}, Score: {score:.2f}, Nodes: {self.nodes}, Best move: {best_move.uci()}, Time: {elapsed:.2f}s")
                
                # Check if we've completed the max depth
                if current_depth == depth:
                    print(f"Search completed in {total_elapsed:.2f}s, final best move: {best_move.uci()}")
                
                # If using smart time management and we've reached a sufficient depth,
                # consider stopping if time is nearly up
                if use_smart_time_management and current_depth >= 4:
                    if total_elapsed > time_limit * 0.80:
                        print(f"Using smart time management to stop at depth {current_depth} after {total_elapsed:.2f}s")
                        break
        except Exception as e:
            print(f"Fatal error in search: {e}")
            import traceback
            traceback.print_exc()
        
        # Reset depth attribute to avoid confusing future searches
        self.depth = 0
        
        # If we still don't have a move, try to get one from the transposition table
        if best_move is None:
            # Look for any move in the transposition table
            for key, entry in self.tt.items():
                if entry.move:
                    # Convert UCI string to Move object
                    entry_move_uci = entry.move
                    for legal_move in board.legal_moves:
                        if legal_move.uci() == entry_move_uci:
                            best_move = legal_move
                            best_score = entry.value
                            print(f"Using fallback move from transposition table: {entry_move_uci}")
                            break
                    if best_move:  # Break outer loop if move found
                        break
        
        # If still no move found from transposition table, pick the first legal move
        if best_move is None:
            legal_moves = list(board.legal_moves)
            if legal_moves:
                best_move = legal_moves[0]
                best_score = 0  # Neutral score for fallback move
                print(f"No move found in search, using first legal move: {best_move.uci()}")
        
        # Report final search results
        elapsed_total = time.time() - start_overall
        print(f"Search completed in {elapsed_total:.2f}s, final best move: {best_move.uci() if best_move else 'None'}")
        
        return best_score, best_move
        
    def check_terminal_state(self, board):
        """Check for terminal state conditions in Drawback Chess"""
        # No legal moves - stalemate or checkmate
        if not any(True for _ in board.legal_moves):
            return True
        
        # Check for variant loss due to drawbacks
        if board.is_variant_loss():
            return True
            
        # Check for king capture on next move - terminal state
        for move in board.legal_moves:
            target = board.piece_at(move.to_square)
            if target and target.piece_type == chess.KING:
                return True
                
        return False
        
    def get_book_move(self, board):
        """
        Get a move from the opening book if available, considering drawbacks.
        This is used only to guide search, not to directly play moves.
        """
        try:
            from AI.book_handler import BookMoveSelector
            
            # Get the active drawback for current player
            active_drawback = board.get_active_drawback(board.turn)
            
            # Create a book selector instance
            book_selector = BookMoveSelector()
            
            # If we have a drawback, use weighted selection with drawback consideration
            if active_drawback:
                # Get weighted book moves with drawback info
                book_move_result = book_selector.get_weighted_book_move(board)
                
                if book_move_result and book_move_result[0]:
                    move = book_move_result[0]
                    info = book_move_result[1] if len(book_move_result) > 1 else None
                    
                    # Store the move bonuses for search if we need to fall back
                    # But convert Move objects to UCI strings
                    if info and "book_move_bonuses" in info:
                        # Convert Move objects to UCI strings for the book_move_bonuses
                        self.book_move_bonuses = {}
                        for bmove, bonus in info["book_move_bonuses"].items():
                            self.book_move_bonuses[bmove.uci()] = bonus
                        
                    print(f"Found drawback-adjusted book move: {move.uci()} (will use to guide search)")
                    return move
            
            # If no drawback or no weighted move found, fall back to standard book move
            book_move_result = book_selector.get_weighted_book_move(board)
            if book_move_result and book_move_result[0]:
                move = book_move_result[0]
                info = book_move_result[1] if len(book_move_result) > 1 else None
                
                # Store the move bonuses for search as UCI strings
                if info and "book_move_bonuses" in info:
                    self.book_move_bonuses = {}
                    for bmove, bonus in info["book_move_bonuses"].items():
                        self.book_move_bonuses[bmove.uci()] = bonus
                    
                print(f"Found standard book move: {move.uci()} (will use to guide search)")
                return move
            
        except ImportError:
            print("Book handler not available")
            pass
        except Exception as e:
            print(f"Error getting book move: {e}")
        return None
        
    def get_best_move(self, board, depth=3, use_book=True):
        """Get the best move from the current position with drawback considerations"""
        # First, check for terminal state
        if self.check_terminal_state(board):
            print("Terminal state detected")
            return None
            
        # Get active drawback
        active_drawback = board.get_active_drawback(board.turn)
        
        # Find book moves to guide search, but never play them directly
        book_move = None
        if use_book:
            book_move = self.get_book_move(board)
            if book_move:
                # Check that the book move complies with drawback restrictions
                if active_drawback and board._is_drawback_illegal(book_move, board.turn):
                    print(f"Book move {book_move.uci()} incompatible with drawback: {active_drawback}")
                    book_move = None
                    # Clear book move bonuses
                    self.book_move_bonuses = {}
                else:
                    # Don't return book move - just save it to guide search
                    print(f"Book move will guide search but not be played directly")
                
        # Mark the board for search
        if hasattr(board, "_in_search"):
            board._in_search = True
            
        # Fall back to search
        if active_drawback:
            print(f"Searching with active drawback: {active_drawback}")
        else:
            print(f"Searching with no drawback restrictions")
        
        # Ensure depth is at least 1
        search_depth = max(1, depth)
        print(f"Starting search at depth {search_depth}")
        
        # Always perform the search, even with book moves
        score, move = self.search(board, search_depth)
        
        # Reset search flag
        if hasattr(board, "_in_search"):
            board._in_search = False
            
        # If no move was found, find a legal move
        if not move:
            print("Warning: No best move found! Selecting safest available move...")
            # Just return any legal move - preferably one that doesn't lose a piece
            moves = list(board.legal_moves)
            if moves:
                # Sort moves by safety (non-captures first)
                safe_moves = []
                other_moves = []
                
                for m in moves:
                    # Prefer moves that don't put our pieces in danger
                    if not board.is_capture(m):
                        # Check if the move puts the piece in danger
                        board_copy = board.copy()
                        try:
                            board_copy.push(m)
                            # Check if the moved piece is under attack
                            is_safe = True
                            target_piece = board_copy.piece_at(m.to_square)
                            
                            if target_piece:
                                attackers = board_copy.attackers(not board.turn, m.to_square)
                                defenders = board_copy.attackers(board.turn, m.to_square)
                                
                                # If more attackers than defenders, the move is unsafe
                                if len(attackers) > len(defenders):
                                    is_safe = False
                                    
                            if is_safe:
                                safe_moves.append(m)
                            else:
                                other_moves.append(m)
                        except Exception:
                            # If error occurs, consider it other move
                            other_moves.append(m)
                    else:
                        # Captures go to other moves - we'll only use them if no safe moves
                        other_moves.append(m)
                
                # Return safe moves if available, otherwise any legal move
                if safe_moves:
                    selected_move = random.choice(safe_moves)
                    print(f"Selected safe move: {selected_move.uci()}")
                    return selected_move
                    
                selected_move = random.choice(other_moves)
                print(f"Selected fallback move: {selected_move.uci()}")
                return selected_move
            return None
            
        print(f"Search complete. Chosen move: {move.uci()}")
        return move
    
    def get_position_key(self, board):
        """Get a unique key for the position, preferring Zobrist hash if available."""
        if hasattr(board, 'zobrist_hash'):
            return board.zobrist_hash()
        else:
            return str(board.fen())

def best_move(board, depth=3, time_limit=5, book_move_bonuses=None):
    """
    Convenience function to get the best move without creating an engine instance.
    
    Args:
        board: Current position
        depth: Search depth
        time_limit: Time limit in seconds
        book_move_bonuses: Dictionary of book moves with their bonus values
        
    Returns:
        Best move object or None if no move available
    """
    engine = DrawbackBot()
    
    # If book move bonuses are provided, set them in the engine
    if book_move_bonuses:
        engine.book_move_bonuses = book_move_bonuses
        
    # Ensure depth and time_limit are valid
    depth = max(1, depth)
    time_limit = max(0.5, time_limit)
    
    print(f"Starting search with depth {depth} and time limit {time_limit}s")
    
    # Convert time_limit to a simple use_book flag for compatibility
    use_book = time_limit > 0
    
    return engine.get_best_move(board, depth, use_book) 