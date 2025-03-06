"""
Unit tests for the move generation module
"""
import unittest
import chess
import sys
import os

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from GameState.movegen import DrawbackBoard, get_legal_moves

class TestMoveGeneration(unittest.TestCase):
    """Test cases for the move generation module"""
    
    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        
    def test_board_initialization(self):
        """Test that DrawbackBoard initializes correctly"""
        # Should start with the standard chess position
        self.assertEqual(self.board.fen().split()[0], chess.STARTING_FEN.split()[0])
        
        # Should have drawbacks initialized
        self.assertGreater(len(self.board.drawbacks), 0)
        
    def test_legal_moves_generator(self):
        """Test that legal_moves returns a LegalMoveGenerator instance"""
        self.assertIsInstance(self.board.legal_moves, LegalMoveGenerator)
        
    def test_legal_moves_iteration(self):
        """Test that legal_moves can be iterated over"""
        moves = list(self.board.legal_moves)
        
        # In starting position, there should be 20 legal moves
        self.assertEqual(len(moves), 20)
        
        # Each move should be a chess.Move
        for move in moves:
            self.assertIsInstance(move, chess.Move)
            
    def test_legal_moves_contains(self):
        """Test that 'in' operator works on legal_moves"""
        # e2e4 is a valid move in the starting position
        e2e4 = chess.Move.from_uci("e2e4")
        self.assertIn(e2e4, self.board.legal_moves)
        
        # e2e5 is not a valid move in the starting position
        e2e5 = chess.Move.from_uci("e2e5")
        self.assertNotIn(e2e5, self.board.legal_moves)
        
    def test_move_generation_after_move(self):
        """Test move generation after making a move"""
        # Make a move
        e2e4 = chess.Move.from_uci("e2e4")
        self.board.push(e2e4)
        
        # Check legal moves for black
        moves = list(self.board.legal_moves)
        
        # Should have expected number of moves
        self.assertEqual(len(moves), 20)
        
        # Some expected moves should be there
        e7e5 = chess.Move.from_uci("e7e5")
        self.assertIn(e7e5, self.board.legal_moves)
        
    def test_push_and_pop(self):
        """Test push and pop with the board stack"""
        # Initial state
        initial_fen = self.board.fen()
        
        # Make a move
        e2e4 = chess.Move.from_uci("e2e4")
        self.board.push(e2e4)
        
        # Board should be different now
        self.assertNotEqual(self.board.fen(), initial_fen)
        
        # Pop the move
        self.board.pop()
        
        # Board should be back to initial state
        self.assertEqual(self.board.fen(), initial_fen)
        
    def test_pseudo_legal_moves(self):
        """Test pseudo-legal move generation"""
        # In the initial position, pseudo-legal moves should equal legal moves
        legal_moves = list(self.board.legal_moves)
        pseudo_legal_moves = list(self.board.generate_pseudo_legal_moves())
        
        self.assertEqual(len(legal_moves), len(pseudo_legal_moves))
        
        # Set up a position where king is in check
        self.board.clear()
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        self.board.set_piece_at(chess.D2, chess.Piece(chess.PAWN, chess.WHITE))
        self.board.set_piece_at(chess.F5, chess.Piece(chess.QUEEN, chess.BLACK))
        self.board.turn = chess.WHITE
        
        # Pseudo-legal moves should include moves that don't get out of check
        pseudo_legal_moves = list(self.board.generate_pseudo_legal_moves())
        legal_moves = list(self.board.legal_moves)
        
        # There should be more pseudo-legal moves than legal ones
        self.assertGreater(len(pseudo_legal_moves), len(legal_moves))
        
    def test_move_generation_in_check(self):
        """Test move generation when king is in check"""
        # Set up a position where king is in check
        self.board.clear()
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        self.board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        self.board.set_piece_at(chess.F5, chess.Piece(chess.QUEEN, chess.BLACK))
        self.board.turn = chess.WHITE
        
        # King should be in check
        self.assertTrue(self.board.is_check())
        
        # Get legal moves
        legal_moves = list(self.board.legal_moves)
        
        # Should only have moves that get out of check
        for move in legal_moves:
            # Make the move
            self.board.push(move)
            # Should no longer be in check
            self.assertFalse(self.board.is_check())
            # Undo the move
            self.board.pop()
            
    def test_move_generation_checkmate(self):
        """Test move generation in a checkmate position"""
        # Set up a checkmate position (fool's mate)
        self.board = DrawbackBoard()
        self.board.push(chess.Move.from_uci("f2f3"))
        self.board.push(chess.Move.from_uci("e7e5"))
        self.board.push(chess.Move.from_uci("g2g4"))
        self.board.push(chess.Move.from_uci("d8h4"))
        
        # Should be checkmate
        self.assertTrue(self.board.is_checkmate())
        
        # No legal moves
        legal_moves = list(self.board.legal_moves)
        self.assertEqual(len(legal_moves), 0)
        
    def test_move_generation_stalemate(self):
        """Test move generation in a stalemate position"""
        # Set up a stalemate position
        self.board.clear()
        self.board.set_piece_at(chess.A8, chess.Piece(chess.KING, chess.BLACK))
        self.board.set_piece_at(chess.C6, chess.Piece(chess.QUEEN, chess.WHITE))
        self.board.set_piece_at(chess.C7, chess.Piece(chess.KING, chess.WHITE))
        self.board.turn = chess.BLACK
        
        # Should be stalemate
        self.assertTrue(self.board.is_stalemate())
        
        # No legal moves
        legal_moves = list(self.board.legal_moves)
        self.assertEqual(len(legal_moves), 0)
        
    def test_generation_with_drawbacks(self):
        """Test that move generation works correctly with drawbacks"""
        # We'll use the standard starting position and make sure all normal moves are available
        self.board = DrawbackBoard()
        
        # Get all legal moves
        legal_moves = list(self.board.legal_moves)
        
        # Normal chess should have 20 moves in the starting position
        self.assertEqual(len(legal_moves), 20)
        
        # Make sure common opening moves are available
        common_openings = ["e2e4", "d2d4", "g1f3", "b1c3"]
        for opening in common_openings:
            self.assertIn(chess.Move.from_uci(opening), legal_moves)
            
    def test_legal_move_generator_len(self):
        """Test that len() works on LegalMoveGenerator"""
        # Starting position has 20 legal moves
        self.assertEqual(len(self.board.legal_moves), 20)
        
        # Make a move
        self.board.push(chess.Move.from_uci("e2e4"))
        
        # Black should have 20 legal moves in response
        self.assertEqual(len(self.board.legal_moves), 20)
        
        # Make another move
        self.board.push(chess.Move.from_uci("e7e5"))
        
        # White should have 29 legal moves now
        self.assertEqual(len(self.board.legal_moves), 29)

class TestLegalMoveGenerator(unittest.TestCase):
    """Test cases specific to the LegalMoveGenerator class"""
    
    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        self.generator = LegalMoveGenerator(self.board)
        
    def test_iteration(self):
        """Test iteration over the generator"""
        moves = list(self.generator)
        
        # Starting position has 20 legal moves
        self.assertEqual(len(moves), 20)
        
    def test_contains(self):
        """Test the contains operation"""
        # e2e4 is a valid move in the starting position
        e2e4 = chess.Move.from_uci("e2e4")
        self.assertIn(e2e4, self.generator)
        
        # e2e5 is not a valid move in the starting position
        e2e5 = chess.Move.from_uci("e2e5")
        self.assertNotIn(e2e5, self.generator)
        
    def test_len(self):
        """Test the len() operation"""
        # Starting position has 20 legal moves
        self.assertEqual(len(self.generator), 20)

if __name__ == '__main__':
    unittest.main() 