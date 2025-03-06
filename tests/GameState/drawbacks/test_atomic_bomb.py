"""
Unit tests for the atomic bomb drawback
"""
import unittest
import chess
import sys
import os

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from GameState.drawbacks.atomic_bomb import AtomicBombDrawback
from GameState.movegen import DrawbackBoard

class TestAtomicBombDrawback(unittest.TestCase):
    """Test cases for the AtomicBombDrawback class"""
    
    def setUp(self):
        """Set up a clean board for each test"""
        self.board = DrawbackBoard()
        self.drawback = AtomicBombDrawback()
        
    def test_atomic_bomb_initialization(self):
        """Test that AtomicBombDrawback initializes correctly"""
        self.assertEqual(self.drawback.name, "Atomic Bomb")
        self.assertIn("knights explode", self.drawback.description.lower())
        
    def test_basic_explosion(self):
        """Test a basic atomic bomb explosion"""
        # Clear the board
        self.board.clear()
        
        # Place kings
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        
        # Place atomic bomb knight
        self.board.set_piece_at(chess.D4, chess.Piece(chess.KNIGHT, chess.WHITE))
        
        # Place capturing piece
        self.board.set_piece_at(chess.C6, chess.Piece(chess.KNIGHT, chess.BLACK))
        
        # Create capture move
        move = chess.Move(chess.C6, chess.D4)
        
        # Apply the drawback effect
        result = self.drawback.make_move(self.board, move)
        
        # Verify effects
        self.assertTrue(result)
        
        # D4 (target) should be empty
        self.assertIsNone(self.board.piece_at(chess.D4))
        
        # C6 (source) should be empty
        self.assertIsNone(self.board.piece_at(chess.C6))
        
        # Adjacent squares should be empty
        for square in [chess.C3, chess.C4, chess.C5, chess.D3, chess.D5, chess.E3, chess.E4, chess.E5]:
            self.assertIsNone(self.board.piece_at(square), f"Square {chess.square_name(square)} should be empty")
            
        # Kings should remain
        self.assertIsNotNone(self.board.piece_at(chess.E1))
        self.assertIsNotNone(self.board.piece_at(chess.E8))
        
    def test_unmake_move(self):
        """Test unmake_move functionality restores the board correctly"""
        # Clear the board
        self.board.clear()
        
        # Place kings
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        
        # Place atomic bomb knight
        bomb = chess.Piece(chess.KNIGHT, chess.WHITE)
        bomb_square = chess.D4
        self.board.set_piece_at(bomb_square, bomb)
        
        # Place pieces around that will be affected by explosion
        affected_pieces = [
            (chess.C3, chess.Piece(chess.PAWN, chess.WHITE)),
            (chess.D3, chess.Piece(chess.BISHOP, chess.WHITE)),
            (chess.E3, chess.Piece(chess.PAWN, chess.WHITE)),
            (chess.C4, chess.Piece(chess.PAWN, chess.BLACK)),
            (chess.E4, chess.Piece(chess.PAWN, chess.BLACK)),
            (chess.C5, chess.Piece(chess.BISHOP, chess.BLACK)),
            (chess.D5, chess.Piece(chess.PAWN, chess.BLACK)),
            (chess.E5, chess.Piece(chess.KNIGHT, chess.BLACK)),
        ]
        
        # Place the pieces
        for square, piece in affected_pieces:
            self.board.set_piece_at(square, piece)
            
        # Place capturing piece
        capturing_piece = chess.Piece(chess.QUEEN, chess.BLACK)
        source_square = chess.B5
        self.board.set_piece_at(source_square, capturing_piece)
        
        # Create capture move
        move = chess.Move(source_square, bomb_square)
        
        # Store the original board state for comparison
        original_board = self.board.copy()
        
        # Apply the drawback effect
        self.drawback.make_move(self.board, move)
        
        # Verify explosion happened
        for square, _ in affected_pieces:
            self.assertIsNone(self.board.piece_at(square), 
                             f"Square {chess.square_name(square)} should be empty after explosion")
        
        # Unmake the move
        self.drawback.unmake_move(self.board, move)
        
        # Verify all pieces are restored
        self.assertEqual(self.board.piece_at(source_square), capturing_piece)
        self.assertEqual(self.board.piece_at(bomb_square), bomb)
        
        for square, piece in affected_pieces:
            board_piece = self.board.piece_at(square)
            self.assertEqual(board_piece, piece, 
                            f"Square {chess.square_name(square)} should have {piece} but has {board_piece}")
            
        # The board should be identical to the original
        self.assertEqual(self.board.board_fen(), original_board.board_fen())
        
    def test_king_protection(self):
        """Test that kings are protected from explosion"""
        # Clear the board
        self.board.clear()
        
        # Place kings adjacent to the explosion
        self.board.set_piece_at(chess.D3, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.D5, chess.Piece(chess.KING, chess.BLACK))
        
        # Place atomic bomb knight
        self.board.set_piece_at(chess.D4, chess.Piece(chess.KNIGHT, chess.WHITE))
        
        # Place capturing piece
        self.board.set_piece_at(chess.C6, chess.Piece(chess.KNIGHT, chess.BLACK))
        
        # Create capture move
        move = chess.Move(chess.C6, chess.D4)
        
        # Apply the drawback effect
        result = self.drawback.make_move(self.board, move)
        
        # Verify kings remain
        self.assertTrue(result)
        self.assertIsNotNone(self.board.piece_at(chess.D3))
        self.assertIsNotNone(self.board.piece_at(chess.D5))
        
    def test_non_knight_capture(self):
        """Test that capturing non-knight pieces doesn't trigger explosion"""
        # Clear the board
        self.board.clear()
        
        # Place kings
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        
        # Place a bishop (not a knight)
        self.board.set_piece_at(chess.D4, chess.Piece(chess.BISHOP, chess.WHITE))
        
        # Place capturing piece
        self.board.set_piece_at(chess.C5, chess.Piece(chess.PAWN, chess.BLACK))
        
        # Create capture move
        move = chess.Move(chess.C5, chess.D4)
        
        # Apply the drawback effect
        result = self.drawback.make_move(self.board, move)
        
        # Verify no explosion happened
        self.assertFalse(result)
        
        # Normal capture should occur (managed by the chess.Board class)
        # We just verify no additional effects took place
        
    def test_in_game_integration(self):
        """Test integration with the DrawbackBoard"""
        # Clear the board
        self.board.clear()
        
        # Place kings
        self.board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        self.board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        
        # Place atomic bomb knight
        bomb_square = chess.D4
        self.board.set_piece_at(bomb_square, chess.Piece(chess.KNIGHT, chess.WHITE))
        
        # Place pieces around that will be affected by explosion
        pieces = [
            (chess.C3, chess.Piece(chess.PAWN, chess.WHITE)),
            (chess.D3, chess.Piece(chess.BISHOP, chess.WHITE)),
            (chess.E3, chess.Piece(chess.PAWN, chess.WHITE)),
        ]
        
        # Place the pieces
        for square, piece in pieces:
            self.board.set_piece_at(square, piece)
            
        # Place capturing piece
        source_square = chess.C6
        self.board.set_piece_at(source_square, chess.Piece(chess.BISHOP, chess.BLACK))
        
        # Set correct turn
        self.board.turn = chess.BLACK
        
        # Create and execute the move
        move = chess.Move(source_square, bomb_square)
        self.board.push(move)
        
        # Verify explosion happened
        self.assertIsNone(self.board.piece_at(bomb_square))
        for square, _ in pieces:
            self.assertIsNone(self.board.piece_at(square), 
                             f"Square {chess.square_name(square)} should be empty after explosion")
        
        # Undo the move
        self.board.pop()
        
        # Verify everything is restored
        self.assertEqual(self.board.piece_at(bomb_square).piece_type, chess.KNIGHT)
        for square, piece in pieces:
            self.assertEqual(self.board.piece_at(square), piece)

if __name__ == '__main__':
    unittest.main() 