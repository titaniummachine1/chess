"""
Unit tests for the DrawbackBot chess engine
"""
import unittest
import chess
import sys
import os

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from AI.drawback_Bot import DrawbackBot, best_move
from AI.search_utils import negamax, quiescence_search
from AI.ai_utils import MAX_DEPTH
from GameState.movegen import DrawbackBoard

class TestDrawbackBot(unittest.TestCase):
    """Test cases for the DrawbackBot chess engine"""

    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        self.engine = DrawbackBot()

    def test_initialization(self):
        """Test that the engine initializes correctly"""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.nodes, 0)
        self.assertEqual(len(self.engine.tt), 0)
        self.assertEqual(len(self.engine.history), 0)
        self.assertEqual(len(self.engine.killers), MAX_DEPTH + 1)
        
    def test_evaluation(self):
        """Test basic position evaluation"""
        score = self.engine.evaluate_position(self.board)
        # Starting position should be roughly equal
        self.assertAlmostEqual(score, 0, delta=50)
        
        # Test a position with material advantage - remove black pieces
        self.board.remove_piece_at(chess.E7)  # Remove black pawn
        self.board.remove_piece_at(chess.D7)  # Remove another black pawn
        self.board.remove_piece_at(chess.D8)  # Remove black queen
        score = self.engine.evaluate_position(self.board)
        # White should be significantly ahead
        self.assertGreater(score, 80)
        
    def test_quiescence_search(self):
        """Test quiescence search with a capturing sequence"""
        # Set up a position with a capturing sequence
        self.board = DrawbackBoard("r1bqkbnr/ppp2ppp/2n5/3pp3/3PP3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 4")
        
        # Test that quiescence search returns a valid score
        score = quiescence_search(self.engine, self.board, -10000, 10000)
        self.assertIsNotNone(score)
        
    def test_king_capture_detection(self):
        """Test detection of king captures"""
        # Set up a clear board
        self.board = DrawbackBoard()
        self.board.clear()
        
        # Place only white queen and black king for a direct capture
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        self.board.set_piece_at(chess.E7, chess.Piece(chess.QUEEN, chess.WHITE))
        
        self.board.turn = chess.WHITE
        
        # This position should immediately detect king capture in quiescence
        score = quiescence_search(self.engine, self.board, -10000, 10000)
        # Should detect mate
        self.assertGreater(score, 9000)
        
    def test_atomic_bomb_detection(self):
        """Test detection of atomic bomb drawback win"""
        # Create a board with the atomic bomb setup
        self.board = DrawbackBoard()
        self.board.clear()  # Start with a clear board
        
        # Set up a position with king and a piece adjacent to it
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        self.board.set_piece_at(chess.D7, chess.Piece(chess.PAWN, chess.BLACK))
        
        # Place kings required for valid position
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        
        # Place attacking piece
        self.board.set_piece_at(chess.D4, chess.Piece(chess.QUEEN, chess.WHITE))
        
        # Set drawback for black
        self.board.set_black_drawback("atomic_bomb")
        
        # Set white to move
        self.board.turn = chess.WHITE
        
        # Get the best move
        move = best_move(self.board, 2, 0)
        
        # Should find the queen capturing the pawn adjacent to king (Qd4xd7)
        self.assertIsNotNone(move)
        self.assertEqual(move.from_square, chess.D4)
        self.assertEqual(move.to_square, chess.D7)
        
    def test_negamax_search(self):
        """Test negamax search returns a valid move"""
        # Test with the starting position
        self.board = DrawbackBoard()
        score = negamax(self.engine, self.board, 2, -10000, 10000)
        self.assertIsNotNone(score)
        
    def test_book_move_bonus(self):
        """Test that search with book move bonuses returns a valid move"""
        # Create a test position with simple pawn openings
        self.board = DrawbackBoard()
        
        # Add book move bonuses to the engine
        self.engine.book_move_bonuses = {}
        e4_move = chess.Move.from_uci("e2e4")
        self.engine.book_move_bonuses[e4_move] = 100  # Strong bonus
        
        # Use the best_move function which guarantees a move
        move = best_move(self.board, 1, 0)  # Use best_move with depth 1, no book
        
        # Just verify that a valid move is returned
        self.assertIsNotNone(move)
        self.assertIn(move, self.board.legal_moves)

    def test_best_move_function(self):
        """Test the best_move function returns a valid move"""
        self.board = DrawbackBoard()
        move = best_move(self.board, 2, 0)
        
        # Should return a valid move
        self.assertIsNotNone(move)
        self.assertIn(move, self.board.legal_moves)

if __name__ == '__main__':
    unittest.main() 