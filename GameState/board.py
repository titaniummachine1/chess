from GameState.constants import Color, PieceType, MoveType, INITIAL_FEN, BOARD_SIZE
from GameState.piece import Piece

class Board:
    def __init__(self, fen=None):
        self.squares = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.turn = Color.WHITE
        self.castling_rights = {
            Color.WHITE: {"kingside": True, "queenside": True},
            Color.BLACK: {"kingside": True, "queenside": True}
        }
        self.en_passant_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        
        # Track the kings' positions
        self.king_positions = {Color.WHITE: None, Color.BLACK: None}
        
        # Track last captured piece for UI
        self.last_captured = None
        
        # Track moves for history
        self.move_history = []
        
        # Store drawbacks for each color
        self.drawbacks = {Color.WHITE: None, Color.BLACK: None}
        
        # Special tracking for king en-passant after castling
        self.king_passant_squares = []  # Squares where king moved through during castling
        
        # Load position from FEN
        self.load_fen(fen or INITIAL_FEN)
    
    def load_fen(self, fen):
        """Load the board position from FEN notation"""
        parts = fen.split()
        board = parts[0]
        
        # Parse board position
        row, col = 7, 0
        for char in board:
            if char == '/':
                row -= 1
                col = 0
            elif char.isdigit():
                col += int(char)
            else:
                color = Color.WHITE if char.isupper() else Color.BLACK
                piece_type = None
                
                char_lower = char.lower()
                if char_lower == 'p':
                    piece_type = PieceType.PAWN
                elif char_lower == 'n':
                    piece_type = PieceType.KNIGHT
                elif char_lower == 'b':
                    piece_type = PieceType.BISHOP
                elif char_lower == 'r':
                    piece_type = PieceType.ROOK
                elif char_lower == 'q':
                    piece_type = PieceType.QUEEN
                elif char_lower == 'k':
                    piece_type = PieceType.KING
                    self.king_positions[color] = (row, col)
                
                if piece_type is not None:
                    self.squares[row][col] = Piece(piece_type, color)
                col += 1
        
        # Parse active color
        self.turn = Color.WHITE if parts[1] == 'w' else Color.BLACK
        
        # Parse castling rights
        self.castling_rights = {
            Color.WHITE: {"kingside": False, "queenside": False},
            Color.BLACK: {"kingside": False, "queenside": False}
        }
        if parts[2] != '-':
            for char in parts[2]:
                if char == 'K':
                    self.castling_rights[Color.WHITE]["kingside"] = True
                elif char == 'Q':
                    self.castling_rights[Color.WHITE]["queenside"] = True
                elif char == 'k':
                    self.castling_rights[Color.BLACK]["kingside"] = True
                elif char == 'q':
                    self.castling_rights[Color.BLACK]["queenside"] = True
        
        # Parse en passant target square
        if parts[3] != '-':
            col = ord(parts[3][0]) - ord('a')
            row = 8 - int(parts[3][1])
            self.en_passant_square = (row, col)
        
        # Parse halfmove clock and fullmove number
        if len(parts) > 4:
            self.halfmove_clock = int(parts[4])
        if len(parts) > 5:
            self.fullmove_number = int(parts[5])
    
    def get_fen(self):
        """Generate FEN string for the current position"""
        fen_parts = []
        
        # Board position
        for row in range(7, -1, -1):
            empty_count = 0
            row_str = ""
            
            for col in range(8):
                piece = self.squares[row][col]
                
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += piece.char()
            
            if empty_count > 0:
                row_str += str(empty_count)
            
            fen_parts.append(row_str)
        
        fen = '/'.join(fen_parts)
        
        # Active color
        fen += ' w' if self.turn == Color.WHITE else ' b'
        
        # Castling rights
        castling = ""
        if self.castling_rights[Color.WHITE]["kingside"]:
            castling += "K"
        if self.castling_rights[Color.WHITE]["queenside"]:
            castling += "Q"
        if self.castling_rights[Color.BLACK]["kingside"]:
            castling += "k"
        if self.castling_rights[Color.BLACK]["queenside"]:
            castling += "q"
        
        fen += " " + (castling if castling else "-")
        
        # En passant target square
        if self.en_passant_square:
            row, col = self.en_passant_square
            fen += f" {chr(97 + col)}{8 - row}"
        else:
            fen += " -"
        
        # Halfmove clock and fullmove number
        fen += f" {self.halfmove_clock} {self.fullmove_number}"
        
        return fen
    
    def get_piece(self, position):
        """Get the piece at the given position"""
        row, col = position
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return self.squares[row][col]
        return None
    
    def set_piece(self, position, piece):
        """Set a piece at the given position"""
        row, col = position
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            self.squares[row][col] = piece
            # Update king position if it's a king
            if piece and piece.piece_type == PieceType.KING:
                self.king_positions[piece.color] = position
    
    def make_move(self, move):
        """Make a move on the board without checking if it's legal"""
        from_pos, to_pos = move
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        # Get pieces
        piece = self.get_piece(from_pos)
        target = self.get_piece(to_pos)
        
        # Store this move in the history
        move_record = {
            "from": from_pos,
            "to": to_pos,
            "piece": piece,
            "captured": target,
            "en_passant_square": self.en_passant_square,
            "castling_rights": {
                Color.WHITE: self.castling_rights[Color.WHITE].copy(),
                Color.BLACK: self.castling_rights[Color.BLACK].copy()
            },
            "king_passant_squares": self.king_passant_squares.copy(),
            "halfmove_clock": self.halfmove_clock,
            "fullmove_number": self.fullmove_number
        }
        
        # Reset en passant square and king_passant_squares
        self.en_passant_square = None
        self.king_passant_squares = []
        
        # Set last captured piece for UI
        self.last_captured = target
        
        # Handle castling
        castling_move = False
        if piece and piece.piece_type == PieceType.KING and abs(from_col - to_col) > 1:
            castling_move = True
            # Kingside castling
            if to_col > from_col:
                rook_from = (from_row, 7)
                rook_to = (from_row, to_col - 1)
                # Track squares the king moved through
                self.king_passant_squares = [(from_row, from_col), (from_row, from_col + 1), (from_row, to_col)]
            # Queenside castling
            else:
                rook_from = (from_row, 0)
                rook_to = (from_row, to_col + 1)
                # Track squares the king moved through
                self.king_passant_squares = [(from_row, from_col), (from_row, from_col - 1), (from_row, to_col)]
            
            # Move the rook
            rook = self.get_piece(rook_from)
            self.set_piece(rook_from, None)
            self.set_piece(rook_to, rook)
            if rook:
                rook.has_moved = True
        
        # Handle normal capture
        if target:
            self.set_piece(to_pos, None)
        
        # Handle en passant capture
        if piece and piece.piece_type == PieceType.PAWN and self.en_passant_square == to_pos:
            # Remove the captured pawn
            capture_row = from_row
            capture_col = to_col
            self.set_piece((capture_row, capture_col), None)
        
        # Move the piece
        self.set_piece(from_pos, None)
        self.set_piece(to_pos, piece)
        
        if piece:
            # Set the piece's has_moved flag
            piece.has_moved = True
        
            # Set en passant square if pawn moved two squares
            if piece.piece_type == PieceType.PAWN and abs(from_row - to_row) == 2:
                # Set the en passant square to the square the pawn skipped
                self.en_passant_square = (from_row + (1 if to_row > from_row else -1), from_col)
        
        # Update castling rights if king or rook moves
        if piece and piece.piece_type == PieceType.KING:
            self.castling_rights[piece.color]["kingside"] = False
            self.castling_rights[piece.color]["queenside"] = False
        
        if piece and piece.piece_type == PieceType.ROOK:
            if from_col == 0:  # Queenside rook
                self.castling_rights[piece.color]["queenside"] = False
            elif from_col == 7:  # Kingside rook
                self.castling_rights[piece.color]["kingside"] = False
        
        # Update halfmove clock
        if piece and piece.piece_type == PieceType.PAWN or target:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        
        # Update fullmove number
        if self.turn == Color.BLACK:
            self.fullmove_number += 1
        
        # Switch turn
        self.turn = Color.opposite(self.turn)
        
        # Add the move to history
        self.move_history.append(move_record)
        
        return True
    
    def undo_move(self):
        """Undo the last move"""
        if not self.move_history:
            return False
        
        # Get the last move
        move = self.move_history.pop()
        from_pos = move["from"]
        to_pos = move["to"]
        piece = move["piece"]
        captured = move["captured"]
        
        # Restore the piece
        self.set_piece(to_pos, None)
        self.set_piece(from_pos, piece)
        
        if piece:
            # Reset the piece's has_moved flag if this was its first move
            # (This is simplistic and might not cover all cases correctly)
            piece.has_moved = False
        
        # Restore captured piece
        if captured:
            self.set_piece(to_pos, captured)
        
        # Handle en passant capture
        if piece and piece.piece_type == PieceType.PAWN and move["en_passant_square"] == to_pos:
            # En passant capture happened, restore the captured pawn
            capture_row = from_pos[0]
            capture_col = to_pos[1]
            capture_color = Color.WHITE if self.turn == Color.BLACK else Color.BLACK
            self.set_piece((capture_row, capture_col), Piece(PieceType.PAWN, capture_color))
        
        # Handle castling
        king_moved_two = piece and piece.piece_type == PieceType.KING and abs(from_pos[1] - to_pos[1]) > 1
        if king_moved_two:
            # Kingside castling
            if to_pos[1] > from_pos[1]:
                rook_from = (from_pos[0], 7)
                rook_to = (from_pos[0], to_pos[1] - 1)
            # Queenside castling
            else:
                rook_from = (from_pos[0], 0)
                rook_to = (from_pos[0], to_pos[1] + 1)
            
            # Move the rook back
            rook = self.get_piece(rook_to)
            self.set_piece(rook_to, None)
            self.set_piece(rook_from, rook)
            if rook:
                rook.has_moved = False
        
        # Restore board state
        self.en_passant_square = move["en_passant_square"]
        self.castling_rights = move["castling_rights"]
        self.king_passant_squares = move["king_passant_squares"]
        self.halfmove_clock = move["halfmove_clock"]
        self.fullmove_number = move["fullmove_number"]
        
        # Switch back turn
        self.turn = Color.opposite(self.turn)
        
        return True
    
    def get_all_moves(self, color=None, respect_drawbacks=True):
        """Get all possible moves for the given color"""
        if color is None:
            color = self.turn
        
        all_moves = []
        
        # Iterate over all squares
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.get_piece((row, col))
                
                if piece and piece.color == color:
                    # Get all moves for this piece
                    moves = piece.get_moves(self, (row, col))
                    
                    # Add king-en-passant moves if available
                    if piece.piece_type != PieceType.KING:  # Any piece can capture a king via en passant
                        for king_passant_pos in self.king_passant_squares:
                            if king_passant_pos[0] == row and abs(king_passant_pos[1] - col) == 1:
                                moves.append(((row, col), king_passant_pos))
                    
                    # Filter moves based on drawbacks
                    if respect_drawbacks:
                        drawback = self.drawbacks.get(color)
                        if drawback:
                            moves = drawback.filter_moves(self, moves)
                    
                    all_moves.extend(moves)
        
        return all_moves
    
    def is_legal_move(self, move, color=None):
        """Check if a move is legal for the current player"""
        if color is None:
            color = self.turn
        
        all_moves = self.get_all_moves(color)
        return move in all_moves
    
    def is_game_over(self):
        """Check if the game is over - if a king is captured or no legal moves"""
        # Check if a king was captured
        if self.king_positions[Color.WHITE] is None:
            return True, Color.BLACK  # Black wins
        if self.king_positions[Color.BLACK] is None:
            return True,