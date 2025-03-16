import unittest
import chess
from GameState.movegen import DrawbackBoard

class TestDrawConditions(unittest.TestCase):
    """Test the draw conditions in Drawback Chess"""
    
    def test_threefold_repetition(self):
        """Test that 3-fold repetition is correctly detected"""
        # Create a new board with standard starting position
        board = DrawbackBoard()
        
        # Make a sequence of moves that will create a repetition
        # Knight moves back and forth
        move_sequence = [
            chess.Move.from_uci("g1f3"),  # White knight to f3
            chess.Move.from_uci("g8f6"),  # Black knight to f6
            chess.Move.from_uci("f3g1"),  # White knight back to g1
            chess.Move.from_uci("f6g8"),  # Black knight back to g8
            chess.Move.from_uci("g1f3"),  # White knight to f3
            chess.Move.from_uci("g8f6"),  # Black knight to f6
            chess.Move.from_uci("f3g1"),  # White knight back to g1
            chess.Move.from_uci("f6g8"),  # Black knight back to g8
            chess.Move.from_uci("g1f3"),  # White knight to f3 (3rd time in same position)
        ]
        
        # Make the moves
        for move in move_sequence[:-1]:
            board.push(move)
            # After these moves, should not yet be a 3-fold repetition
            self.assertFalse(board.is_threefold_repetition(), 
                "Should not be a 3-fold repetition yet")
        
        # Push the final move
        board.push(move_sequence[-1])
        
        # Now should detect 3-fold repetition
        self.assertTrue(board.is_threefold_repetition(), 
            "Should detect 3-fold repetition after the sequence")
        
        # Check that it's considered a draw by the is_variant_draw method
        self.assertTrue(board.is_variant_draw(), 
            "3-fold repetition should be considered a draw")
    
    def test_insufficient_material_king_vs_king(self):
        """Test insufficient material detection: King vs King"""
        # Create a position with just the kings
        board = DrawbackBoard("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        
        # Should be insufficient material
        self.assertTrue(board.has_insufficient_material(), 
            "King vs King should be insufficient material")
            
        # Should be a draw
        self.assertTrue(board.is_variant_draw(), 
            "King vs King should be a draw")
    
    def test_insufficient_material_king_bishop_vs_king(self):
        """Test insufficient material detection: King+Bishop vs King"""
        # Create a position with king+bishop vs king
        board = DrawbackBoard("4k3/8/8/8/8/8/8/4KB2 w - - 0 1")
        
        # Should be insufficient material
        self.assertTrue(board.has_insufficient_material(), 
            "King+Bishop vs King should be insufficient material")
            
        # Should be a draw
        self.assertTrue(board.is_variant_draw(), 
            "King+Bishop vs King should be a draw")
    
    def test_insufficient_material_king_knight_vs_king(self):
        """Test insufficient material detection: King+Knight vs King"""
        # Create a position with king+knight vs king
        board = DrawbackBoard("4k3/8/8/8/8/8/8/4KN2 w - - 0 1")
        
        # Should be insufficient material
        self.assertTrue(board.has_insufficient_material(), 
            "King+Knight vs King should be insufficient material")
            
        # Should be a draw
        self.assertTrue(board.is_variant_draw(), 
            "King+Knight vs King should be a draw")
    
    def test_insufficient_material_king_bishop_vs_king_bishop_same_color(self):
        """Test insufficient material: King+Bishop vs King+Bishop (same color squares)"""
        # Create a position with king+bishop vs king+bishop where the bishops
        # are on same color squares
        board = DrawbackBoard("4kb2/8/8/8/8/8/8/4KB2 w - - 0 1")
        
        # Should be insufficient material
        self.assertTrue(board.has_insufficient_material(), 
            "King+Bishop vs King+Bishop (same color squares) should be insufficient material")
            
        # Should be a draw
        self.assertTrue(board.is_variant_draw(), 
            "King+Bishop vs King+Bishop (same color squares) should be a draw")
    
    def test_insufficient_material_king_bishop_vs_king_bishop_opposite_color(self):
        """Test insufficient material: King+Bishop vs King+Bishop (opposite color squares)"""
        # Create a position with king+bishop vs king+bishop where the bishops
        # are on opposite color squares
        board = DrawbackBoard("3kb3/8/8/8/8/8/8/4KB2 w - - 0 1")
        
        # Should NOT be insufficient material
        self.assertFalse(board.has_insufficient_material(), 
            "King+Bishop vs King+Bishop (opposite color squares) should NOT be insufficient material")
            
        # Should NOT be a draw
        self.assertFalse(board.is_variant_draw(), 
            "King+Bishop vs King+Bishop (opposite color squares) should NOT be a draw")
    
    def test_sufficient_material_with_pawn(self):
        """Test that positions with pawns are considered sufficient material"""
        # Create a position with king+pawn vs king
        board = DrawbackBoard("4k3/8/8/8/8/8/P7/4K3 w - - 0 1")
        
        # Should NOT be insufficient material
        self.assertFalse(board.has_insufficient_material(), 
            "King+Pawn vs King should NOT be insufficient material")
    
    def test_sufficient_material_with_rook(self):
        """Test that positions with rooks are considered sufficient material"""
        # Create a position with king+rook vs king
        board = DrawbackBoard("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
        
        # Should NOT be insufficient material
        self.assertFalse(board.has_insufficient_material(), 
            "King+Rook vs King should NOT be insufficient material")
    
    def test_sufficient_material_with_queen(self):
        """Test that positions with queens are considered sufficient material"""
        # Create a position with king+queen vs king
        board = DrawbackBoard("4k3/8/8/8/8/8/8/Q3K3 w - - 0 1")
        
        # Should NOT be insufficient material
        self.assertFalse(board.has_insufficient_material(), 
            "King+Queen vs King should NOT be insufficient material")
    
    def test_king_en_passant_after_castling(self):
        """Test the king en passant capture rule after castling"""
        # Create a position with white king on e1 and black rook on f8
        board = DrawbackBoard("5r2/8/8/8/8/8/8/4K3 w - - 0 1")
        
        # White castles kingside (king moves from e1 to g1)
        castling_move = chess.Move.from_uci("e1g1")
        print(f"Castling move: {castling_move}")
        
        # Make the castling move
        board.push(castling_move)
        
        # After castling, the king passed through f1
        print(f"Castling king passed squares: {board._castling_king_passed_squares}")
        self.assertEqual(len(board._castling_king_passed_squares), 1, 
            "Should have one square where king passed during castling")
        
        # The king passed through f1
        f1_square = chess.square(5, 0)  # f1
        print(f"f1 square: {f1_square}, passed square: {board._castling_king_passed_squares[0]}")
        self.assertEqual(board._castling_king_passed_squares[0], f1_square, 
            "King should have passed through f1 during kingside castling")
        
        # Black should be able to capture the king "en passant" with a rook on f8
        en_passant_capture = chess.Move.from_uci("f8f1")
        print(f"En passant capture: {en_passant_capture}")
        
        # Debug: Check the piece at f8
        f8_square = chess.square(5, 7)  # f8
        piece_at_f8 = board.piece_at(f8_square)
        print(f"Piece at f8: {piece_at_f8}")
        
        # Debug: Check if the move is pseudo-legal
        is_pseudo_legal = board.is_pseudo_legal(en_passant_capture)
        print(f"Is en passant capture pseudo-legal: {is_pseudo_legal}")
        
        # Debug: Check the current turn
        print(f"Current turn: {'Black' if board.turn == chess.BLACK else 'White'}")
        
        # Check if this move is legal
        is_legal = board.is_legal(en_passant_capture)
        print(f"Is en passant capture legal: {is_legal}")
        self.assertTrue(is_legal, 
            "King en passant capture should be legal after castling")
        
        # Make the move
        board.push(en_passant_capture)
        
        # After the capture, white's king should be gone
        white_king_exists = any(p.piece_type == chess.KING and p.color == chess.WHITE 
                             for p in board.piece_map().values())
        print(f"White king exists after capture: {white_king_exists}")
        self.assertFalse(white_king_exists, 
            "White's king should be captured after en passant capture")
        
        # The game should be over with Black winning
        game_over, winner_color, _ = check_game_end_conditions(board)
        self.assertTrue(game_over, "Game should be over after king is captured")
        self.assertEqual(winner_color, chess.BLACK, "Black should win after capturing white king")

# Helper function to simulate check_game_end_conditions from main.py
def check_game_end_conditions(board):
    # Check if a king has been captured
    white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                         for p in board.piece_map().values())
    black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                         for p in board.piece_map().values())
    
    if not white_king_alive:
        return True, chess.BLACK, "White's king was captured"
    if not black_king_alive:
        return True, chess.WHITE, "Black's king was captured"
    
    return False, None, None

if __name__ == "__main__":
    unittest.main() 