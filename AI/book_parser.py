"""
Chess opening book parser that integrates both GM games and standard openings
with improved error handling for captures
"""

import os
import chess
import random
from AI.opening_csv_parser import OPENING_CSV_PARSER

class OpeningBook:
    """
    A combined opening book that uses both GM games and standard chess openings
    with enhanced capture validation
    """
    def __init__(self, book_file=None, debug_level=1):
        self.positions = {}
        self.unique_positions = 0
        self.total_games = 0
        self.debug_level = debug_level
        
        # If no path is provided, use the default path
        if not book_file:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            book_file = os.path.join(base_dir, "BookMoves", "GMGAMES.txt")
        
        # First load GM games
        self.load_gm_games(book_file)
        
        # Then load standard openings from CSV
        self.integrate_csv_openings()
    
    def load_gm_games(self, book_file):
        """Load GM games from text file with improved error handling"""
        if self.debug_level >= 1:
            print(f"Loading opening book from {book_file}...")
        
        try:
            with open(book_file, 'r') as f:
                lines = f.readlines()
            
            # Count games for stats
            game_count = 0
            
            # Process each line which contains moves from one game
            for line in lines:
                game_count += 1
                self.process_gm_game(line.strip())
            
            self.total_games += game_count
            if self.debug_level >= 1:
                print(f"Opening book loaded: {game_count} games, {self.unique_positions} unique positions")
        except FileNotFoundError:
            print(f"Warning: Opening book file {book_file} not found!")
        except Exception as e:
            print(f"Error loading opening book: {e}")
    
    def process_gm_game(self, moves_text):
        """Process a single GM game with improved error handling"""
        board = chess.Board()
        
        # Parse the moves
        moves = moves_text.split()
        for m in moves:
            try:
                # Extract just the position part of the FEN
                position = board.fen().split(' ')[0]  # Just piece placement
                
                # Validate the move format
                if not (len(m) >= 4 and all(c in 'abcdefgh12345678' for c in m[:4])):
                    continue
                
                # Parse and make the move
                move = chess.Move.from_uci(m)
                
                # Check if the move is legal in this position
                if move not in board.legal_moves:
                    continue
                    
                # Add the move to our database
                if position not in self.positions:
                    self.positions[position] = {}
                    self.unique_positions += 1
                
                self.positions[position][m] = self.positions[position].get(m, 0) + 1
                
                # Apply the move to advance the position
                board.push(move)
            except Exception:
                # Skip any invalid moves
                break
    
    def integrate_csv_openings(self):
        """Integrate openings from the CSV parser with improved validation"""
        # Get position dictionary from CSV openings - use the debug level
        csv_positions = OPENING_CSV_PARSER.build_positions_dict(debug_level=self.debug_level)
        
        if self.debug_level >= 1:
            print(f"Integrating {len(csv_positions)} positions from standard openings...")
        
        # Merge with our existing positions
        added_positions = 0
        for position, moves in csv_positions.items():
            if position not in self.positions:
                self.positions[position] = moves
                self.unique_positions += 1
                added_positions += 1
            else:
                # Merge move frequencies
                for move, frequency in moves.items():
                    self.positions[position][move] = self.positions[position].get(move, 0) + frequency
        
        if self.debug_level >= 1:
            print(f"Added {added_positions} new positions from CSV openings")
            print(f"Combined opening book now contains {self.unique_positions} unique positions")
    
    def get_book_moves(self, board):
        """
        Get all book moves for a given position with their weights/frequencies
        Returns: List of (move, frequency) tuples
        """
        # Extract just the piece placement from FEN for consistent lookups
        position = board.fen().split(' ')[0]
        
        # Check if we have this position in our book
        if position not in self.positions:
            return []
        
        # Get all moves for this position
        book_moves_dict = self.positions[position]
        
        # Convert to list of move objects with weights
        result = []
        for uci_move, frequency in book_moves_dict.items():
            try:
                # Ensure move string has correct format
                if len(uci_move) < 4:
                    continue
                
                # Create the move object
                from_square = chess.parse_square(uci_move[0:2])
                to_square = chess.parse_square(uci_move[2:4])
                
                # Handle promotions
                promotion = None
                if len(uci_move) > 4:
                    promotion_char = uci_move[4].lower()
                    if promotion_char == 'q':
                        promotion = chess.QUEEN
                    elif promotion_char == 'r':
                        promotion = chess.ROOK
                    elif promotion_char == 'b':
                        promotion = chess.BISHOP
                    elif promotion_char == 'n':
                        promotion = chess.KNIGHT
                
                # Create move with or without promotion
                move = chess.Move(from_square, to_square, promotion)
                
                # Validate the move is legal in current position
                if move in board.legal_moves:
                    result.append((move, frequency))
                elif self.debug_level >= 2:
                    print(f"Skipping illegal book move: {uci_move} in position {position}")
            except ValueError:
                # Skip invalid moves
                if self.debug_level >= 2:
                    print(f"Skipping invalid book move format: {uci_move}")
                continue
            except Exception as e:
                # Skip other errors
                if self.debug_level >= 2:
                    print(f"Error processing book move {uci_move}: {str(e)}")
                continue
        
        return result
    
    def is_book_position(self, board):
        """Check if a position is in the opening book"""
        position = board.fen().split(' ')[0]
        return position in self.positions

# Create a singleton instance with normal debug level
OPENING_BOOK = OpeningBook(debug_level=1)

def is_book_position(board):
    """Convenience function to check if a position is in the book"""
    return OPENING_BOOK.is_book_position(board)
