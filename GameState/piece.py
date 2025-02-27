from GameState.constants import PieceType, Color, DIRECTIONS, KNIGHT_MOVES, BOARD_SIZE

class Piece:
    def __init__(self, piece_type, color):
        self.piece_type = piece_type
        self.color = color
        self.has_moved = False
    
    def __str__(self):
        return self.piece_type.symbol(self.color)
    
    def char(self):
        return self.piece_type.char(self.color)
    
    def get_moves(self, board, position):
        """Get all possible moves for this piece without considering drawbacks"""
        row, col = position
        
        # Delegate to specific piece move generators
        if self.piece_type == PieceType.PAWN:
            return self._get_pawn_moves(board, position)
        elif self.piece_type == PieceType.KNIGHT:
            return self._get_knight_moves(board, position)
        elif self.piece_type == PieceType.BISHOP:
            return self._get_sliding_moves(board, position, ["NE", "SE", "SW", "NW"])
        elif self.piece_type == PieceType.ROOK:
            return self._get_sliding_moves(board, position, ["N", "E", "S", "W"])
        elif self.piece_type == PieceType.QUEEN:
            return self._get_sliding_moves(board, position, list(DIRECTIONS.keys()))
        elif self.piece_type == PieceType.KING:
            return self._get_king_moves(board, position)
        
        return []
    
    def _get_pawn_moves(self, board, position):
        """Get all possible pawn moves"""
        row, col = position
        moves = []
        
        # Direction pawns move (white moves up, black moves down)
        direction = 1 if self.color == Color.WHITE else -1
        
        # Forward move
        new_row = row + direction
        if 0 <= new_row < BOARD_SIZE and board.get_piece((new_row, col)) is None:
            moves.append(((row, col), (new_row, col)))
            
            # Double move from starting position
            if (self.color == Color.WHITE and row == 1) or (self.color == Color.BLACK and row == 6):
                new_row = row + 2 * direction
                if 0 <= new_row < BOARD_SIZE and board.get_piece((new_row, col)) is None:
                    moves.append(((row, col), (new_row, col)))
        
        # Captures
        for offset in [-1, 1]:
            new_col = col + offset
            new_row = row + direction
            
            if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                target = board.get_piece((new_row, new_col))
                
                # Regular capture
                if target is not None and target.color != self.color:
                    moves.append(((row, col), (new_row, new_col)))
                
                # En passant
                en_passant_square = board.en_passant_square
                if en_passant_square and en_passant_square == (new_row, new_col):
                    moves.append(((row, col), (new_row, new_col)))
        
        return moves
    
    def _get_knight_moves(self, board, position):
        """Get all possible knight moves"""
        row, col = position
        moves = []
        
        for offset_row, offset_col in KNIGHT_MOVES:
            new_row, new_col = row + offset_row, col + offset_col
            
            if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                target = board.get_piece((new_row, new_col))
                
                # Move to empty square or capture opponent's piece
                if target is None or target.color != self.color:
                    moves.append(((row, col), (new_row, new_col)))
        
        return moves
    
    def _get_sliding_moves(self, board, position, directions):
        """Get all possible moves for sliding pieces (bishop, rook, queen)"""
        row, col = position
        moves = []
        
        for direction_name in directions:
            dr, dc = DIRECTIONS[direction_name]
            
            for dist in range(1, BOARD_SIZE):
                new_row, new_col = row + dr * dist, col + dc * dist
                
                if not (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE):
                    break  # Out of board
                
                target = board.get_piece((new_row, new_col))
                
                if target is None:
                    # Empty square
                    moves.append(((row, col), (new_row, new_col)))
                else:
                    if target.color != self.color:
                        # Capture opponent's piece
                        moves.append(((row, col), (new_row, new_col)))
                    break  # Stop in this direction after encountering a piece
        
        return moves
    
    def _get_king_moves(self, board, position):
        """Get all possible king moves including castling"""
        row, col = position
        moves = []
        
        # Regular king moves (one square in any direction)
        for direction_name, (dr, dc) in DIRECTIONS.items():
            new_row, new_col = row + dr, col + dc
            
            if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                target = board.get_piece((new_row, new_col))
                
                # Move to empty square or capture opponent's piece
                if target is None or target.color != self.color:
                    moves.append(((row, col), (new_row, new_col)))
        
        # Castling
        if not self.has_moved:
            # Look for rooks that haven't moved
            
            # Kingside castling
            kingside_rook_pos = (row, 7)
            rook = board.get_piece(kingside_rook_pos)
            if (rook and rook.piece_type == PieceType.ROOK and rook.color == self.color and 
                not rook.has_moved and 
                all(board.get_piece((row, c)) is None for c in range(col+1, 7))):
                moves.append(((row, col), (row, col+2)))  # King's destination in castling
            
            # Queenside castling
            queenside_rook_pos = (row, 0)
            rook = board.get_piece(queenside_rook_pos)
            if (rook and rook.piece_type == PieceType.ROOK and rook.color == self.color and 
                not rook.has_moved and 
                all(board.get_piece((row, c)) is None for c in range(1, col))):
                moves.append(((row, col), (row, col-2)))  # King's destination in castling
        
        return moves
