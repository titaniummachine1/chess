"""
Asynchronous chess engine handler that manages search tasks and integrates with the opening book.
"""
import asyncio
import chess
import time
import random
from concurrent.futures import ThreadPoolExecutor
from .book_parser import OPENING_BOOK
from .async_core import evaluate_position, get_ordered_moves, CHECKMATE_SCORE
from .book_parser import get_opening_principle_move

# Book move bonus in centipawns
BOOK_MOVE_BONUS = 100

class AsyncEngineHandler:
    """Handles asynchronous chess engine operations"""
    
    def __init__(self, engine_name="Unified Async Engine"):
        self.engine_name = engine_name
        self.current_task = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.stop_search = False
        
    async def get_best_move(self, board, depth=3, drawbacks=None):
        """Find the best move for the given position using async search"""
        self.stop_search = False
        
        print(f"[ENGINE] Starting search at depth {depth} with drawbacks: {drawbacks}")
        
        # Get book moves for logging and later bonus scoring
        book_moves = OPENING_BOOK.get_book_moves(board)
        if book_moves:
            book_moves_uci = [move.uci() for move, freq in book_moves]
            print(f"[ENGINE] Found book moves: {book_moves_uci}")
            
        # Check opening principles if early game
        principle_move = None
        if board.fullmove_number <= 10:
            principle_move = get_opening_principle_move(board, drawbacks)
            if principle_move:
                side = "White" if board.turn else "Black"
                print(f"[ENGINE] Found opening principle move for {side}: {principle_move.uci()}")
        
        # Create and run the search task
        print(f"[ENGINE] Creating search task at depth {depth}")
        task = asyncio.create_task(self._search_task(board, depth, drawbacks))
        self.current_task = task
        
        try:
            best_move = await task
            print(f"[ENGINE] Search completed successfully")
            # Print if the chosen move was from the book
            if best_move and book_moves and any(best_move == bm[0] for bm in book_moves):
                print(f"[ENGINE] Selected book move: {best_move.uci()} (with bonus evaluation)")
            return best_move
        except asyncio.CancelledError:
            print("[ENGINE] Search task was cancelled")
            # Return a valid move if search was interrupted
            return self._get_emergency_move(board, drawbacks)
    
    def stop(self):
        """Stop the current search"""
        self.stop_search = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
    
    async def _search_task(self, board, depth, drawbacks):
        """Asynchronous task to search for the best move"""
        print(f"[ENGINE] Search started at depth {depth}")
        
        # Run the search in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        best_move = await loop.run_in_executor(
            self.executor, 
            self._search_position, 
            board, depth, drawbacks
        )
        
        print(f"[ENGINE] Search completed, found move: {best_move.uci()}")
        return best_move
    
    def _search_position(self, board, depth, drawbacks):
        """Actual search implementation"""
        alpha = -CHECKMATE_SCORE
        beta = CHECKMATE_SCORE
        best_move = None
        best_score = -CHECKMATE_SCORE * 2
        
        # Get ordered moves with book moves prioritized
        ordered_moves = self._get_moves_with_book_priority(board, drawbacks)
        book_moves = {move.uci(): freq for move, freq in OPENING_BOOK.get_book_moves(board)}
        
        print(f"[ENGINE] Searching {len(ordered_moves)} moves at depth {depth}")
        
        # Perform the search
        for i, move in enumerate(ordered_moves):
            if self.stop_search:
                print("[ENGINE] Search stopped by request")
                break
                
            is_book_move = move.uci() in book_moves
            board.push(move)
            
            # Search with negamax algorithm
            print(f"[ENGINE] Analyzing move {i+1}/{len(ordered_moves)}: {move.uci()}" + 
                  (" (book move)" if is_book_move else ""))
            
            score = -self._negamax(board, depth - 1, -beta, -alpha, drawbacks)
            
            # Apply book move bonus if applicable
            if is_book_move:
                score += BOOK_MOVE_BONUS
                print(f"[ENGINE] Book move {move.uci()} got bonus: {score}")
                
            board.pop()
            
            print(f"[ENGINE] Move {move.uci()} evaluated to score: {score}")
            
            if score > best_score:
                best_score = score
                best_move = move
                print(f"[ENGINE] New best move: {best_move.uci()} with score {best_score}")
            
            alpha = max(alpha, score)
            if alpha >= beta:
                print(f"[ENGINE] Alpha-beta cutoff at move {i+1}")
                break
        
        # Fallback in case search was interrupted or no good move was found
        if best_move is None:
            best_move = self._get_emergency_move(board, drawbacks)
            print(f"[ENGINE] Using emergency move: {best_move.uci()}")
            
        return best_move
    
    def _negamax(self, board, depth, alpha, beta, drawbacks):
        """Negamax algorithm with alpha-beta pruning"""
        # Check for terminal node or maximum depth
        if depth == 0 or board.is_game_over():
            return evaluate_position(board, drawbacks)
        
        best_score = -CHECKMATE_SCORE * 2
        ordered_moves = get_ordered_moves(board, drawbacks)
        
        for move in ordered_moves:
            if self.stop_search:
                break
                
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, drawbacks)
            board.pop()
            
            best_score = max(best_score, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
                
        return best_score
    
    def _get_moves_with_book_priority(self, board, drawbacks):
        """Get moves ordered with book moves first"""
        book_moves_with_freq = OPENING_BOOK.get_book_moves(board)
        book_move_dict = {move.uci(): freq for move, freq in book_moves_with_freq}
        
        all_moves = list(board.legal_moves)
        filtered_moves = []
        
        # Filter moves based on drawbacks
        for move in all_moves:
            # Check if move respects the drawbacks
            if self._is_valid_with_drawbacks(board, move, drawbacks):
                filtered_moves.append(move)
        
        # Sort moves with book moves first (by frequency), then other moves
        def move_order_key(move):
            if move.uci() in book_move_dict:
                # Higher frequency book moves come first (negative value)
                return -1000 - book_move_dict[move.uci()]  
            # Other moves are ordered by standard evaluation
            return 0
            
        filtered_moves.sort(key=move_order_key)
        
        if book_moves_with_freq:
            print(f"[ENGINE] Ordered moves with book moves first: {[m.uci() for m in filtered_moves[:5]]}...")
        
        return filtered_moves

    def _is_valid_with_drawbacks(self, board, move, drawbacks):
        """Check if a move is valid considering the active drawbacks"""
        if not drawbacks:
            return True
            
        # Get the moving piece
        piece = board.piece_at(move.from_square)
        if piece is None:
            return True
            
        piece_type = piece.piece_type
        is_capture = board.is_capture(move)
        
        # Check specific drawbacks
        if "no_knight_moves" in drawbacks and piece_type == chess.KNIGHT:
            return False
            
        if "no_knight_captures" in drawbacks and piece_type == chess.KNIGHT and is_capture:
            return False
            
        if "no_bishop_captures" in drawbacks and piece_type == chess.BISHOP and is_capture:
            return False
            
        # Add other drawback checks as needed
        
        return True
    
    def _get_emergency_move(self, board, drawbacks):
        """Get a safe move when search is interrupted"""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
        
        # Try to find a capture or check first
        for move in legal_moves:
            if board.is_capture(move) or board.gives_check(move):
                print(f"[ENGINE] Emergency move - found capture/check: {move.uci()}")
                return move
        
        # Otherwise return a random legal move
        random_move = random.choice(legal_moves)
        print(f"[ENGINE] Emergency move - using random move: {random_move.uci()}")
        return random_move
