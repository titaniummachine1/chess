"""
Chess opening book parser with hardcoded main lines for common openings
"""
import os
import chess
import re
import hashlib

# Bonus value for book moves (in centipawns)
BOOK_MOVE_BONUS = 35  # Slightly lower bonus to prevent book moves from dominating

class OpeningBook:
    """
    Manages opening theory and provides access to trusted opening moves
    with built-in fallback options if the book file isn't available.
    """
    def __init__(self, book_path="AI/Book.txt"):
        self.positions = {}  # Position hash -> [(move, frequency), ...]
        self.loaded = False
        self.hash_table = {}  # FEN -> hash for quick lookups
        
        # Add hardcoded opening lines for common positions
        self.initialize_hardcoded_lines()
        
        # Try to load external book file if available
        try:
            self.load_book(book_path)
            self.loaded = True
        except Exception as e:
            print(f"Using built-in opening lines only. External book error: {e}")

    def initialize_hardcoded_lines(self):
        """Initialize hardcoded opening lines for common positions"""
        self.hardcoded_positions = {}
        
        # Standard first moves for White
        start_pos = chess.Board()
        self.add_position_move(start_pos, "e2e4", 8)  # e4 - slightly preferred
        self.add_position_move(start_pos, "d2d4", 7)  # d4
        self.add_position_move(start_pos, "c2c4", 5)  # English
        self.add_position_move(start_pos, "g1f3", 5)  # Nf3
        
        # Responses to e4
        e4_pos = chess.Board()
        e4_pos.push_uci("e2e4")
        self.add_position_move(e4_pos, "e7e5", 8)    # Open game
        self.add_position_move(e4_pos, "c7c5", 7)    # Sicilian
        self.add_position_move(e4_pos, "e7e6", 6)    # French
        self.add_position_move(e4_pos, "c7c6", 5)    # Caro-Kann
        
        # Responses to d4
        d4_pos = chess.Board()
        d4_pos.push_uci("d2d4")
        self.add_position_move(d4_pos, "d7d5", 8)    # Queen's pawn
        self.add_position_move(d4_pos, "g8f6", 7)    # Indian defense
        self.add_position_move(d4_pos, "e7e6", 6)    # Various defenses
        
        # Common e4 e5 continuations
        e4e5_pos = chess.Board()
        e4e5_pos.push_uci("e2e4")
        e4e5_pos.push_uci("e7e5")
        self.add_position_move(e4e5_pos, "g1f3", 9)   # King's Knight
        self.add_position_move(e4e5_pos, "f1c4", 6)   # Italian/Bishop's opening

        # Response to e4 e5 Nf3
        e4e5nf3_pos = chess.Board()
        e4e5nf3_pos.push_uci("e2e4")
        e4e5nf3_pos.push_uci("e7e5")
        e4e5nf3_pos.push_uci("g1f3")
        self.add_position_move(e4e5nf3_pos, "b8c6", 8)  # Knight development
        self.add_position_move(e4e5nf3_pos, "g8f6", 6)  # Petrov/Russian
        
        # More positions can be added as needed
        
        print("Initialized hardcoded opening lines")

    def add_position_move(self, board, move_uci, weight=1):
        """Add a position and corresponding move to the book"""
        try:
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                return False
                
            # Create position hash
            position_hash = self._get_position_hash(board)
            if position_hash not in self.positions:
                self.positions[position_hash] = []
                
            # Add the move with its weight
            self.positions[position_hash].append((move, weight))
            return True
        except:
            return False

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
            
            print(f"External opening book loaded: {game_count} games, {len(self.positions)} unique positions")
        except Exception as e:
            print(f"Error parsing opening book: {e}")
            raise

    def _process_game_moves(self, moves):
        """Process a sequence of moves from a game and record positions"""
        board = chess.Board()
        
        for i, move_str in enumerate(moves):
            # Skip if we're already deep in the game (only care about openings)
            if i > 17:  # Only consider first 17 moves of each game
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
        position_hash = self._get_position_hash(board)
        return self.positions.get(position_hash, [])
    
    def get_best_book_move(self, board):
        """Get the best book move with highest weight for current position"""
        book_moves = self.get_book_moves(board)
        if not book_moves:
            return None
            
        # Sort by frequency and pick the highest
        book_moves.sort(key=lambda x: x[1], reverse=True)
        return book_moves[0][0]  # Return the move with highest weight

# Create a singleton instance that can be imported elsewhere
OPENING_BOOK = OpeningBook()

def get_book_move(board):
    """Get a move from the opening book based on position"""
    return OPENING_BOOK.get_best_book_move(board)

def is_book_position(board):
    """Check if the current position is in the opening book"""
    return bool(OPENING_BOOK.get_book_moves(board))
