"""
Unified async handler for chess engines - combines functionality from all async modules and opening book
"""
import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
import random
import chess
from AI.drawback_sunfish import best_move as engine_best_move
from AI.book_parser import get_book_move, is_book_position, BOOK_MOVE_BONUS

# Global state for async search
current_search = None
current_progress = "Idle"
current_result = None
search_executor = ThreadPoolExecutor(max_workers=1)

# Simple opening book for standard openings
def get_opening_book_move(board):
    """Get standard opening moves for common starting positions"""
    if len(board.move_stack) == 0:
        # First moves as white
        if board.turn == chess.WHITE:
            for move_uci in ["e2e4", "d2d4"]:
                try:
                    move = chess.Move.from_uci(move_uci)
                    if move in board.legal_moves:
                        return move
                except ValueError:
                    pass
    elif len(board.move_stack) == 1:
        # First moves as black
        if board.turn == chess.BLACK:
            last_move = board.move_stack[-1]
            if last_move.uci() == "e2e4":
                e5 = chess.Move.from_uci("e7e5")
                if e5 in board.legal_moves:
                    return e5
            elif last_move.uci() == "d2d4":
                d5 = chess.Move.from_uci("d7d5")
                if d5 in board.legal_moves:
                    return d5
    
    return None

def run_search(board, depth, time_limit=5):
    """Run the engine search in a separate thread with opening book integration"""
    try:
        start_time = time.time()
        
        # Always use a copy of the board for thread safety
        board_copy = board.copy()
        
        # Check opening book first - but consider drawbacks 
        book_move = get_book_move(board_copy)
        if book_move and book_move in board_copy.legal_moves:  # Make sure the book move is actually legal with drawbacks
            print(f"Opening book move found: {book_move}")
            
            # Check if there's a better immediate move (like king capture)
            for move in board_copy.legal_moves:
                target = board_copy.piece_at(move.to_square)
                if target and target.piece_type == chess.KING:
                    print("Found king capture (checkmate)! Prioritizing over book move.")
                    return move
                    
            return book_move
        
        # Check for king captures (checkmates in Drawback Chess)
        for move in board_copy.legal_moves:
            target = board_copy.piece_at(move.to_square)
            if target and target.piece_type == chess.KING:
                print("Found king capture (checkmate)!")
                return move
                
        # Call the core engine search with the time limit
        print(f"Starting regular search at depth {depth}, time limit {time_limit}s")
        move = engine_best_move(board_copy, depth, time_limit)
        
        elapsed = time.time() - start_time
        print(f"Search completed in {elapsed:.2f}s, found move: {move}")
        
        return move
    except Exception as e:
        print(f"Engine search error: {e}")
        print(traceback.format_exc())
        
        # Emergency fallback
        try:
            legal_moves = list(board.legal_moves)
            if legal_moves:
                move = random.choice(legal_moves)
                print(f"Using emergency fallback move: {move}")
                return move
        except:
            pass
        return None

async def async_search(board, depth, time_limit=5):
    """Run the chess engine search asynchronously"""
    global current_progress, current_result
    current_progress = f"Searching at depth {depth}..."
    
    try:
        # Make a copy of the board for thread safety
        board_copy = board.copy()
        
        loop = asyncio.get_running_loop()
        current_result = await loop.run_in_executor(
            search_executor,
            lambda: run_search(board_copy, depth, time_limit)
        )
        
        if current_result:
            current_progress = "Search complete"
        else:
            current_progress = "No move found"
    except Exception as e:
        print(f"Search error: {str(e)}")
        current_progress = f"Search error: {str(e)}"
        current_result = None

def start_search(board, depth, time_limit=5):
    """Start a new async search task"""
    global current_search, current_progress
    
    # Cancel any existing search first
    if current_search and not current_search.done():
        current_search.cancel()
        print("Cancelled existing search")
        
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    current_search = asyncio.create_task(async_search(board, depth, time_limit))
    current_progress = f"Thinking at depth {depth}..."
    print(f"[DEBUG] Search task started successfully")

def get_progress():
    """Get the current search progress description"""
    return current_progress

def get_result():
    """Get the completed search result"""
    return current_result

def is_search_complete():
    """Check if the current search is complete"""
    return current_search is not None and current_search.done()

def reset_search():
    """Reset the search state"""
    global current_search, current_progress, current_result
    current_search = None
    current_progress = "Idle"
    current_result = None
