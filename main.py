"""
Drawback Chess - Main Game Module
A chess variant where each player has a drawback (rule restriction)
"""
import pygame as p
import chess
import random
import asyncio

# Import utilities and board drawing functions
from utils import load_images, draw_board, draw_pieces, draw_legal_move_indicators
from utils import WIDTH, HEIGHT, BOARD_HEIGHT, BOARD_Y_OFFSET, BOARD_X_OFFSET, DIMENSION, SQ_SIZE

# Import game logic
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS as AVAILABLE_DRAWBACKS

# Import global settings
from Globals import (
    FPS, AI_DEPTH, WHITE_AI, BLACK_AI, DRAWBACKS, TIME_LIMIT,  # Add TIME_LIMIT here
    GAME_OVER, WINNER_COLOR, FLIPPED_BOARD, AI_MOVE_COOLDOWN, SEARCH_IN_PROGRESS,
    TINKER_BUTTON_WIDTH, TINKER_BUTTON_HEIGHT, TINKER_BUTTON_TOP, TINKER_BUTTON_COLOR,
    TEXT_COLOR_WHITE, TEXT_COLOR_BLACK, HIGHLIGHT_COLOR, GOLD_COLOR, STATUS_BG_COLOR
)

# UI panel setup
try:
    from ui.tinker_panel import TinkerPanel
    HAS_TINKER_PANEL = True
    print("Tinker Panel UI loaded successfully")
except Exception as panel_error:
    print(f"Warning: Tinker Panel failed to load: {panel_error}")
    import traceback
    traceback.print_exc()
    HAS_TINKER_PANEL = False

# Import AI async functions
try:
    print("Attempting to import AI module...")
    from AI.async_engine import start_search, get_progress, get_result, is_search_complete, reset_search
    HAS_AI = True
    print("AI module imported successfully")
except Exception as e:
    print(f"Warning: AI module not available. Error: {e}")
    import traceback
    traceback.print_exc()
    HAS_AI = False

# Global state variables
game_over = GAME_OVER
winner_color = WINNER_COLOR
flipped = FLIPPED_BOARD
ai_move_cooldown = AI_MOVE_COOLDOWN
search_in_progress = SEARCH_IN_PROGRESS
time_limit = TIME_LIMIT  # Add this line to track the time limit
tinker_button_rect = p.Rect(WIDTH - TINKER_BUTTON_WIDTH, TINKER_BUTTON_TOP, 
                           TINKER_BUTTON_WIDTH, TINKER_BUTTON_HEIGHT)

def display_drawbacks(screen, board, flipped):
    """Display the active drawbacks for each player on screen"""
    font = p.font.SysFont(None, 22)
    white_drawback = board.get_active_drawback(chess.WHITE) or "None"
    black_drawback = board.get_active_drawback(chess.BLACK) or "None"
    
    # Just show the formatted name instead of the description
    white_display = white_drawback.replace('_', ' ').title() if white_drawback != "None" else "None"
    black_display = black_drawback.replace('_', ' ').title() if black_drawback != "None" else "None"
    
    # Create the text surfaces
    white_text = font.render(f"White: {white_display}", True, TEXT_COLOR_WHITE, TEXT_COLOR_BLACK)
    black_text = font.render(f"Black: {black_display}", True, TEXT_COLOR_BLACK, TEXT_COLOR_WHITE)
    
    # Position based on flipped state - this ensures they're always on the correct side
    if not flipped:
        # Normal orientation: White on bottom of screen, black on top
        screen.blit(white_text, (10, HEIGHT - 30))
        screen.blit(black_text, (10, 10))
    else:
        # Flipped: White on top of screen, black on bottom
        screen.blit(white_text, (10, 10))
        screen.blit(black_text, (10, HEIGHT - 30))

def display_current_turn(screen, board):
    """Display whose turn it is at the top of the screen"""
    font = p.font.SysFont(None, 22)
    # Simplify to just "White" or "Black"
    turn_text = "White" if board.turn == chess.WHITE else "Black"
    color = TEXT_COLOR_WHITE if board.turn == chess.WHITE else TEXT_COLOR_BLACK
    bg_color = TEXT_COLOR_BLACK if board.turn == chess.WHITE else TEXT_COLOR_WHITE
    text_surf = font.render(turn_text, True, color, bg_color)
    screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, 10))

def display_winner(screen, winner_color):
    """Display the game over message with the winner"""
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king! Press 'R' to restart."
    text_surf = font.render(text, True, TEXT_COLOR_BLACK, GOLD_COLOR)
    text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

def draw_tinker_button(screen):
    """Draw the button to open the tinker panel"""
    font = p.font.SysFont(None, 22)
    p.draw.rect(screen, TINKER_BUTTON_COLOR, tinker_button_rect)
    text = font.render("Tinker Panel", True, TEXT_COLOR_WHITE)
    text_rect = text.get_rect(center=tinker_button_rect.center)
    screen.blit(text, text_rect)

def open_tinker_panel(board):
    """Open the tinker panel to configure drawbacks and AI settings"""
    global WHITE_AI, BLACK_AI, flipped, AI_DEPTH, time_limit, search_in_progress  # Add search_in_progress
    
    # Store current search state to restore after panel closes
    was_searching = search_in_progress
    ai_turn_before = (WHITE_AI and board.turn == chess.WHITE) or (BLACK_AI and board.turn == chess.BLACK)
    
    # Stop AI search while in tinker panel to prevent lag
    if search_in_progress:
        print("Pausing AI search while tinker panel is open...")
        reset_search()  # Stop any ongoing AI search
        search_in_progress = False
    
    if HAS_TINKER_PANEL:
        try:
            ai_settings = {"WHITE_AI": WHITE_AI, "BLACK_AI": BLACK_AI, "AI_DEPTH": AI_DEPTH, "TIME_LIMIT": time_limit}  # Add time_limit
            print("Opening Tinker Panel...")
            tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
            result = tinker_panel.run()
            
            if result:
                white_drawback, black_drawback, updated_ai_settings, options = result
                # Update AI settings
                WHITE_AI = updated_ai_settings["WHITE_AI"]
                BLACK_AI = updated_ai_settings["BLACK_AI"]
                AI_DEPTH = updated_ai_settings.get("AI_DEPTH", AI_DEPTH)
                time_limit = updated_ai_settings.get("TIME_LIMIT", time_limit)  # Update time_limit
                print(f"Updated AI settings - Depth: {AI_DEPTH}, Time limit: {time_limit}s")
                
                # Update drawbacks on the board
                board.set_white_drawback(white_drawback)
                board.set_black_drawback(black_drawback)
                
                # Only flip if the option changed
                old_flipped = flipped
                if options.get("FLIP_BOARD", False):
                    flipped = not old_flipped
                    print(f"Board flipped: {old_flipped} -> {flipped}")
                
                print("Tinker Panel settings applied successfully")
            else:
                print("Tinker Panel closed without changes")
                
            # Restore main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
            
            # Clear all events that built up while panel was open
            p.event.clear()
            
            # Resume AI search if it was active before and it's still AI's turn
            current_ai_turn = (WHITE_AI and board.turn == chess.WHITE) or (BLACK_AI and board.turn == chess.BLACK)
            if was_searching and current_ai_turn:
                print("Resuming AI search after tinker panel closed...")
                # Set cooldown to allow the main loop to resume properly
                ai_move_cooldown = 5
                
        except Exception as e:
            print(f"Error in Tinker Panel: {e}")
            import traceback
            traceback.print_exc()
            # Make sure we restore the main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
    else:
        print("Tinker Panel not available - see above errors for details.")
        
    # Ensure pygame is properly initialized after returning
    p.display.update()

def display_ai_status(screen, board):
    """Display the AI status (which player is AI-controlled and thinking progress)"""
    if not HAS_AI:
        return
        
    font = p.font.SysFont(None, 20)
    player_color = "White" if board.turn == chess.WHITE else "Black"
    drawback = board.get_active_drawback(board.turn) or "None"
    
    status_text = f"{player_color} AI ({drawback.replace('_',' ').title()})"
    status_surf = font.render(status_text, True, TEXT_COLOR_WHITE, STATUS_BG_COLOR)
    thinking_surf = font.render(get_progress(), True, TEXT_COLOR_WHITE, STATUS_BG_COLOR)
    
    status_rect = status_surf.get_rect(topright=(WIDTH-10, 40))
    thinking_rect = thinking_surf.get_rect(topright=(WIDTH-10, 65))
    
    screen.blit(status_surf, status_rect)
    screen.blit(thinking_surf, thinking_rect)

def handle_ai_turn(board):
    """
    Non-blocking AI turn handler that starts a search if needed,
    or applies the move if search is complete
    """
    global game_over, winner_color, ai_move_cooldown, search_in_progress
    
    if not HAS_AI or game_over or board.is_variant_end():
        return
    
    # If AI's turn and no search is in progress, start one
    if not search_in_progress:
        # Add additional debugging for drawbacks
        active_drawback = board.get_active_drawback(board.turn)
        if active_drawback:
            print(f"AI turn with active drawback: {active_drawback}")
            # Verify legal moves with this drawback
            legal_moves = list(board.legal_moves)
            print(f"Legal moves with '{active_drawback}' drawback: {len(legal_moves)}")
            
            # Check the first few legal moves to verify they're correct
            if legal_moves:
                print("Sample legal moves:")
                for i, move in enumerate(legal_moves[:5]):
                    print(f"  {i+1}. {move.uci()}")
            else:
                print("No legal moves available with this drawback - ending game")
                game_over = True
                winner_color = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                return
        
        print(f"Starting AI search for turn {board.turn} at depth {AI_DEPTH} with time limit {time_limit}s")
        print(f"Active drawback: {board.get_active_drawback(board.turn)}")
        # Print number of legal moves for debugging
        legal_move_count = len(list(board.legal_moves))
        print(f"Number of legal moves: {legal_move_count}")
        
        start_search(board, AI_DEPTH, time_limit)  # Pass time_limit here
        search_in_progress = True
        return
    
    # If a search is already in progress, check if it's done
    if is_search_complete():
        print("Search is complete, retrieving result...")
        move = get_result()
        print(f"AI selected move: {move}")
        
        # Explicitly reset search state BEFORE applying the move
        # to avoid potential state corruption
        search_in_progress = False
        reset_search()
        
        if move is None:
            print("AI returned None for move - searching for fallback move")
            # No good move found, pick a random legal move
            legal_moves = list(board.legal_moves)
            if legal_moves:
                move = random.choice(legal_moves)
                print(f"Using fallback random move: {move}")
            else:
                # No legal moves available
                game_over = True
                winner_color = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                print("No legal moves available for AI; ending game.")
                return
        
        # Apply the selected move
        if move:
            # Check if move is legal and why it might not be
            legal_moves = list(board.legal_moves)
            is_legal = move in legal_moves
            print(f"Move {move} is {'legal' if is_legal else 'ILLEGAL'}!")
            print(f"Number of legal moves: {len(legal_moves)}")
            
            if is_legal:
                print(f"Applying AI move: {move}")
                board.push(move)
                print(f"AI moved: {move}")
                print("Board FEN after AI move:", board.fen())
                
                if not list(board.legal_moves):
                    game_over = True
                    winner_color = board.turn
                    print("No legal moves available for opponent; ending game.")
                
                if board.is_variant_end():
                    game_over = True
                    winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                    print(f"Game over! {'White' if winner_color == chess.WHITE else 'Black'} wins!")
                
                ai_move_cooldown = FPS // 2
            else:
                # Move is not legal - debug why
                print(f"AI ERROR: Move {move} is not legal!")
                
                # Check active drawback
                active_drawback = board.get_active_drawback(board.turn)
                print(f"Active drawback: {active_drawback}")
                
                # Get a sample of actually legal moves
                legal_moves = list(board.legal_moves)
                print(f"There are {len(legal_moves)} legal moves. Examples:")
                for i, legal_move in enumerate(legal_moves[:5]):
                    print(f"  {i+1}. {legal_move.uci()}")
                
                # Test the drawback function directly
                try:
                    # Get the drawback function
                    from GameState.drawback_manager import get_drawback_function
                    
                    if active_drawback:
                        check_func = get_drawback_function(active_drawback)
                        
                        # Print function signature to debug parameter order
                        import inspect
                        sig = inspect.signature(check_func)
                        print(f"Drawback function signature: {sig}")
                        
                        # Test with both parameter orders to diagnose the issue
                        test1 = check_func(board, move, board.turn)
                        test2 = check_func(board, board.turn, move)
                        print(f"Function returns: {test1} with (board, move, color)")
                        print(f"Function returns: {test2} with (board, color, move)")
                    
                except Exception as e:
                    import traceback
                    print(f"Error analyzing drawback: {e}")
                    traceback.print_exc()
                
                # Fall back to random move
                if legal_moves:
                    move = random.choice(legal_moves)
                    print(f"Selecting random fallback move: {move}")
                    board.push(move)
                
        else:
            print("AI move invalid.")
        
        # Reset search state for next turn
        search_in_progress = False
        reset_search()
    else:
        # Print a status update occasionally to confirm search is still active
        if random.random() < 0.05:  # ~5% chance each frame to avoid spamming
            progress = get_progress()
            print(f"AI is still thinking: {progress}")

def undo_last_move(board):
    """Safely undo the last move on the board and update game state"""
    global game_over, winner_color, search_in_progress
    
    # Check if there are moves to undo
    if len(board.move_stack) > 0:
        try:
            # Cancel any ongoing AI search
            if search_in_progress:
                print("Cancelling AI search due to move undo")
                reset_search()
                search_in_progress = False
            
            # Pop the last move
            board.pop()
            print(f"Move undone. New position: {board.fen()}")
            
            # Reset game state if the game was over
            if game_over:
                game_over = False
                winner_color = None
                print("Game state reset after undoing move.")
                
            return True
        except Exception as e:
            print(f"Error undoing move: {e}")
            return False
    else:
        print("No moves to undo.")
        return False

async def async_main():
    """Main game loop using asyncio for better performance"""
    global game_over, winner_color, WHITE_AI, BLACK_AI, flipped, ai_move_cooldown, search_in_progress
    
    # Initialize pygame
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")  # Fixed: setCaption -> set_caption
    
    # Load images for pieces at the beginning
    square_size = BOARD_HEIGHT // DIMENSION
    IMAGES = load_images(square_size)
    
    # Initialize game state
    ai_move_cooldown = 0
    board = DrawbackBoard()
    board.reset()
    running = True
    flipped = False
    selected_square = None
    game_over = False
    winner_color = None
    search_in_progress = False

    while running:
        # Process pygame events and update game state
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False
                
            elif event.type == p.MOUSEBUTTONDOWN:
                # Handle mouse clicks
                x, y = event.pos
                
                # Check if tinker button was clicked
                if tinker_button_rect.collidepoint(x, y):
                    open_tinker_panel(board)
                    continue
                
                # Handle board clicks (if not game over and not AI's turn)
                if not game_over and not ((WHITE_AI and board.turn == chess.WHITE) or 
                                         (BLACK_AI and board.turn == chess.BLACK)):
                    # Convert screen coordinates to board position
                    board_x = x - BOARD_X_OFFSET
                    board_y = y - BOARD_Y_OFFSET
                    
                    # Check if click is within board boundaries
                    if 0 <= board_y < BOARD_HEIGHT and 0 <= board_x < BOARD_HEIGHT:
                        # Calculate square indices
                        row, col = board_y // SQ_SIZE, board_x // SQ_SIZE
                        board_row, board_col = (row, 7 - col) if flipped else (7 - row, col)
                        clicked_square = chess.square(board_col, board_row)
                        
                        # First click: select a piece
                        if selected_square is None:
                            piece = board.piece_at(clicked_square)
                            if piece and piece.color == board.turn:
                                selected_square = clicked_square
                                print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                                
                        # Second click: move the selected piece
                        else:
                            # Check for pawn promotion
                            pawn = board.piece_at(selected_square)
                            if pawn and pawn.piece_type == chess.PAWN and (
                                (pawn.color == chess.WHITE and chess.square_rank(clicked_square) == 7) or
                                (pawn.color == chess.BLACK and chess.square_rank(clicked_square) == 0)
                            ):
                                import promotion_panel
                                promo = promotion_panel.run()
                                move_obj = chess.Move(selected_square, clicked_square, promotion=promo)
                            else:
                                move_obj = chess.Move(selected_square, clicked_square)
                            
                            # Try to make the move
                            if board.is_legal(move_obj):
                                board.push(move_obj)
                                print(f"Human moved: {move_obj}")
                                selected_square = None
                                
                                # Check if game is over
                                if board.is_variant_end():
                                    winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                                    game_over = True
                            else:
                                # If illegal move, check if clicking a new piece
                                piece = board.piece_at(clicked_square)
                                if piece and piece.color == board.turn:
                                    selected_square = clicked_square
                                    print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                                else:
                                    print(f"Illegal move: {chess.square_name(selected_square)} to {chess.square_name(clicked_square)}")
                                    selected_square = None
                                    
            elif event.type == p.KEYDOWN:
                # Handle key presses
                if event.key == p.K_r:
                    # Restart game with 'R' key
                    board = DrawbackBoard()
                    board.reset()
                    selected_square = None
                    game_over = False
                    winner_color = None
                    search_in_progress = False
                    print("Game restarted!")
                    
                elif event.key == p.K_t:
                    # Open tinker panel with 'T' key
                    open_tinker_panel(board)
                
                elif event.key == p.K_z:
                    # Undo last move with 'Z' key
                    if undo_last_move(board):
                        selected_square = None  # Reset selection after undoing
                        # If AI is now supposed to move, give it a moment to reset
                        if ((WHITE_AI and board.turn == chess.WHITE) or 
                            (BLACK_AI and board.turn == chess.BLACK)):
                            # Small delay to ensure clean reset before new AI search
                            ai_move_cooldown = FPS // 4  # 1/4 second cooldown
                    
        # Handle AI turn - non-blocking approach
        if not game_over and ai_move_cooldown <= 0:
            if (BLACK_AI and board.turn == chess.BLACK) or (WHITE_AI and board.turn == chess.WHITE):
                handle_ai_turn(board)
        else:
            # Decrement cooldown timer if it's active
            if ai_move_cooldown > 0:
                ai_move_cooldown -= 1
                    
        # Draw everything
        screen.fill(TEXT_COLOR_BLACK)  # Clear screen with black background
        
        # Draw board and pieces
        draw_board(screen, DIMENSION, BOARD_HEIGHT, BOARD_HEIGHT, flipped, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        draw_pieces(screen, board, flipped, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        
        # Draw UI elements
        display_drawbacks(screen, board, flipped)
        display_current_turn(screen, board)
        draw_tinker_button(screen)
        display_ai_status(screen, board)
        
        # Highlight selected square and show legal moves
        if selected_square is not None:
            square_size = BOARD_HEIGHT // DIMENSION
            r = chess.square_rank(selected_square)
            c = chess.square_file(selected_square)
            draw_row, draw_col = (r, 7 - c) if flipped else (7 - r, c)
            
            # Create highlight surface
            highlight = p.Surface((square_size, square_size), p.SRCALPHA)
            highlight.fill(HIGHLIGHT_COLOR)
            screen.blit(highlight, (BOARD_X_OFFSET + draw_col * square_size, 
                                  BOARD_Y_OFFSET + draw_row * square_size))
                                  
            # Draw indicators for legal moves
            draw_legal_move_indicators(screen, board, selected_square, flipped, 
                                     DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
                                     
        # Display winner message if game is over
        if game_over and winner_color is not None:
            display_winner(screen, winner_color)
            
        # Update display and control frame rate    
        clock.tick(FPS)
        p.display.flip()
        
        # Give more time for background tasks
        await asyncio.sleep(0.01)
    
    # Quit pygame when done
    p.quit()

if __name__ == "__main__":
    asyncio.run(async_main())