"""
Parser for standard chess openings in CSV format with improved error handling
"""
import csv
import chess
import os
import re

class OpeningCSVParser:
    """
    Parses chess openings from a CSV file with ECO codes, names, and move sequences
    with enhanced error handling and validation
    """
    def __init__(self, csv_path=None):
        self.openings = []
        self.parsing_errors = []
        
        # If no path is provided, use the default path
        if not csv_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(base_dir, "BookMoves", "chess_openings.csv")
        
        self.load_openings(csv_path)
    
    def load_openings(self, csv_path):
        """Load openings from the CSV file with improved error handling"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'ECO' not in row or 'name' not in row or 'moves' not in row:
                        continue
                    
                    eco = row['ECO'].strip()
                    name = row['name'].strip()
                    moves_str = row['moves'].strip()
                    
                    # Store the opening regardless of move validity
                    # We'll validate moves during position building
                    self.openings.append({
                        'eco': eco,
                        'name': name,
                        'moves_str': moves_str
                    })
                
            print(f"Loaded {len(self.openings)} openings from CSV file: {os.path.basename(csv_path)}")
        except Exception as e:
            print(f"Error loading openings CSV: {e}")
            self.openings = []
    
    def normalize_moves_string(self, moves_str):
        """Clean up and normalize the moves string format"""
        # Remove move numbers and their periods
        cleaned = re.sub(r'\d+\.+\s*', '', moves_str)
        # Remove ellipses
        cleaned = re.sub(r'\.\.\.', '', cleaned)
        # Normalize spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def build_positions_dict(self, debug_level=0):
        """
        Convert opening moves into a dictionary mapping positions to moves
        Format: {position_fen: {move_uci: frequency, ...}, ...}
        
        Args:
            debug_level: 0=minimal output, 1=summary only, 2=detailed
        """
        positions_dict = {}
        processed_count = 0
        failed_count = 0
        
        if debug_level >= 2:
            print("Building opening book from CSV data...")
        
        for opening_idx, opening in enumerate(self.openings):
            try:
                moves_str = self.normalize_moves_string(opening['moves_str'])
                board = chess.Board()
                
                # For very detailed debugging (level 3+)
                if debug_level >= 3 and opening_idx % 100 == 0:
                    print(f"Processing opening {opening_idx}/{len(self.openings)}: {opening['name']}")
                    print(f"  Moves: {moves_str}")
                
                # Process each move in sequence
                moves_list = moves_str.split()
                success = True
                
                for move_idx, move_san in enumerate(moves_list):
                    # Store current position before making the move
                    position_fen = board.fen().split(' ')[0]  # Just the piece placement part
                    
                    try:
                        # Try to parse the move in SAN format
                        move = board.parse_san(move_san)
                        
                        # Store this move as an option from the current position
                        if position_fen not in positions_dict:
                            positions_dict[position_fen] = {}
                        
                        # Convert move to UCI format for consistency
                        move_uci = move.uci()
                        positions_dict[position_fen][move_uci] = positions_dict[position_fen].get(move_uci, 0) + 1
                        
                        # Make the move to continue to next position
                        board.push(move)
                        processed_count += 1
                        
                    except ValueError:
                        # Just skip invalid moves and continue with the next opening
                        if debug_level >= 2:
                            print(f"Invalid move '{move_san}' in opening '{opening['name']}' (move {move_idx+1})")
                        success = False
                        failed_count += 1
                        break
                    except Exception as e:
                        # Handle any other exceptions that might occur
                        if debug_level >= 2:
                            print(f"Error processing move '{move_san}': {str(e)}")
                        success = False
                        failed_count += 1
                        break
                
                # Show success for detailed debugging
                if debug_level >= 3 and success:
                    print(f"  Successfully processed opening: {opening['name']}")
                    
            except Exception as e:
                # Log the error but continue processing other openings
                failed_count += 1
                if debug_level >= 1:
                    print(f"Error processing opening '{opening.get('name', 'unknown')}': {str(e)}")
        
        # Print summary statistics
        if debug_level >= 1:
            print(f"Built opening book with {len(positions_dict)} unique positions from {processed_count} valid moves")
            print(f"Failed to process {failed_count} moves out of {len(self.openings)} openings")
        
        return positions_dict

# Create a singleton instance
OPENING_CSV_PARSER = OpeningCSVParser()
