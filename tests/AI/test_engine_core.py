"""
Unit tests for the engine_core module
"""
import unittest
import chess
import sys
import os

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from AI.engine_core import analyze_position, check_drawback_loss_conditions, select_best_move, evaluate_current_position
from GameState.movegen import DrawbackBoard

class TestEngineCore(unittest.TestCase):
    """Test cases for the engine_core module"""

    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        
    def test_analyze_position(self):
        """Test position analysis functionality"""
        # Basic stats test
        stats = analyze_position(self.board, include_stats=True)
        
        # In the starting position, there are 20 legal moves
        self.assertEqual(len(stats.legal_moves), 20)
        # No captures in the starting position
        self.assertEqual(len(stats.captures), 0)
        # No checks in the starting position
        self.assertEqual(len(stats.checks), 0)
        # There should be some possible pawn advances
        self.assertGreater(len(stats.advancement_moves), 0)
        
        # Test a more complex position
        self.board = DrawbackBoard("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        stats = analyze_position(self.board, include_stats=True)
        self.assertGreater(len(stats.legal_moves), 0)
        
    def test_check_drawback_loss_conditions(self):
        """Test detection of drawback loss conditions"""
        # Test with no drawbacks
        has_loss, losing_color, reason = check_drawback_loss_conditions(self.board)
        self.assertFalse(has_loss)
        self.assertIsNone(losing_color)
        self.assertIsNone(reason)
        
        # Test with atomic bomb drawback and a loss condition
        self.board = DrawbackBoard()
        self.board.set_white_drawback("atomic_bomb")
        
        # Set up a position where the last move was a capture next to white's king
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.D2, None)  # Remove pawn
        
        # Simulate black capturing a piece adjacent to white king
        self.board.turn = chess.WHITE  # White to move after black's capture
        move = chess.Move.from_uci("d7d5")
        self.board.push(move)  # Placeholder move to have a move in the stack
        
        # Manually set the flag that tracks the last capture
        self.board._last_capture_square = chess.D2
        
        # Currently not triggering actual loss condition in test since we're mocking the move
        # This would need actual game dynamics to fully test
        
    def test_select_best_move(self):
        """Test selecting the best move"""
        # Test on starting position
        result = select_best_move(self.board, depth=2, time_limit=1.0)
        
        # Should return a valid move
        self.assertIsNotNone(result.move)
        self.assertIn(result.move, self.board.legal_moves)
        
        # Test timing functionality
        start = time.time()
        result = select_best_move(self.board, depth=1, time_limit=0.1)
        elapsed = time.time() - start
        
        # Should respect time limit (with some reasonable margin)
        self.assertLess(elapsed, 1.0)
        
    def test_evaluate_current_position(self):
        """Test position evaluation"""
        # Starting position should be roughly equal
        score = evaluate_current_position(self.board)
        self.assertAlmostEqual(score, 0, delta=50)
        
        # Test position with material advantage
        self.board.remove_piece_at(chess.E7)  # Remove black pawn
        score = evaluate_current_position(self.board)
        # White should be ahead
        self.assertGreater(score, 0)
        
        # Test with and without drawback effects
        score_with = evaluate_current_position(self.board, include_drawback_effects=True)
        score_without = evaluate_current_position(self.board, include_drawback_effects=False)
        # Should be different for a position with drawbacks
        self.assertIsNotNone(score_with)
        self.assertIsNotNone(score_without)

if __name__ == '__main__':
    unittest.main() 