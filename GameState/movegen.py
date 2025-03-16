## movegen.py contains the custom board class for Drawback Chess, which extends the standard python-chess board class.
from typing import Iterator, Optional, List, Union, Dict, Set
from GameState.drawback_manager import (
    get_drawback_info, get_drawback_function, get_drawback_loss_function
)
from collections import Counter
import chess
import random

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - Standard starting FEN (white on bottom, black on top).
      - Ignores checks, can capture king.
      - Drawback-based restrictions.
      - Implements 3-fold repetition.
      - Implements insufficient material draws using chess.com rules.
      - Implements king en passant capture during castling.
    """

    def __init__(self, fen: str = chess.STARTING_FEN, white_drawback: Optional[str] = None, black_drawback: Optional[str] = None):
        """
        Initialize the board with optional white and black drawbacks
        
        Args:
            fen: The FEN string to initialize the board with
            white_drawback: The name of the drawback for the white player (None for no drawback)
            black_drawback: The name of the drawback for the black player (None for no drawback)
        """
        super().__init__(fen)
        self._white_drawback = white_drawback
        self._black_drawback = black_drawback
        self._in_search = False  # Flag to indicate when we're in a search context
        self._last_moved_piece = None
        self._last_capture_square = None
        self._position_history = []  # Track position history for 3-fold repetition
        self._castling_king_passed_squares = []  # Track squares king passed during castling
        self._lastmove_was_capture = False
        self._lastmove_captured_piece = None
        self._move_history = []  # List of (move, was_capture, captured_piece)

    def reset(self, fen: str = chess.STARTING_FEN) -> None:
        """Reset the board to the starting position"""
        super().reset()
        self._white_drawback = None
        self._black_drawback = None
        self._position_history = []
        self._castling_king_passed_squares = []
        self._lastmove_was_capture = False
        self._lastmove_captured_piece = None
        self._move_history = []

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
        """
        Generate legal moves modified for Drawback Chess, including king en passant capture.
        """
        # Generate standard pseudo-legal moves
        for move in self.generate_pseudo_legal_moves(from_mask, to_mask):
            # Skip moves that violate the active drawback
            if self._is_drawback_illegal(move, self.turn):
                continue
                
            yield move
            
        # Add king en passant captures if available and if king castled last move
        if self._castling_king_passed_squares:
            for passed_square in self._castling_king_passed_squares:
                # Get the rank and file of the passed square
                rank = chess.square_rank(passed_square)
                file = chess.square_file(passed_square)
                
                # Check horizontally adjacent squares (same rank, adjacent files)
                for file_offset in [-1, 1]:
                    adj_file = file + file_offset
                    if 0 <= adj_file < 8:  # Ensure file is on board
                        adj_square = chess.square(adj_file, rank)
                        
                        # Check if there's a piece there that belongs to the current player
                        piece = self.piece_at(adj_square)
                        if piece and piece.color == self.turn:
                            # Create a special "king en passant" capture move
                            en_passant_move = chess.Move(adj_square, passed_square)
                            
                            # Check if this move would violate the active drawback
                            if not self._is_drawback_illegal(en_passant_move, self.turn):
                                yield en_passant_move
                
                # Check all squares on the same file (vertical captures from any distance)
                for check_rank in range(8):
                    if check_rank == rank:  # Skip the passed square itself
                        continue
                        
                    check_square = chess.square(file, check_rank)
                    
                    # Check if there's a piece there that belongs to the current player
                    piece = self.piece_at(check_square)
                    if piece and piece.color == self.turn:
                        # Create a special "king en passant" capture move
                        en_passant_move = chess.Move(check_square, passed_square)
                        
                        # Check if this move would violate the active drawback
                        if not self._is_drawback_illegal(en_passant_move, self.turn):
                            yield en_passant_move

    def is_variant_end(self) -> bool:
        """
        In Drawback Chess, the game ends when one of the kings is captured,
        when a player has no legal moves due to drawback restrictions,
        or when standard draw conditions are met (3-fold repetition, insufficient material).
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

        # Check for 3-fold repetition
        if self.is_threefold_repetition():
            return True
            
        # Check for insufficient material
        if self.has_insufficient_material():
            return True

        # Check for special drawback-related loss conditions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            # Check explicit loss condition function
            loss_function = get_drawback_loss_function(active_drawback)
            if loss_function and loss_function(self, self.turn):
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
                    
        # No other end conditions
        return False

    def is_variant_win(self) -> bool:
        """
        In Drawback Chess, you win by capturing the opponent's king
        or if the opponent has no legal moves.
        """
        # Check if opponent lost their king
        if self.turn == chess.WHITE:
            # White's turn - check if Black's king is gone
            black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                                 for p in self.piece_map().values())
            if not black_king_alive:
                return True
        else:
            # Black's turn - check if White's king is gone
            white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                                 for p in self.piece_map().values())
            if not white_king_alive:
                return True
        
        # Check if opponent has no legal moves due to drawback
        opponent_color = not self.turn
        opponent_drawback = self.get_active_drawback(opponent_color)
        
        if opponent_drawback:
            # Create a hypothetical board with opponent's turn
            test_board = self.copy()
            test_board.turn = opponent_color
            
            # Check if there are any legal moves
            legal_moves_exist = any(True for _ in test_board.legal_moves)
            
            if not legal_moves_exist:
                # Opponent has no legal moves - current player wins
                return True
        
        return False

    def is_variant_loss(self) -> bool:
        """
        In Drawback Chess, you lose when:
        1. Your king is captured
        2. You have no legal moves due to drawback restrictions
        """
        # Check if current player's king is gone
        if self.turn == chess.WHITE:
            white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                                 for p in self.piece_map().values())
            if not white_king_alive:
                return True
        else:
            black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                                 for p in self.piece_map().values())
            if not black_king_alive:
                return True
                
        # Check if current player has no legal moves due to drawback
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            legal_moves_exist = any(True for _ in self.legal_moves)
            if not legal_moves_exist:
                # Current player has no legal moves - current player loses
                return True
                
        return False

    def is_variant_draw(self) -> bool:
        """
        In Drawback Chess, draws occur in the following cases:
        1. Threefold repetition
        2. Insufficient material
        """
        # Check for threefold repetition
        if self.is_threefold_repetition():
            return True
            
        # Check for insufficient material
        if self.has_insufficient_material():
            return True
            
        return False

    def is_threefold_repetition(self) -> bool:
        """
        Override the threefold repetition detection to use our custom position tracking
        and avoid recursion with has_legal_en_passant.
        """
        # Use our own position history tracking instead of the parent's implementation
        if not self._position_history:
            return False
            
        # Count positions
        positions = {}
        for position in self._position_history:
            positions[position] = positions.get(position, 0) + 1
            
        # Get current position without using epd() to avoid recursion
        current_position = self.board_fen()
        positions[current_position] = positions.get(current_position, 0) + 1
        
        # Check if any position appears 3 or more times
        for count in positions.values():
            if count >= 3:
                return True
                
        return False
    
    def has_insufficient_material(self) -> bool:
        """
        Check if the position has insufficient material to checkmate.
        Implements chess.com rules for insufficient material:
        - King vs King
        - King and Bishop vs King
        - King and Knight vs King
        - King and Bishop vs King and Bishop (same color bishops)
        """
        # Count pieces by type and color
        white_pieces = {chess.PAWN: 0, chess.KNIGHT: 0, chess.BISHOP: 0, chess.ROOK: 0, chess.QUEEN: 0}
        black_pieces = {chess.PAWN: 0, chess.KNIGHT: 0, chess.BISHOP: 0, chess.ROOK: 0, chess.QUEEN: 0}
        white_bishop_squares = []
        black_bishop_squares = []
        
        for square, piece in self.piece_map().items():
            if piece.piece_type == chess.KING:
                continue  # Skip kings
                
            if piece.color == chess.WHITE:
                white_pieces[piece.piece_type] += 1
                # Track bishop square
                if piece.piece_type == chess.BISHOP:
                    white_bishop_squares.append(square)
            else:
                black_pieces[piece.piece_type] += 1
                # Track bishop square
                if piece.piece_type == chess.BISHOP:
                    black_bishop_squares.append(square)
        
        # Early exit if any pawns, rooks, or queens exist
        if (white_pieces[chess.PAWN] > 0 or white_pieces[chess.ROOK] > 0 or white_pieces[chess.QUEEN] > 0 or
            black_pieces[chess.PAWN] > 0 or black_pieces[chess.ROOK] > 0 or black_pieces[chess.QUEEN] > 0):
            return False
        
        # Count total pieces (excluding kings)
        white_total = sum(white_pieces.values())
        black_total = sum(black_pieces.values())
        
        # Case 1: King vs King
        if white_total == 0 and black_total == 0:
            return True
            
        # Case 2: King and Bishop vs King or King and Knight vs King
        if (white_total == 1 and black_total == 0) or (white_total == 0 and black_total == 1):
            # Check if the piece is a bishop or knight
            if (white_pieces[chess.BISHOP] == 1 or white_pieces[chess.KNIGHT] == 1 or
                black_pieces[chess.BISHOP] == 1 or black_pieces[chess.KNIGHT] == 1):
                return True
            
        # Case 3: King and Bishop vs King and Bishop (same color bishops)
        if (white_pieces[chess.BISHOP] == 1 and black_pieces[chess.BISHOP] == 1 and
            white_total == 1 and black_total == 1):
            # Get the square colors
            white_square = white_bishop_squares[0]
            black_square = black_bishop_squares[0]
            
            # Check if bishops are on same color squares
            # A square is light if the sum of its file and rank is even
            white_square_color = (chess.square_file(white_square) + chess.square_rank(white_square)) % 2
            black_square_color = (chess.square_file(black_square) + chess.square_rank(black_square)) % 2
            
            # If both bishops are on the same color squares, it's a draw
            if white_square_color == black_square_color:
                return True
            else:
                return False
        
        return False

    def is_legal(self, move: chess.Move) -> bool:
        """
        In Drawback Chess, a move is legal if:
        1. It's a valid chess move (pseudo-legal)
        2. It doesn't violate the player's drawback
        
        Check and checkmate don't exist in this variant.
        """
        # Special case for king en passant capture
        if move.to_square in self._castling_king_passed_squares:
            piece = self.piece_at(move.from_square)
            if piece and piece.color == self.turn:
                from_file = chess.square_file(move.from_square)
                to_file = chess.square_file(move.to_square)
                from_rank = chess.square_rank(move.from_square)
                to_rank = chess.square_rank(move.to_square)
                
                horizontal_capture = from_rank == to_rank and abs(from_file - to_file) == 1
                vertical_capture = from_file == to_file
                
                if horizontal_capture or vertical_capture:
                    # Only check drawback restrictions
                    return self._check_drawbacks(move, self.turn)
        
        # Check if the move is a valid chess move (pseudo-legal)
        if not self.is_pseudo_legal(move):
            return False
            
        # Check drawback restrictions
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
        """
        Check if a move is pseudo-legal without causing recursion.
        Also handles the special king en passant capture.
        """
        # Special case: King en passant capture check
        if move.to_square in self._castling_king_passed_squares:
            # This is a potential king en passant capture
            piece = self.piece_at(move.from_square)
            
            # Check if the piece belongs to the current player
            if piece and piece.color == self.turn:
                # The piece must be adjacent to the king's path
                from_file = chess.square_file(move.from_square)
                to_file = chess.square_file(move.to_square)
                from_rank = chess.square_rank(move.from_square)
                to_rank = chess.square_rank(move.to_square)
                
                # The piece must be on the same rank and one file away
                if from_rank == to_rank and abs(from_file - to_file) == 1:
                    return True
        
        # Regular move legality check
        # Get the piece at the from-square
        piece = self.piece_at(move.from_square)
        
        # If there's no piece or it's not our turn, move is illegal
        if not piece or piece.color != self.turn:
            return False
            
        # Check if the move is valid for the piece type
        if piece.piece_type == chess.PAWN:
            return self._is_pawn_move_pseudo_legal(move)
        elif piece.piece_type == chess.KING:
            # Kings can move one square in any direction or castle
            from_file = chess.square_file(move.from_square)
            to_file = chess.square_file(move.to_square)
            from_rank = chess.square_rank(move.from_square)
            to_rank = chess.square_rank(move.to_square)
            
            # Normal king move: one square in any direction
            if max(abs(from_file - to_file), abs(from_rank - to_rank)) <= 1:
                # Cannot capture own pieces
                target = self.piece_at(move.to_square)
                return target is None or target.color != piece.color
                
            # Castling: king moves two squares horizontally
            elif from_rank == to_rank and abs(from_file - to_file) == 2:
                # Check if castling is possible (rook in place, path clear)
                if to_file > from_file:  # Kingside
                    # Check if path is clear
                    if any(self.piece_at(chess.square(file, from_rank)) 
                          for file in range(from_file + 1, 7)):
                        return False
                    # Check if rook is in place
                    rook_square = chess.square(7, from_rank)
                    rook = self.piece_at(rook_square)
                    return (rook and rook.piece_type == chess.ROOK and rook.color == piece.color)
                else:  # Queenside
                    # Check if path is clear
                    if any(self.piece_at(chess.square(file, from_rank)) 
                          for file in range(1, from_file)):
                        return False
                    # Check if rook is in place
                    rook_square = chess.square(0, from_rank)
                    rook = self.piece_at(rook_square)
                    return (rook and rook.piece_type == chess.ROOK and rook.color == piece.color)
            else:
                return False
        else:
            # For other pieces, delegate to parent class
            try:
                return super()._is_pseudo_legal(move)
            except (RecursionError, RuntimeError):
                # Fallback to simplified check if the parent method causes recursion
                return self._simplified_piece_move_check(piece, move)
                
    def _simplified_piece_move_check(self, piece, move):
        """Simplified move check for pieces if the parent method fails"""
        # Cannot capture own pieces
        target = self.piece_at(move.to_square)
        if target and target.color == piece.color:
            return False
            
        from_file = chess.square_file(move.from_square)
        to_file = chess.square_file(move.to_square)
        from_rank = chess.square_rank(move.from_square)
        to_rank = chess.square_rank(move.to_square)
        
        # Knight: L-shaped move
        if piece.piece_type == chess.KNIGHT:
            return (abs(from_file - to_file) == 2 and abs(from_rank - to_rank) == 1 or
                    abs(from_file - to_file) == 1 and abs(from_rank - to_rank) == 2)
                    
        # Bishop: diagonal movement
        elif piece.piece_type == chess.BISHOP:
            if abs(from_file - to_file) != abs(from_rank - to_rank):
                return False
                
            # Check if path is clear
            step_file = 1 if to_file > from_file else -1
            step_rank = 1 if to_rank > from_rank else -1
            
            check_file, check_rank = from_file + step_file, from_rank + step_rank
            while check_file != to_file and check_rank != to_rank:
                if self.piece_at(chess.square(check_file, check_rank)) is not None:
                    return False
                check_file += step_file
                check_rank += step_rank
                
            return True
            
        # Rook: horizontal/vertical movement
        elif piece.piece_type == chess.ROOK:
            if from_file != to_file and from_rank != to_rank:
                return False
                
            # Check if path is clear
            if from_file == to_file:  # Vertical movement
                step = 1 if to_rank > from_rank else -1
                for check_rank in range(from_rank + step, to_rank, step):
                    if self.piece_at(chess.square(from_file, check_rank)) is not None:
                        return False
            else:  # Horizontal movement
                step = 1 if to_file > from_file else -1
                for check_file in range(from_file + step, to_file, step):
                    if self.piece_at(chess.square(check_file, from_rank)) is not None:
                        return False
                        
            return True
            
        # Queen: combined bishop and rook movement
        elif piece.piece_type == chess.QUEEN:
            # Diagonal movement (like bishop)
            if abs(from_file - to_file) == abs(from_rank - to_rank):
                # Check if path is clear
                step_file = 1 if to_file > from_file else -1
                step_rank = 1 if to_rank > from_rank else -1
                
                check_file, check_rank = from_file + step_file, from_rank + step_rank
                while check_file != to_file and check_rank != to_rank:
                    if self.piece_at(chess.square(check_file, check_rank)) is not None:
                        return False
                    check_file += step_file
                    check_rank += step_rank
                    
                return True
                
            # Horizontal/vertical movement (like rook)
            elif from_file == to_file or from_rank == to_rank:
                if from_file == to_file:  # Vertical movement
                    step = 1 if to_rank > from_rank else -1
                    for check_rank in range(from_rank + step, to_rank, step):
                        if self.piece_at(chess.square(from_file, check_rank)) is not None:
                            return False
                else:  # Horizontal movement
                    step = 1 if to_file > from_file else -1
                    for check_file in range(from_file + step, to_file, step):
                        if self.piece_at(chess.square(check_file, from_rank)) is not None:
                            return False
                            
                return True
                
            else:
                return False
                
        return False

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

    def push(self, move: chess.Move) -> None:
        """
        Enhanced push that tracks additional information needed for drawbacks
        and implements king en passant capture during castling.
        """
        # Track information before making the move
        moving_piece = self.piece_at(move.from_square)
        target_piece = self.piece_at(move.to_square)
        is_capture = target_piece is not None
        
        # Check for castling to implement king en passant
        castling_move = False
        self._castling_king_passed_squares = []  # Reset passed squares
        
        if (moving_piece and moving_piece.piece_type == chess.KING and 
            abs(chess.square_file(move.from_square) - chess.square_file(move.to_square)) > 1):
            # This is a castling move
            castling_move = True
            rank = chess.square_rank(move.from_square)
            from_file = chess.square_file(move.from_square)
            to_file = chess.square_file(move.to_square)
            
            # Store the square the king passes through during castling
            # (this square can be used for en passant capture of the king)
            passed_file = from_file + (1 if to_file > from_file else -1)
            passed_square = chess.square(passed_file, rank)
            self._castling_king_passed_squares.append(passed_square)
        
        # Execute the move using the parent method
        super().push(move)
        
        # Store current position for 3-fold repetition detection AFTER making the move
        position_key = self.epd()
        self._position_history.append(position_key)
        
        # Store the last moved piece and capture information
        self._last_moved_piece = moving_piece
        
        # Handle piece capture tracking
        if is_capture:
            self._last_capture_square = move.to_square
            self._lastmove_was_capture = True
            self._lastmove_captured_piece = target_piece
        else:
            self._last_capture_square = None
            self._lastmove_was_capture = False
            self._lastmove_captured_piece = None

    def pop(self) -> chess.Move:
        """
        Enhanced pop that clears the tracked move information and
        removes the last position from history.
        """
        # Remove the last position from history
        if self._position_history:
            self._position_history.pop()
            
        # Reset king passed squares from castling
        self._castling_king_passed_squares = []
            
        # Execute standard pop
        return super().pop()

    def check_drawback_win(self, color, drawback_name) -> bool:
        """
        Check if the specified player has won due to a drawback condition.
        This is a standardized method to ensure consistent evaluation for both players.
        
        Args:
            color: The player to check for winning (chess.WHITE or chess.BLACK)
            drawback_name: The name of the drawback to check
            
        Returns:
            bool: True if player has won due to the drawback, False otherwise
        """
        opponent = not color
        
        # Special case for atomic bomb - we need to check adjacency to king
        if drawback_name == "atomic_bomb":
            # First ensure there's a move stack and a last capture square
            if len(self.move_stack) == 0 or not hasattr(self, '_last_capture_square') or self._last_capture_square is None:
                return False
                
            last_move = self.move_stack[-1]
            # CRITICAL: Only consider actual captures for atomic bomb
            if not self.is_capture(last_move):
                return False
                
            # Find the opponent's king
            king_square = None
            for square, piece in self.piece_map().items():
                if piece and piece.piece_type == chess.KING and piece.color == opponent:
                    king_square = square
                    break
            
            if king_square is not None:
                # Check if the last capture was adjacent to the king
                capture_square = self._last_capture_square
                king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
                capture_file = chess.square_file(capture_square)
                capture_rank = chess.square_rank(capture_square)
                
                # If they're adjacent (within 1 square in any direction)
                if abs(king_file - capture_file) <= 1 and abs(king_rank - capture_rank) <= 1:
                    if king_square != capture_square:  # Not the king itself
                        # For debugging
                        print(f"Drawback win: {color} won by atomic bomb - " +
                              f"Capture at {chess.square_name(capture_square)} " +
                              f"adjacent to {opponent} king at {chess.square_name(king_square)}")
                        return True
        
        # For other drawbacks, use the loss function from drawback_manager
        try:
            loss_function = get_drawback_loss_function(drawback_name)
            if loss_function and loss_function(self, opponent):
                return True
        except (ImportError, Exception):
            pass
            
        return False

    def get_last_move_info(self):
        """
        Return information about the last move for drawbacks to use
        
        Returns:
            tuple: (was_capture, captured_piece, move)
        """
        if not self._move_history:
            return False, None, None
            
        move, was_capture, captured_piece = self._move_history[-1]
        return was_capture, captured_piece, move

    # Override has_legal_en_passant to avoid recursion
    def has_legal_en_passant(self) -> bool:
        """
        Custom implementation to avoid calling into generate_legal_ep which calls is_variant_end.
        In Drawback Chess, en passant is always legal if the ep_square is set.
        """
        return self.ep_square is not None
