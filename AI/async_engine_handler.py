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
        
        # Check opening book first
        book_moves = OPENING_BOOK.get_book_moves(board)
        if book_moves:
            # Sort by frequency
            book_moves.sort(key=lambda x: x[1], reverse=True)
            best_book_move = book_moves[0][0]
            print(f"Selected book move: {best_book_move.uci()}")
            return best_book_move
            
        # Check opening principles if not in book but early game
        if board.fullmove_number <= 10:
            principle_move = get_opening_principle_move(board, drawbacks)
            if principle_move:
                side = "White" if board.turn else "Black"
                print(f"Using opening principle move for {side}: {principle_move.uci()}")
                return principle_move
        
        # Create and run the search task
        print(f"Created new search task at depth {depth}")
        task = asyncio.create_task(self._search_task(board, depth, drawbacks))
        self.current_task = task
        
        try:
            best_move = await task
            print(f"Search task finished")
            return best_move
        except asyncio.CancelledError:
            print("Search task was cancelled")
            # Return a valid move if search was interrupted
            return self._get_emergency_move(board, drawbacks)
    
    def stop(self):
        """Stop the current search"""
        self.stop_search = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
    
    async def _search_task(self, board, depth, drawbacks):
        """Asynchronous task to search for the best move"""
        print(f"Search started at depth {depth}")
        
        # Run the search in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        best_move = await loop.run_in_executor(
            self.executor, 
            self._search_position, 
            board, depth, drawbacks
        )
        
        print(f"Search completed, found move: {best_move.uci()}")
        return best_move
    
    def _search_position(self, board, depth, drawbacks):
        """Actual search implementation"""
        alpha = -CHECKMATE_SCORE
        beta = CHECKMATE_SCORE
        best_move = None
        best_score = -CHECKMATE_SCORE * 2
        
        # Get ordered moves with book moves prioritized
        ordered_moves = self._get_moves_with_book_priority(board, drawbacks)
        
        # Perform the search
        for move in ordered_moves:
            if self.stop_search:
                break
                
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, drawbacks)
            board.pop()
            
            if score > best_score:
                best_score = score
                best_move = move
            
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        
        # Fallback in case search was interrupted or no good move was found
        if best_move is None:
            return self._get_emergency_move(board, drawbacks)
            
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
        book_moves = OPENING_BOOK.get_book_moves(board)
        book_move_uci = [move.uci() for move, _ in book_moves]
        
        all_moves = list(board.legal_moves)
        
        # Sort moves with book moves first, then by standard ordering
        def move_order_key(move):
            if move.uci() in book_move_uci:
                return -1000  # Book moves come first
            return 0  # Other moves follow standard ordering
            
        all_moves.sort(key=move_order_key)
        return all_moves
    
    def _get_emergency_move(self, board, drawbacks):
        """Get a safe move when search is interrupted"""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
        
        # Try to find a capture or check first
        for move in legal_moves:
            if board.is_capture(move) or board.gives_check(move):
                return move
        
        # Otherwise return a random legal move
        return random.choice(legal_moves)
