"""
Chess opening book parser and utility functions.
Used to read and match positions from a book of GM-level games.
"""
import os
import chess
import re
import hashlib

class OpeningBook:
    """
    Parses and stores an opening book from a text file containing GM games.
    Allows for fast matching of positions and retrieval of good follow-up moves.
    """
    def __init__(self, book_path="AI/Book.txt"):
        self.positions = {}  # Position hash -> [(move, frequency), ...]
        self.loaded = False
        self.hash_table = {}  # FEN -> hash for quick lookups
        try:
            self.load_book(book_path)
            self.loaded = True
        except Exception as e:
            print(f"Error loading opening book: {e}")

    def load_book(self, book_path):
        """Load and parse the opening book file"""
        if not os.path.exists(book_path):
            print(f"Warning: Opening book file not found at {book_path}")
            return

        print(f"Loading opening book from {book_path}...")
        
        # Parse the book file
        try:
            with open(book_path, 'r') as f:
                lines = f.readlines()
            
            game_count = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Try to extract moves from the line
                moves_pattern = re.compile(r'\b[a-h][1-8][a-h][1-8][qrbn]?\b')
                moves = moves_pattern.findall(line)
                
                if moves:
                    game_count += 1
                    self._process_game_moves(moves)
            
            print(f"Opening book loaded: {game_count} games, {len(self.positions)} unique positions")
        except Exception as e:
            print(f"Error parsing opening book: {e}")
            raise

    def _process_game_moves(self, moves):
        """Process a sequence of moves from a game and record positions"""
        board = chess.Board()
        
        for i, move_str in enumerate(moves):
            # Skip if we're already deep in the game (only care about openings)
            if i > 20:  # Only consider first 20 moves of each game
                break
                
            # Try to convert the move string to a chess.Move
            try:
                # Convert from basic coordinate notation (e2e4) to Move object
                from_square = chess.parse_square(move_str[:2])
                to_square = chess.parse_square(move_str[2:4])
                
                # Handle promotions
                if len(move_str) == 5:
                    promotion_map = {'q': chess.QUEEN, 'r': chess.ROOK, 
                                     'n': chess.KNIGHT, 'b': chess.BISHOP}
                    promo = promotion_map.get(move_str[4].lower(), None)
                    move = chess.Move(from_square, to_square, promotion=promo)
                else:
                    move = chess.Move(from_square, to_square)
                
                # Skip if move is not legal
                if move not in board.legal_moves:
                    break
                    
                # Record the position and the move played
                position_hash = self._get_position_hash(board)
                if position_hash not in self.positions:
                    self.positions[position_hash] = []
                    
                # Add or update the move frequency
                move_found = False
                for idx, (existing_move, freq) in enumerate(self.positions[position_hash]):
                    if existing_move == move:
                        self.positions[position_hash][idx] = (existing_move, freq + 1)
                        move_found = True
                        break
                        
                if not move_found:
                    self.positions[position_hash].append((move, 1))
                    
                # Apply the move and continue
                board.push(move)
                
            except (ValueError, IndexError):
                # Malformed move, skip to next game
                break

    def _get_position_key(self, board):
        """Convert board to a normalized FEN for position lookup"""
        # We only care about piece positions and side to move
        fen_parts = board.fen().split(' ')
        return f"{fen_parts[0]} {fen_parts[1]}"
    
    def _get_position_hash(self, board):
        """Get a hash of the position for faster lookups"""
        fen_key = self._get_position_key(board)
        
        # Check if we've already computed this hash
        if fen_key in self.hash_table:
            return self.hash_table[fen_key]
            
        # Compute hash and store it
        position_hash = hashlib.md5(fen_key.encode()).hexdigest()
        self.hash_table[fen_key] = position_hash
        return position_hash

    def get_book_moves(self, board):
        """Get book moves for current position with their frequency"""
        if not self.loaded:
            return []
            
        position_hash = self._get_position_hash(board)
        return self.positions.get(position_hash, [])

# Create a singleton instance that can be imported elsewhere
OPENING_BOOK = OpeningBook()
