"""
Drawback Chess - Main Game Module
A chess variant where each player has a drawback (rule restriction)
"""
import pygame as p
import chess
import random
import asyncio
import time

# Import utilities and board drawing functions
from utils import load_images, draw_board, draw_pieces, draw_legal_move_indicators
from utils import WIDTH, HEIGHT, BOARD_HEIGHT, BOARD_Y_OFFSET, BOARD_X_OFFSET, DIMENSION, SQ_SIZE

# Import game logic
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS as AVAILABLE_DRAWBACKS
from GameState.drawback_manager import get_drawback_loss_function

# Import global settings
from Globals import (
    FPS, AI_DEPTH, WHITE_AI, BLACK_AI, DRAWBACKS, TIME_LIMIT,
    GAME_OVER, WINNER_COLOR, FLIPPED_BOARD, AI_MOVE_COOLDOWN, SEARCH_IN_PROGRESS,
    TINKER_BUTTON_WIDTH, TINKER_BUTTON_HEIGHT, TINKER_BUTTON_TOP, TINKER_BUTTON_COLOR,
    TEXT_COLOR_WHITE, TEXT_COLOR_BLACK, HIGHLIGHT_COLOR, GOLD_COLOR, STATUS_BG_COLOR
)

# Add smart time management setting (default to False)
USE_SMART_TIME_MANAGEMENT = True

# Use the enhanced async engine
from AI.enhanced_async_engine import (
    start_search, get_result, is_search_complete, 
    reset_search, get_progress, engine_state
)

# Import engine core utilities for position analysis and drawback checking
from AI.engine_core import analyze_position, check_drawback_loss_conditions

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

# Flag indicating AI is available
HAS_AI = True

# Global state variables
game_over = GAME_OVER
winner_color = WINNER_COLOR
flipped = FLIPPED_BOARD
ai_move_cooldown = AI_MOVE_COOLDOWN
search_in_progress = SEARCH_IN_PROGRESS
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
    global WHITE_AI, BLACK_AI, flipped, AI_DEPTH, TIME_LIMIT, search_in_progress, ai_move_cooldown, USE_SMART_TIME_MANAGEMENT
    
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
            ai_settings = {
                "WHITE_AI": WHITE_AI, 
                "BLACK_AI": BLACK_AI, 
                "AI_DEPTH": AI_DEPTH, 
                "TIME_LIMIT": TIME_LIMIT,
                "SMART_TIME_MANAGEMENT": USE_SMART_TIME_MANAGEMENT
            }
            print("Opening Tinker Panel...")
            tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
            result = tinker_panel.run()
            
            if result:
                white_drawback, black_drawback, updated_ai_settings, options = result
                # Update AI settings
                WHITE_AI = updated_ai_settings["WHITE_AI"]
                BLACK_AI = updated_ai_settings["BLACK_AI"]
                AI_DEPTH = updated_ai_settings.get("AI_DEPTH", AI_DEPTH)
                TIME_LIMIT = updated_ai_settings.get("TIME_LIMIT", TIME_LIMIT)
                USE_SMART_TIME_MANAGEMENT = updated_ai_settings.get("SMART_TIME_MANAGEMENT", USE_SMART_TIME_MANAGEMENT)
                print(f"Updated AI settings - Depth: {AI_DEPTH}, Time limit: {TIME_LIMIT}s, Smart Time Management: {USE_SMART_TIME_MANAGEMENT}")
                
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
            
            # Completely reset AI search state - don't resume old search
            reset_search()
            search_in_progress = False
            
            # Check if it's AI's turn after closing the panel
            current_ai_turn = (WHITE_AI and board.turn == chess.WHITE) or (BLACK_AI and board.turn == chess.BLACK)
            if current_ai_turn:
                print("Starting fresh AI search after tinker panel closed...")
                # Force a short delay before starting new search to avoid UI freeze
                ai_move_cooldown = 2  # Set a short cooldown to let the UI refresh
            
        except Exception as e:
            print(f"Error in Tinker Panel: {e}")
            import traceback
            traceback.print_exc()
            # Make sure we restore the main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
            # Reset search state in case of error
            reset_search()
            search_in_progress = False
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

def check_game_end_conditions(board):
    """
    Check if the game has ended due to a variety of conditions:
    - King capture
    - Drawback loss condition
    - No legal moves
    
    Returns:
        tuple: (game_over, winner_color, message)
    """
    # Check if a king has been captured (standard variant end)
    white_king_alive = False
    black_king_alive = False
    
    for square, piece in board.piece_map().items():
        if piece.piece_type == chess.KING:
            if piece.color == chess.WHITE:
                white_king_alive = True
            else:
                black_king_alive = True
                
            # Early exit if both kings found
            if white_king_alive and black_king_alive:
                break
    
    # Handle king capture
    if not white_king_alive:
        return True, chess.BLACK, "White's king was captured"
        
    if not black_king_alive:
        return True, chess.WHITE, "Black's king was captured"
    
    # Check for drawback-specific loss conditions (like atomic bomb)
    has_loss, losing_color, reason = check_drawback_loss_conditions(board)
    if has_loss:
        return True, chess.WHITE if losing_color == chess.BLACK else chess.BLACK, reason
    
    # Check for no legal moves
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return True, chess.WHITE if board.turn == chess.BLACK else chess.BLACK, f"No legal moves for {'Black' if board.turn == chess.BLACK else 'White'}"
    
    # Game not over
    return False, None, None

def handle_ai_turn(board):
    """Handle the AI's turn to move, using the configured engine"""
    global game_over, winner_color, search_in_progress
    
    # Only proceed if this is AI's turn and not already searching
    if search_in_progress:
        return
    
    # Get side to move and active drawback, if any
    side_to_move = "White" if board.turn == chess.WHITE else "Black"
    active_drawback = board.get_active_drawback(board.turn)
    
    # Display what drawback is active, if any
    if active_drawback:
        print(f"AI turn with active drawback: {active_drawback}")
        
        # Show some sample legal moves to help with debugging
        legal_moves = list(board.legal_moves)
        print(f"Legal moves with '{active_drawback}' drawback: {len(legal_moves)}")
        if legal_moves:
            print("Sample legal moves:")
            for i, move in enumerate(legal_moves[:5]):
                print(f"  {i+1}. {move}")
    else:
        print(f"AI turn with no drawback restrictions")
        print(f"Legal moves: {len(list(board.legal_moves))}")
    
    # Get depth and time limit from settings
    from Globals import AI_DEPTH, TIME_LIMIT
    depth = AI_DEPTH
    time_limit = TIME_LIMIT
    smart_time_management = USE_SMART_TIME_MANAGEMENT
    
    # Initialize engine
    from AI.enhanced_async_engine import engine_state, start_search, reset_search, get_result
    
    # Store the last seen best move for timeout recovery
    last_seen_best_move = None
    try:
        from AI.drawback_Bot import current_best_move
        if current_best_move:
            last_seen_best_move = current_best_move.uci()
    except (ImportError, AttributeError):
        pass
    
    print(f"Starting AI search for {side_to_move} at depth {depth} with time limit {time_limit}s")
    
    # Ensure the engine state has the current board
    engine_state.board = board
    engine_state.depth = depth
    engine_state.time_limit = time_limit
    
    # Set search in progress flag
    search_in_progress = True
    
    # Start search
    search_started = start_search(board, depth, time_limit, smart_time_management)
    
    if not search_started:
        print("Failed to start search")
        search_in_progress = False
        return
    
    # Wait a short time for search to initialize
    import asyncio
    yield from asyncio.sleep(0.1)
    
    # Get result if available
    result = get_result()
    
    # If result already available, process it
    if result:
        search_in_progress = False
        
        # Apply the move
        try:
            # Get the move from the result
            move = None
            if isinstance(result, dict) and 'move' in result:
                # Result is a dictionary with a 'move' key (from newer async engine)
                move_uci = result['move']
                if move_uci:
                    # Convert UCI string to Move object
                    for legal_move in board.legal_moves:
                        if legal_move.uci() == move_uci:
                            move = legal_move
                            break
            else:
                # Result is directly a Move object (from older engine versions)
                move = result
            
            # If no move found, try to pick the first legal move as fallback
            if not move:
                # Try to use the last seen best move if available
                if last_seen_best_move:
                    for legal_move in board.legal_moves:
                        if legal_move.uci() == last_seen_best_move:
                            move = legal_move
                            print(f"Using last seen best move: {move}")
                            break
                
                # If still no move, fall back to first legal move
                if not move:
                    legal_moves = list(board.legal_moves)
                    if legal_moves:
                        move = legal_moves[0]
                        print(f"Selected fallback move: {move}")
                    else:
                        print("No legal moves available - game should be over")
                        game_over = True
                        winner_color = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                        return
            
            # Apply the chosen move
            try:
                board.push(move)
                print(f"Move applied: {move}")
                
                # Check for game end conditions AFTER the move is applied
                game_over, winner_color, end_message = check_game_end_conditions(board)
                if game_over:
                    print(f"Game over after AI move: {end_message}")
                    return
                    
                # Set cooldown to prevent AI from moving again immediately
                ai_move_cooldown = AI_MOVE_COOLDOWN
            except Exception as e:
                print(f"Error applying move: {str(e)}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"Error processing AI move: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        # Check if search has been running too long and force completion
        from AI.enhanced_async_engine import engine_state
        if engine_state.start_time is not None:
            current_time = time.time()
            elapsed_time = current_time - engine_state.start_time
            search_time_limit = max(0.5, TIME_LIMIT)
            
            # If we've exceeded the time limit, force completion
            if elapsed_time > search_time_limit * 1.5:  # Give a 50% buffer to be safe
                print(f"Search exceeded time limit ({elapsed_time:.1f}s > {search_time_limit}s), forcing completion...")
                
                # Check if we have a current best move before timing out
                current_timeout_best_move = None
                try:
                    from AI.drawback_Bot import current_best_move
                    if current_best_move:
                        current_timeout_best_move = current_best_move.uci()
                        print(f"Current best move at timeout: {current_timeout_best_move}")
                except (ImportError, AttributeError):
                    pass
                
                # Get whatever move we have so far
                move = get_result()
                
                # If no move available, try to use the last known best move
                if move is None or (isinstance(move, dict) and move.get('move') is None):
                    if current_timeout_best_move:
                        # Found a current best move at timeout, use it
                        for legal_move in board.legal_moves:
                            if legal_move.uci() == current_timeout_best_move:
                                move = {'move': current_timeout_best_move, 'time': elapsed_time, 'note': 'timeout_recovery'}
                                print(f"Using current best move at timeout: {current_timeout_best_move}")
                                break
                    elif last_seen_best_move:
                        # Try using the last seen best move
                        for legal_move in board.legal_moves:
                            if legal_move.uci() == last_seen_best_move:
                                move = {'move': last_seen_best_move, 'time': elapsed_time, 'note': 'timeout_recovery_last_seen'}
                                print(f"Using last seen best move for timeout: {last_seen_best_move}")
                                break
                    
                    # If still no move, fall back to first legal move
                    if move is None or (isinstance(move, dict) and move.get('move') is None):
                        legal_moves = list(board.legal_moves)
                        if legal_moves:
                            fallback_move = legal_moves[0]
                            move = {'move': fallback_move.uci(), 'time': elapsed_time, 'note': 'fallback'}
                            print(f"No move from search, selected first legal move: {fallback_move}")
                        else:
                            print("No legal moves available - game should be over")
                            game_over = True
                            winner_color = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                            search_in_progress = False
                            reset_search()
                            return
                
                # Reset search state
                search_in_progress = False
                reset_search()
                
                # Apply the move
                try:
                    # Process the move based on its format
                    move_obj = None
                    
                    if isinstance(move, dict) and 'move' in move:
                        # Convert UCI string to Move object
                        move_uci = move['move']
                        if move_uci:
                            # Find the matching legal move
                            for legal_move in board.legal_moves:
                                if legal_move.uci() == move_uci:
                                    move_obj = legal_move
                                    break
                            if not move_obj:
                                print(f"Warning: Could not find legal move matching {move_uci}")
                                
                    elif isinstance(move, dict) and 'error' in move and move['error'] == 'timeout':
                        # Handle timeout error - try to use last known best move from drawback_Bot
                        if current_timeout_best_move:
                            # Find the matching legal move
                            for legal_move in board.legal_moves:
                                if legal_move.uci() == current_timeout_best_move:
                                    move_obj = legal_move
                                    break
                            if move_obj:
                                print(f"Using best move at timeout: {move_obj}")
                        elif last_seen_best_move:
                            # Try the last seen best move as fallback
                            for legal_move in board.legal_moves:
                                if legal_move.uci() == last_seen_best_move:
                                    move_obj = legal_move
                                    break
                            if move_obj:
                                print(f"Using last seen best move after timeout: {move_obj}")
                    else:
                        # Move is already a Move object
                        move_obj = move
                    
                    # If we still don't have a move, use first legal move
                    if not move_obj:
                        legal_moves = list(board.legal_moves)
                        if legal_moves:
                            move_obj = legal_moves[0]
                            print(f"Using fallback first legal move: {move_obj}")
                        else:
                            print("No legal moves available - game should be over")
                            game_over = True
                            winner_color = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                            return
                    
                    # Now apply the move
                    board.push(move_obj)
                    print(f"Move applied after timeout: {move_obj}")
                    
                    # Check for game end conditions
                    game_over, winner_color, end_message = check_game_end_conditions(board)
                    if game_over:
                        print(f"Game over after AI move: {end_message}")
                        return
                        
                    # Set cooldown
                    ai_move_cooldown = AI_MOVE_COOLDOWN
                except Exception as e:
                    print(f"Error applying move: {str(e)}")
                    import traceback
                    traceback.print_exc()

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
                                
                                # Check for game end conditions AFTER the move is applied
                                game_over, winner_color, end_message = check_game_end_conditions(board)
                                if game_over:
                                    print(f"Game over after human move: {end_message}")
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
                    
                    # Cancel any running search and clear search knowledge
                    reset_search()
                    engine_state.clear_search_knowledge()
                    print("Game restarted and search knowledge cleared!")
                    
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