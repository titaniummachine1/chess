"""
Unit tests for the drawbacks module
"""
import unittest
import chess
import sys
import os

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from GameState.drawback_manager import (
    get_drawback_info, validate_drawback_info, DRAWBACKS,
    get_drawback_function, get_drawback_loss_function
)
from GameState.movegen import DrawbackBoard
from GameState.drawbacks import atomic_bomb

# Create a simple test drawback class
class TestDrawback:
    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    def make_move(self, board, move):
        return True
        
    def unmake_move(self, board, move):
        return True

class TestDrawbackBase(unittest.TestCase):
    """Test the drawback functionality"""
    
    def test_drawback_base_initialization(self):
        """Test that drawbacks can be initialized correctly"""
        drawback = TestDrawback("Test Drawback", "A test drawback")
        self.assertEqual(drawback.name, "Test Drawback")
        self.assertEqual(drawback.description, "A test drawback")
        
    def test_drawback_registry(self):
        """Test drawback registration and retrieval"""
        # Create a test drawback
        test_drawback_info = {
            "name": "Test Registry Drawback",
            "description": "A test for registry",
            "check_move": "test_check_function",
            "supported": True
        }
        
        # Register the drawback directly in DRAWBACKS dict
        DRAWBACKS["test_registry_drawback"] = test_drawback_info
        
        # Get drawback info
        retrieved = get_drawback_info("test_registry_drawback")
        
        # Check that our drawback is in the dictionary
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Test Registry Drawback")
        
        # Test get_drawback_function
        test_function = lambda board, move, color: False
        DRAWBACKS["test_registry_drawback"]["check_function"] = test_function
        self.assertEqual(get_drawback_function("test_registry_drawback"), test_function)
        
        # Unregister by removing from dictionary
        del DRAWBACKS["test_registry_drawback"]
        self.assertIsNone(get_drawback_info("test_registry_drawback"))
        
    def test_drawback_functionality(self):
        """Test general drawback functionality using atomic bomb as an example"""
        # Create a test board with a position suitable for testing
        board = DrawbackBoard()
        board.clear()
        
        # Place kings
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        
        # Place atomic bomb and a pawn
        board.set_piece_at(chess.D4, chess.Piece(chess.KNIGHT, chess.WHITE))  # Bomb
        board.set_piece_at(chess.C5, chess.Piece(chess.PAWN, chess.BLACK))
        
        # Test check_atomic_bomb function
        move = chess.Move(chess.E8, chess.D7)  # Move king
        result = atomic_bomb.check_atomic_bomb(board, move, chess.BLACK)
        self.assertFalse(result)  # Should be legal
        
        # Test king capture - should be illegal
        king_move = chess.Move(chess.E1, chess.D2)
        board.set_piece_at(chess.D2, chess.Piece(chess.PAWN, chess.BLACK))
        result = atomic_bomb.check_atomic_bomb(board, king_move, chess.WHITE)
        self.assertTrue(result)  # King capture is illegal
        
        # Test explosion loss condition
        # We need to set up the board's state to simulate a move that just happened
        board.turn = chess.WHITE  # White's turn (meaning black just moved)
        
        # Move king adjacent to capture
        board.set_piece_at(chess.E1, None)
        board.set_piece_at(chess.D3, chess.Piece(chess.KING, chess.WHITE))
        
        # Simulate recent capture next to king
        board._last_capture_square = chess.E3  # Adjacent to white king at D3
        board.move_stack.append(chess.Move(chess.F3, chess.E3))  # Add capture move to stack
        
        # Check explosion loss for white
        # Since we're checking for WHITE's loss, and it's WHITE's turn (black just captured),
        # this should detect the loss
        result = atomic_bomb.check_explosion_loss(board, chess.WHITE) 
        self.assertTrue(result)  # Should detect loss condition

class TestDrawbackIntegration(unittest.TestCase):
    """Test integration of drawbacks with DrawbackBoard"""
    
    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        
    def test_drawback_board_initialization(self):
        """Test that DrawbackBoard initializes with drawbacks"""
        # Board should have drawbacks registered
        self.assertGreater(len(DRAWBACKS), 0)
        
    def test_drawback_move_application(self):
        """Test that drawbacks are applied when making moves"""
        # Set up the board with a specific position for testing
        # Here we'll test with atomic bomb drawback
        self.board.clear()
        
        # Place kings
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        
        # Set an active drawback for black 
        self.board.set_white_drawback("atomic_bomb")
        
        # Place knight and a pawn
        self.board.set_piece_at(chess.D4, chess.Piece(chess.KNIGHT, chess.WHITE))
        self.board.set_piece_at(chess.C5, chess.Piece(chess.PAWN, chess.BLACK))
        
        # Set white to move
        self.board.turn = chess.WHITE
        
        # Regular moves should be legal
        self.assertIn(chess.Move(chess.D4, chess.F5), self.board.legal_moves)
        
        # Place a piece that could be captured by the white king
        self.board.set_piece_at(chess.F2, chess.Piece(chess.PAWN, chess.BLACK))
        
        # With atomic bomb active, king captures should be illegal
        king_capture = chess.Move(chess.E1, chess.F2)
        
        # Check if the move is in legal moves
        # If atomic bomb is working, this capture should be illegal
        legal_moves_list = list(self.board.legal_moves)
        self.assertNotIn(king_capture, legal_moves_list, 
                         f"King capture found in legal moves: {legal_moves_list}")
        
        # Make a legal move and test undo
        legal_move = chess.Move(chess.D4, chess.F3)
        self.board.push(legal_move)
        self.board.pop()
        
        # Verify the knight is back in place after undo
        knight = self.board.piece_at(chess.D4)
        self.assertIsNotNone(knight)
        self.assertEqual(knight.piece_type, chess.KNIGHT)

if __name__ == '__main__':
    unittest.main() 