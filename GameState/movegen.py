## movegen.py contains the custom board class for Drawback Chess, which extends the standard python-chess board class.
import chess
import random
from typing import Iterator, Optional, List, Union
from GameState.drawback_manager import (
    get_drawback_info, get_drawback_function, get_drawback_loss_function
)

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - Standard starting FEN (white on bottom, black on top).
      - Ignores checks, can capture king.
      - Drawback-based restrictions.
    """

    def __init__(self, fen: str = chess.STARTING_FEN, white_drawback: Optional[str] = None, black_drawback: Optional[str] = None):
        super().__init__(fen)
        self._white_drawback = white_drawback
        self._black_drawback = black_drawback
        self._in_search = False  # Flag to indicate when we're in a search context

    def reset(self, fen: str = chess.STARTING_FEN) -> None:
        """Reset the board to the starting position"""
        super().reset()
        self._white_drawback = None
        self._black_drawback = None

    def set_white_drawback(self, drawback: Optional[str]) -> None:
        """Set the white drawback"""
        self._white_drawback = drawback

    def set_black_drawback(self, drawback: Optional[str]) -> None:
        """Set the black drawback"""
        self._black_drawback = drawback

    def get_active_drawback(self, color: chess.Color) -> Optional[str]:
        """Get the active drawback for the specified color"""
        assert color in [chess.WHITE, chess.BLACK], "Invalid color"
        return self._white_drawback if color == chess.WHITE else self._black_drawback

    # Ignore checks entirely
    def checkers_mask(self) -> chess.Bitboard:
        return 0

    def is_into_check(self, move: chess.Move) -> bool:
        return False

    def was_into_check(self) -> bool:
        return False

    @property
    def legal_moves(self) -> chess.LegalMoveGenerator:
        """Get legal moves with drawback restrictions safely"""
        # First, make sure the game isn't over to avoid recursion issues
        if self._is_game_over_simple():
            # Return empty move list if game is over
            return chess.LegalMoveGenerator(self)
        
        # Otherwise, use the standard generator
        return chess.LegalMoveGenerator(self)

    def generate_legal_moves(self, from_mask: chess.Bitboard = chess.BB_ALL, to_mask: chess.Bitboard = chess.BB_ALL) -> Iterator[chess.Move]:
        """Generate legal moves considering drawbacks"""
        # Get standard chess moves first
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))
        
        # Apply drawback restrictions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            filtered_moves = []
            for move in moves:
                # Use direct drawback check to avoid recursion
                if self._check_drawbacks(move, self.turn):
                    filtered_moves.append(move)
            return iter(filtered_moves)
                
        return iter(moves)

    def is_variant_end(self) -> bool:
        """
        In Drawback Chess, the game ends when one of the kings is captured,
        or when a player has no legal moves due to drawback restrictions.
        """
        # Check if kings are captured - direct board inspection to avoid recursion
        white_king_alive = False
        black_king_alive = False
        
        # Directly access the piece map to check for kings
        for square, piece in self.piece_map().items():
            if piece.piece_type == chess.KING:
                if piece.color == chess.WHITE:
                    white_king_alive = True
                else:
                    black_king_alive = True
                    
                # Early exit if both kings found
                if white_king_alive and black_king_alive:
                    break

        # Game ends when a king is captured
        if not white_king_alive or not black_king_alive:
            return True

        # Check for special drawback-related loss conditions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            # Check explicit loss condition function
            loss_function = get_drawback_loss_function(active_drawback)
            if loss_function and loss_function(self, self.turn):
                print(f"Drawback '{active_drawback}' triggered loss condition!")
                return True
            
            # Check for legal moves WITHOUT using recursive calls
            # Use internal move generator directly
            legal_moves_exist = False
            
            # Get all piece positions for current player's turn
            for square in chess.SQUARES:
                piece = self.piece_at(square)
                if piece and piece.color == self.turn:
                    # For each piece, generate moves directly
                    for move_square in chess.SQUARES:
                        # Create potential move
                        move = chess.Move(square, move_square)
                        
                        # Check if move is pseudo-legal according to basic chess rules
                        if self._is_pseudo_legal(move):
                            # Then check if it's legal according to drawback
                            if not self._is_drawback_illegal(move, self.turn):
                                legal_moves_exist = True
                                break
                                
                    # Early exit once we found a legal move
                    if legal_moves_exist:
                        break
                        
            # If no legal moves exist, game is over
            if not legal_moves_exist:
                print(f"No legal moves available due to drawback '{active_drawback}' - game ends")
                return True
                    
        # No other end conditions - you must capture the king to win
        return False

    def is_variant_win(self) -> bool:
        """
        In Drawback Chess, you win by capturing the opponent's king.
        """
        white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                               for p in self.piece_map().values())
        black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                               for p in self.piece_map().values())

        # White wins if Black's king is captured
        if not black_king_alive:
            return True
        # Black wins if White's king is captured    
        if not white_king_alive:
            return False
            
        # No win yet if both kings are alive
        return False

    def is_variant_loss(self) -> bool:
        """
        In Drawback Chess, you lose when:
        1. Your king is captured
        2. You have no legal moves due to drawback restrictions
        3. A drawback-specific loss condition is met
        """
        # First directly check for king capture without using is_variant_end
        white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                             for p in self.piece_map().values())
        black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                             for p in self.piece_map().values())
                             
        if not white_king_alive and self.turn == chess.WHITE:
            return True  # White's king captured, white loses
        if not black_king_alive and self.turn == chess.BLACK:
            return True  # Black's king captured, black loses
        
        # Check for drawback loss conditions directly
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            loss_function = get_drawback_loss_function(active_drawback)
            if loss_function and loss_function(self, self.turn):
                return True  # Explicit loss condition triggered
            
            # Check for legal moves directly without recursion
            pseudo_moves = list(super().generate_pseudo_legal_moves())
            has_legal_moves = False
            for move in pseudo_moves:
                if not self._is_drawback_illegal(move, self.turn):
                    has_legal_moves = True
                    break
            
            if not has_legal_moves:
                return True  # No legal moves due to drawback
            
        return False

    def is_legal(self, move: chess.Move) -> bool:
        """Enhanced is_legal that incorporates drawback rules"""
        # Basic legality check first
        if not super().is_legal(move):
            return False
            
        # Use direct drawback check to avoid recursion
        return self._check_drawbacks(move, self.turn)
        
    def _is_drawback_illegal(self, move: chess.Move, color: chess.Color) -> bool:
        """
        Direct, non-recursive check of a drawback without going through legal_moves.
        Returns True if the move is illegal due to drawbacks, False if legal.
        """
        assert move is not None, "Move cannot be None"
        assert color in [chess.WHITE, chess.BLACK], f"Invalid color: {color}"
        
        drawback_name = self.get_active_drawback(color)
        if not drawback_name:
            return False  # No drawback, move is legal
            
        # Get check function for this drawback
        check_function = get_drawback_function(drawback_name)
        assert check_function is not None, f"No check function found for drawback '{drawback_name}'"
        
        # Call the check function directly - try standard parameter order first
        result = check_function(self, move, color)
        return result  # True means illegal

    def _check_drawbacks(self, move: chess.Move, color: chess.Color) -> bool:
        """
        Check if a move is legal according to active drawbacks.
        Returns True if move is LEGAL, False if ILLEGAL.
        """
        # Use the non-recursive check method
        return not self._is_drawback_illegal(move, color)

    def copy(self) -> 'DrawbackBoard':
        new_board = DrawbackBoard(fen=self.fen())
        new_board._white_drawback = self._white_drawback
        new_board._black_drawback = self._black_drawback
        new_board._in_search = self._in_search  # Copy the search flag
        return new_board

    def _is_pseudo_legal(self, move: chess.Move) -> bool:
        """Check if a move is pseudo-legal without causing recursion"""
        # Get the piece at the from-square
        piece = self.piece_at(move.from_square)
        
        # If there's no piece or it's not our turn, move is illegal
        if not piece or piece.color != self.turn:
            return False
            
        # Check if the move is valid for the piece type (simplified)
        # This is a basic implementation - the full chess rules would be more complex
        if piece.piece_type == chess.PAWN:
            # Simplified pawn move check
            return self._is_pawn_move_pseudo_legal(move)
        elif piece.piece_type == chess.KNIGHT:
            # Knight move check - calculate offset
            from_rank, from_file = chess.square_rank(move.from_square), chess.square_file(move.from_square)
            to_rank, to_file = chess.square_rank(move.to_square), chess.square_file(move.to_square)
            
            rank_diff = abs(to_rank - from_rank)
            file_diff = abs(to_file - from_file)
            
            # Knight moves in L-shape: 2 squares in one direction, 1 in the other
            return (rank_diff == 2 and file_diff == 1) or (rank_diff == 1 and file_diff == 2)
        elif piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]:
            # For these pieces, we'll use a simplified check that just ensures
            # we're not trying to move to a square occupied by our own piece
            target = self.piece_at(move.to_square)
            return target is None or target.color != piece.color
            
        return True  # Default to true for other cases

    def _is_pawn_move_pseudo_legal(self, move: chess.Move) -> bool:
        """Check if a pawn move is pseudo-legal without recursion"""
        piece = self.piece_at(move.from_square)
        if piece.piece_type != chess.PAWN:
            return False
            
        # Get basics
        from_rank = chess.square_rank(move.from_square)
        from_file = chess.square_file(move.from_square)
        to_rank = chess.square_rank(move.to_square)
        to_file = chess.square_file(move.to_square)
        
        # Direction depends on color
        direction = 1 if piece.color == chess.WHITE else -1
        
        # Normal forward move
        if from_file == to_file:
            # Single square forward
            if to_rank == from_rank + direction:
                return self.piece_at(move.to_square) is None
            # Double square forward from starting position
            elif (piece.color == chess.WHITE and from_rank == 1 and to_rank == 3) or \
                 (piece.color == chess.BLACK and from_rank == 6 and to_rank == 4):
                middle_square = chess.square(from_file, from_rank + direction)
                return self.piece_at(move.to_square) is None and self.piece_at(middle_square) is None
        
        # Capture move (diagonal)
        elif abs(to_file - from_file) == 1 and to_rank == from_rank + direction:
            target = self.piece_at(move.to_square)
            return target is not None and target.color != piece.color
        
        return False

    def _is_game_over_simple(self) -> bool:
        """Simple non-recursive check if the game is over"""
        # Check kings without recursion
        white_king_found = False
        black_king_found = False
        
        for square, piece in self.piece_map().items():
            if piece.piece_type == chess.KING:
                if piece.color == chess.WHITE:
                    white_king_found = True
                else:
                    black_king_found = True
        
        return not (white_king_found and black_king_found)
