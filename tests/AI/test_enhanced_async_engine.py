"""
Unit tests for the enhanced_async_engine module
"""
import unittest
import chess
import asyncio
import sys
import os
import time

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from AI.enhanced_async_engine import (
    run_search, start_search, get_result, is_search_complete, 
    reset_search, get_progress, AsyncEngineState, engine_state
)
from GameState.movegen import DrawbackBoard

class TestEnhancedAsyncEngine(unittest.TestCase):
    """Test cases for the enhanced_async_engine module"""

    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        # Reset the engine state before each test
        reset_search()
        
    def test_run_search(self):
        """Test run_search functionality directly"""
        move = run_search(self.board, depth=1, time_limit=1.0)
        
        # Should return a valid move
        self.assertIsNotNone(move)
        self.assertIn(move, self.board.legal_moves)
        
    def test_async_state_initialization(self):
        """Test AsyncEngineState initialization"""
        state = AsyncEngineState()
        
        # Check default values
        self.assertIsNone(state.current_search)
        self.assertEqual(state.current_progress, "Idle")
        self.assertIsNone(state.current_result)
        self.assertIsNotNone(state.search_executor)
        self.assertIsNone(state.start_time)
        self.assertEqual(state.depth, 0)
        self.assertEqual(state.time_limit, 0)
        
    def test_reset_state(self):
        """Test resetting the engine state"""
        # Set up a state
        engine_state.current_progress = "Testing"
        engine_state.start_time = time.time()
        engine_state.depth = 5
        engine_state.time_limit = 10
        
        # Reset state
        engine_state.reset()
        
        # Check that it was reset
        self.assertEqual(engine_state.current_progress, "Idle")
        self.assertIsNone(engine_state.current_result)
        self.assertIsNone(engine_state.start_time)
        self.assertEqual(engine_state.depth, 0)
        self.assertEqual(engine_state.time_limit, 0)
    
    async def helper_async_search_test(self):
        """Helper method for async search test"""
        board = DrawbackBoard()
        start_search(board, depth=1, time_limit=1.0)
        
        # Wait for search to complete
        for _ in range(10):  # Try for up to 10 seconds
            await asyncio.sleep(1)
            if is_search_complete():
                break
        
        # Check search completed
        self.assertTrue(is_search_complete())
        
        # Check results
        move = get_result()
        self.assertIsNotNone(move)
        self.assertIn(move, board.legal_moves)
        
    def test_async_search(self):
        """Test async search"""
        # Run the async helper method
        asyncio.run(self.helper_async_search_test())
        
    def test_get_progress(self):
        """Test progress reporting"""
        # Initial state
        self.assertEqual(get_progress(), "Idle")
        
        # Start a search
        start_search(self.board, depth=1, time_limit=1.0)
        
        # Progress should now indicate thinking
        progress = get_progress()
        self.assertIn("Thinking", progress)
        
        # Reset search
        reset_search()
        
        # Should be back to idle
        self.assertEqual(get_progress(), "Idle")
        
    def test_win_detection(self):
        """Test detection of winning moves in async search"""
        # Set up a position where a king capture is possible
        self.board = DrawbackBoard()
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        self.board.set_piece_at(chess.D7, None)  # Remove blocking pawn
        self.board.set_piece_at(chess.E7, chess.Piece(chess.QUEEN, chess.WHITE))
        self.board.turn = chess.WHITE
        
        # Run search
        move = run_search(self.board, depth=1, time_limit=1.0)
        
        # Should find the king capture
        self.assertIsNotNone(move)
        self.assertEqual(move.to_square, chess.E8)
        
    def test_time_limit_respect(self):
        """Test that time limits are respected"""
        start = time.time()
        move = run_search(self.board, depth=5, time_limit=0.2)
        elapsed = time.time() - start
        
        # Should not exceed time limit by too much (add margin for system overhead)
        self.assertLess(elapsed, 1.0)
        
        # Should return a valid move despite time constraint
        self.assertIsNotNone(move)
        self.assertIn(move, self.board.legal_moves)

if __name__ == '__main__':
    unittest.main() 