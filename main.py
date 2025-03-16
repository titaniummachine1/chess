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

# Import constants
from GameState.constants import (
    FPS, TINKER_BUTTON_WIDTH, TINKER_BUTTON_HEIGHT, TINKER_BUTTON_TOP, TINKER_BUTTON_COLOR,
    TEXT_COLOR_WHITE, TEXT_COLOR_BLACK, HIGHLIGHT_COLOR, GOLD_COLOR, STATUS_BG_COLOR,
    endgame_Fen, middlegame_Fen, capture_test_Fen, complex_Fen, kings_adjacent_Fen, 
    atomic_bomb_test_Fen, INITIAL_FEN
)

# Import the centralized state manager
from GameState.state_manager import game_state_manager

# Import configuration system
import config

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

# Create local references to frequently accessed state
game_state = game_state_manager.state

# Button rect for the tinker panel
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

def display_winner(screen, winner_color, message=None):
    """
    Display the game over message with the winner or draw status.
    
    Args:
        screen: The pygame screen to draw on
        winner_color: The color of the winner (WHITE, BLACK, or None for draw)
        message: Optional message explaining the win/draw condition
    """
    font = p.font.Font(None, 50)
    
    if winner_color is None:
        # It's a draw
        text = f"Game Drawn! {message or ''} Press 'R' to restart."
        bg_color = STATUS_BG_COLOR
    else:
        # Someone won
        text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins! "
        if message:
            text += message
        else:
            text += "King was captured!"
        text += " Press 'R' to restart."
        bg_color = GOLD_COLOR
        
    text_surf = font.render(text, True, TEXT_COLOR_BLACK, bg_color)
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
    # Use the game state manager for state updates
    state = game_state_manager.state
    
    # Store current search state to restore after panel closes
    was_searching = state.search_in_progress
    ai_turn_before = state.is_ai_turn(board)
    
    # Stop AI search while in tinker panel to prevent lag
    if state.search_in_progress:
        print("Pausing AI search while tinker panel is open...")
        reset_search()  # Stop any ongoing AI search
        game_state_manager.update(search_in_progress=False)
    
    if HAS_TINKER_PANEL:
        try:
            ai_settings = {
                "WHITE_AI": state.white_ai, 
                "BLACK_AI": state.black_ai, 
                "AI_DEPTH": state.ai_depth, 
                "TIME_LIMIT": state.time_limit,
                "SMART_TIME_MANAGEMENT": state.use_smart_time_management
            }
            print("Opening Tinker Panel...")
            tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
            result = tinker_panel.run()
            
            if result:
                white_drawback, black_drawback, updated_ai_settings, options = result
                
                # Check if AI settings actually changed
                ai_changed = (
                    updated_ai_settings["WHITE_AI"] != state.white_ai or 
                    updated_ai_settings["BLACK_AI"] != state.black_ai or
                    updated_ai_settings.get("AI_DEPTH", state.ai_depth) != state.ai_depth or
                    updated_ai_settings.get("TIME_LIMIT", state.time_limit) != state.time_limit or
                    updated_ai_settings.get("SMART_TIME_MANAGEMENT", state.use_smart_time_management) != state.use_smart_time_management
                )
                
                # Check if drawbacks changed
                drawbacks_changed = (
                    white_drawback != board.get_active_drawback(chess.WHITE) or
                    black_drawback != board.get_active_drawback(chess.BLACK)
                )
                
                # Update state with new AI settings
                game_state_manager.update(
                    white_ai=updated_ai_settings["WHITE_AI"],
                    black_ai=updated_ai_settings["BLACK_AI"],
                    ai_depth=updated_ai_settings.get("AI_DEPTH", state.ai_depth),
                    time_limit=updated_ai_settings.get("TIME_LIMIT", state.time_limit),
                    use_smart_time_management=updated_ai_settings.get("SMART_TIME_MANAGEMENT", state.use_smart_time_management)
                )
                
                print(f"Updated AI settings - Depth: {state.ai_depth}, Time limit: {state.time_limit}s, Smart Time Management: {state.use_smart_time_management}")
                
                # Update drawbacks on the board
                board.set_white_drawback(white_drawback)
                board.set_black_drawback(black_drawback)
                
                # Only flip if the option changed
                old_flipped = state.flipped_board
                board_flipped = options.get("FLIP_BOARD", False)
                if board_flipped:
                    game_state_manager.update(flipped_board=not old_flipped)
                    print(f"Board flipped: {old_flipped} -> {state.flipped_board}")
                
                # Save settings to config file
                current_position = board.fen()
                ui_settings = {"flip_board": state.flipped_board}
                
                # Convert settings to lower case for config file
                ai_config = {
                    "white_ai": state.white_ai,
                    "black_ai": state.black_ai,
                    "depth": state.ai_depth,
                    "time_limit": state.time_limit,
                    "smart_time_management": state.use_smart_time_management
                }
                
                config.save_current_settings(
                    current_position, 
                    white_drawback, 
                    black_drawback, 
                    ai_config, 
                    ui_settings
                )
                
                # Clear AI search knowledge if AI settings or drawbacks changed
                if ai_changed or drawbacks_changed or board_flipped:
                    from AI.enhanced_async_engine import engine_state
                    reset_search()
                    engine_state.clear_search_knowledge()
                    print("AI settings or drawbacks changed - cleared search knowledge for fresh evaluation!")
                
                print("Tinker Panel settings applied successfully and saved to config")
            else:
                print("Tinker Panel closed without changes")
                
            # Restore main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
            
            # Clear all events that built up while panel was open
            p.event.clear()
            
            # Completely reset AI search state - don't resume old search
            reset_search()
            game_state_manager.update(search_in_progress=False)
            
            # Check if it's AI's turn after closing the panel
            if state.is_ai_turn(board):
                print("Starting fresh AI search after tinker panel closed...")
                # Force a short delay before starting new search to avoid UI freeze
                game_state_manager.update(ai_move_cooldown=2)  # Set a short cooldown to let the UI refresh
                
        except Exception as e:
            print(f"Error in Tinker Panel: {e}")
            import traceback
            traceback.print_exc()
            # Make sure we restore the main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
            # Reset search state in case of error
            reset_search()
            game_state_manager.update(search_in_progress=False)
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
    - 3-fold repetition (draw)
    - Insufficient material (draw)
    
    Returns:
        tuple: (game_over, winner_color, message)
    """
    end_message = None
    
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
        end_message = "White's king was captured"
        return True, chess.BLACK, end_message
        
    if not black_king_alive:
        end_message = "Black's king was captured"
        return True, chess.WHITE, end_message
    
    # Check for drawback-specific loss conditions (like atomic bomb)
    has_loss, losing_color, reason = check_drawback_loss_conditions(board)
    if has_loss:
        # Special verification for atomic bomb drawback
        # This is a safety check in addition to the checks already in check_drawback_loss_conditions
        active_drawback = board.get_active_drawback(losing_color) if losing_color is not None else None
        if active_drawback == "atomic_bomb":
            # Triple-check that the conditions are actually met:
            # 1. It's the losing player's turn (opponent just moved)
            if board.turn != losing_color:
                print("MAIN SAFETY CHECK: Atomic bomb false positive - Not the losing player's turn")
                return False, None, None
                
            # 2. There was at least one move
            if len(board.move_stack) == 0:
                print("MAIN SAFETY CHECK: Atomic bomb false positive - No moves in the stack")
                return False, None, None
                
            # 3. The last move was definitely a capture
            last_move = board.move_stack[-1]
            was_capture = False
            
            # Try different methods to determine if it was a capture
            if hasattr(board, 'is_capture'):
                was_capture = board.is_capture(last_move)
            elif hasattr(board, '_lastmove_was_capture'):
                was_capture = board._lastmove_was_capture
            elif last_move.to_square == board.ep_square:
                was_capture = True  # En passant is always a capture
            else:
                # If we can't verify, we'll trust the drawback's determination
                was_capture = True  
                
            if not was_capture:
                print(f"MAIN SAFETY CHECK: Atomic bomb false positive - Last move {last_move} was not a capture")
                return False, None, None
                
            # Log the successful atomic bomb trigger for debugging
            print(f"MAIN: Atomic bomb successfully triggered. {losing_color} player lost because a piece was captured next to their king.")
            print(f"MAIN: The final move that triggered the loss was: {last_move}")
        
        end_message = reason
        return True, chess.WHITE if losing_color == chess.BLACK else chess.BLACK, end_message
    
    # Check for no legal moves
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        end_message = f"No legal moves for {'Black' if board.turn == chess.BLACK else 'White'}"
        return True, chess.WHITE if board.turn == chess.BLACK else chess.BLACK, end_message
    
    # Check for draw by 3-fold repetition
    if board.is_threefold_repetition():
        end_message = "Draw by 3-fold repetition"
        return True, None, end_message
    
    # Check for draw by insufficient material
    if board.has_insufficient_material():
        end_message = "Draw by insufficient material"
        return True, None, end_message
    
    # Game not over
    return False, None, None

def handle_ai_turn(board):
    """Handle the AI's turn to move, using the configured engine"""
    state = game_state_manager.state
    
    # Only proceed if this is AI's turn and not already searching
    if state.search_in_progress:
        return
    
    # Get side to move and active drawback, if any
    side_to_move = "White" if board.turn == chess.WHITE else "Black"
    active_drawback = board.get_active_drawback(board.turn)
    
    # Initialize engine
    from AI.enhanced_async_engine import engine_state, start_search, reset_search, get_result, is_search_complete
    
    # Always reset search knowledge completely between player turns
    # This ensures no inconsistent perspective evaluations between white and black
    reset_search()
    
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
    depth = state.ai_depth
    time_limit = state.time_limit
    smart_time_management = state.use_smart_time_management
    
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
    game_state_manager.update(search_in_progress=True)
    
    # Start search
    search_started = start_search(board, depth, time_limit, smart_time_management)
    
    if not search_started:
        print("Failed to start search")
        game_state_manager.update(search_in_progress=False)
        return
    
    # Wait a short time for search to initialize (use regular sleep since this isn't a coroutine)
    time.sleep(0.1)
    
    # Since this isn't a coroutine anymore, we need to actively wait for the search to complete
    # or time out. Let's check for a result now, and if none is available, we'll return and
    # let the main loop check again on subsequent iterations.
    result = get_result()
    
    # If a result is already available, process it immediately
    if result:
        process_search_result(board, result, last_seen_best_move)
    
    # Otherwise, let the main loop periodically check for completion
    return

def process_search_result(board, result, last_seen_best_move=None):
    """Process the search result and apply the move to the board"""
    # Update game state
    game_state_manager.update(search_in_progress=False)
    
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
                    game_state_manager.update(
                        game_over=True,
                        winner_color=chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                    )
                    return
        
        # Apply the chosen move
        try:
            board.push(move)
            print(f"Move applied: {move}")
            
            # Check for game end conditions AFTER the move is applied
            game_over, winner_color, end_message = check_game_end_conditions(board)
            if game_over:
                game_state_manager.update(
                    game_over=game_over,
                    winner_color=winner_color,
                    end_message=end_message
                )
                print(f"Game over after AI move: {end_message}")
                return
                
            # Set cooldown to prevent AI from moving again immediately
            game_state_manager.update(ai_move_cooldown=FPS // 3)  # 1/3 second cooldown
        except Exception as e:
            print(f"Error applying move: {str(e)}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"Error processing AI move: {str(e)}")
        import traceback
        traceback.print_exc()
        
    # Make sure search is fully reset
    reset_search()

def undo_last_move(board):
    """Safely undo the last move on the board and update game state"""
    # Check if there are moves to undo
    if len(board.move_stack) > 0:
        try:
            # Cancel any ongoing AI search
            if game_state_manager.state.search_in_progress:
                print("Cancelling AI search due to move undo")
                reset_search()
                game_state_manager.update(search_in_progress=False)
            
            # Pop the last move
            board.pop()
            print(f"Move undone. New position: {board.fen()}")
            
            # Reset game state if the game was over
            if game_state_manager.state.game_over:
                game_state_manager.update(
                    game_over=False,
                    winner_color=None,
                    end_message=None
                )
                print("Game state reset after undoing move.")
                
            return True
        except Exception as e:
            print(f"Error undoing move: {e}")
            return False
    else:
        print("No moves to undo.")
        return False

def select_position(position_name):
    """
    Select a predefined position by name
    
    Args:
        position_name: Name of the predefined position or a custom FEN string
        
    Returns:
        FEN string for the selected position
    """
    positions = {
        "initial": INITIAL_FEN,
        "endgame": endgame_Fen,
        "middlegame": middlegame_Fen,
        "capture_test": capture_test_Fen,
        "complex": complex_Fen,
        "kings_adjacent": kings_adjacent_Fen,
        "atomic_bomb_test": atomic_bomb_test_Fen,
    }
    
    # If the input is a position name, return the corresponding FEN
    if position_name in positions:
        return positions[position_name]
    
    # Otherwise, assume it's a custom FEN string
    return position_name

def setup_test_environment(board, position_name, white_drawback=None, black_drawback=None):
    """
    Set up a test environment with a selected position and drawbacks
    
    Args:
        board: The DrawbackBoard instance
        position_name: Name of the predefined position or a custom FEN string
        white_drawback: Drawback to set for white player (None for no drawback)
        black_drawback: Drawback to set for black player (None for no drawback)
    """
    # Import here to ensure it's available
    from GameState.movegen import DrawbackBoard
    
    # Get the selected FEN
    selected_fen = select_position(position_name)
    
    # Create a new board with the FEN and drawbacks
    # We need to create a new board rather than reset to avoid clearing drawbacks
    new_board = DrawbackBoard(selected_fen, white_drawback, black_drawback)
    
    # Copy the state to the provided board
    board.clear()
    board.set_board_fen(new_board.board_fen())
    board.turn = new_board.turn
    board.castling_rights = new_board.castling_rights
    board.ep_square = new_board.ep_square
    board.halfmove_clock = new_board.halfmove_clock
    board.fullmove_number = new_board.fullmove_number
    
    # Set drawbacks manually to ensure they are properly set
    board.set_white_drawback(white_drawback)
    board.set_black_drawback(black_drawback)
    
    # Log the setup information
    print(f"Using position: {position_name} - {selected_fen}")
    if white_drawback:
        print(f"White drawback: {white_drawback}")
    else:
        print("White has no drawback")
        
    if black_drawback:
        print(f"Black drawback: {black_drawback}")
    else:
        print("Black has no drawback")
    
    # Verify setup was successful
    current_fen = board.fen()
    print(f"Board FEN after setup: {current_fen}")
    print(f"White's drawback: {board.get_active_drawback(chess.WHITE)}")
    print(f"Black's drawback: {board.get_active_drawback(chess.BLACK)}")

async def async_main():
    """Main game loop using asyncio for better performance"""
    # Load UI and game state from the state manager
    state = game_state_manager.state
    
    # Initialize pygame
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")
    
    # Load images for pieces at the beginning
    square_size = BOARD_HEIGHT // DIMENSION
    IMAGES = load_images(square_size)
    
    # Initialize game state
    game_state_manager.update(ai_move_cooldown=0)
    board = DrawbackBoard()
    
    # Load settings from config
    test_position = config.get_position()
    white_test_drawback = config.get_white_drawback()
    black_test_drawback = config.get_black_drawback()
    
    # Apply AI settings from config
    ai_settings = config.get_ai_settings()
    game_state_manager.update(
        white_ai=ai_settings["white_ai"],
        black_ai=ai_settings["black_ai"],
        ai_depth=ai_settings["depth"],
        time_limit=ai_settings["time_limit"],
        use_smart_time_management=ai_settings["smart_time_management"]
    )
    
    # Apply UI settings
    ui_settings = config.get_ui_settings()
    game_state_manager.update(flipped_board=ui_settings["flip_board"])
    
    # Set up a test environment with settings from config
    setup_test_environment(
        board,
        position_name=test_position,
        white_drawback=white_test_drawback,
        black_drawback=black_test_drawback
    )
        
    # Reset the game state
    game_state_manager.reset()
    
    # Restore UI settings after reset
    game_state_manager.update(
        flipped_board=ui_settings["flip_board"],
        white_ai=ai_settings["white_ai"],
        black_ai=ai_settings["black_ai"]
    )
    
    # Completely reset AI search knowledge for fresh evaluation
    from AI.enhanced_async_engine import engine_state, reset_search
    reset_search()
    engine_state.clear_search_knowledge()
    print("Game initialized with fresh AI search knowledge!")

    # Initialize end_message variable
    end_message = None

    while True:
        # Get the current state at the beginning of each loop
        state = game_state_manager.state
        
        # Process pygame events and update game state
        for event in p.event.get():
            if event.type == p.QUIT:
                p.quit()
                return
                
            elif event.type == p.MOUSEBUTTONDOWN:
                # Handle mouse clicks
                x, y = event.pos
                
                # Check if tinker button was clicked
                if tinker_button_rect.collidepoint(x, y):
                    open_tinker_panel(board)
                    continue
                
                # Handle board clicks (if not game over and not AI's turn)
                if not state.game_over and not state.is_ai_turn(board):
                    # Convert screen coordinates to board position
                    board_x = x - BOARD_X_OFFSET
                    board_y = y - BOARD_Y_OFFSET
                    
                    # Check if click is within board boundaries
                    if 0 <= board_y < BOARD_HEIGHT and 0 <= board_x < BOARD_HEIGHT:
                        # Calculate square indices
                        row, col = board_y // SQ_SIZE, board_x // SQ_SIZE
                        board_row, board_col = (row, 7 - col) if state.flipped_board else (7 - row, col)
                        clicked_square = chess.square(board_col, board_row)
                        
                        # First click: select a piece
                        if state.selected_square is None:
                            piece = board.piece_at(clicked_square)
                            if piece and piece.color == board.turn:
                                game_state_manager.update(selected_square=clicked_square)
                                print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                                
                        # Second click: move the selected piece
                        else:
                            # Check for pawn promotion
                            pawn = board.piece_at(state.selected_square)
                            if pawn and pawn.piece_type == chess.PAWN and (
                                (pawn.color == chess.WHITE and chess.square_rank(clicked_square) == 7) or
                                (pawn.color == chess.BLACK and chess.square_rank(clicked_square) == 0)
                            ):
                                import promotion_panel
                                promo = promotion_panel.run()
                                move_obj = chess.Move(state.selected_square, clicked_square, promotion=promo)
                            else:
                                move_obj = chess.Move(state.selected_square, clicked_square)
                            
                            # Try to make the move
                            if board.is_legal(move_obj):
                                board.push(move_obj)
                                print(f"Human moved: {move_obj}")
                                game_state_manager.update(selected_square=None)
                                
                                # Check for game end conditions AFTER the move is applied
                                game_over, winner_color, end_message = check_game_end_conditions(board)
                                if game_over:
                                    game_state_manager.update(
                                        game_over=game_over,
                                        winner_color=winner_color,
                                        end_message=end_message
                                    )
                                    print(f"Game over after human move: {end_message}")
                            else:
                                # If illegal move, check if clicking a new piece
                                piece = board.piece_at(clicked_square)
                                if piece and piece.color == board.turn:
                                    game_state_manager.update(selected_square=clicked_square)
                                    print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                                else:
                                    print(f"Illegal move: {chess.square_name(state.selected_square)} to {chess.square_name(clicked_square)}")
                                    game_state_manager.update(selected_square=None)
                                    
            elif event.type == p.KEYDOWN:
                # Handle key presses
                if event.key == p.K_r:
                    # Restart game with 'R' key
                    board = DrawbackBoard()
                    board.reset()
                    game_state_manager.reset()
                    
                    # Re-apply the test environment setup from config
                    test_position = config.get_position()
                    white_test_drawback = config.get_white_drawback()
                    black_test_drawback = config.get_black_drawback()
                    
                    setup_test_environment(
                        board,
                        position_name=test_position,
                        white_drawback=white_test_drawback,
                        black_drawback=black_test_drawback
                    )
                    
                    # Restore AI settings
                    ai_settings = config.get_ai_settings()
                    game_state_manager.update(
                        white_ai=ai_settings["white_ai"],
                        black_ai=ai_settings["black_ai"],
                        ai_depth=ai_settings["depth"],
                        time_limit=ai_settings["time_limit"],
                        use_smart_time_management=ai_settings["smart_time_management"]
                    )
                    
                    # Restore UI settings
                    ui_settings = config.get_ui_settings()
                    game_state_manager.update(flipped_board=ui_settings["flip_board"])
                    
                    # Cancel any running search and clear search knowledge
                    from AI.enhanced_async_engine import engine_state
                    reset_search()
                    engine_state.clear_search_knowledge()
                    print("Game restarted and search knowledge cleared!")
                    
                elif event.key == p.K_t:
                    # Open tinker panel with 'T' key
                    open_tinker_panel(board)
                
                elif event.key == p.K_z:
                    # Undo last move with 'Z' key
                    if undo_last_move(board):
                        game_state_manager.update(selected_square=None)  # Reset selection after undoing
                        # If AI is now supposed to move, give it a moment to reset
                        if state.is_ai_turn(board):
                            # Small delay to ensure clean reset before new AI search
                            game_state_manager.update(ai_move_cooldown=FPS // 4)  # 1/4 second cooldown
                    
        # Handle AI turn - non-blocking approach
        if not state.game_over and state.ai_move_cooldown <= 0:
            if state.is_ai_turn(board):
                # Check if a search is already in progress
                if state.search_in_progress:
                    # Check if the search has completed
                    from AI.enhanced_async_engine import get_result, is_search_complete
                    
                    if is_search_complete():
                        # Search is done, get the result and process it
                        result = get_result()
                        
                        # Try to get the last best move for fallback
                        last_seen_best_move = None
                        try:
                            from AI.drawback_Bot import current_best_move
                            if current_best_move:
                                last_seen_best_move = current_best_move.uci()
                        except (ImportError, AttributeError):
                            pass
                            
                        # Process the search result
                        process_search_result(board, result, last_seen_best_move)
                    else:
                        # Search is still running, check if it has timed out
                        from AI.enhanced_async_engine import engine_state
                        
                        if engine_state.start_time is not None:
                            elapsed_time = time.time() - engine_state.start_time
                            time_limit = engine_state.time_limit
                            
                            # Force completion if we've exceeded the time limit by 50%
                            if time_limit > 0 and elapsed_time > time_limit * 1.5:
                                print(f"Search exceeded time limit ({elapsed_time:.1f}s > {time_limit}s), forcing completion...")
                                result = get_result()  # This should trigger timeout handling in get_result
                                
                                # Get last best move for fallback
                                last_seen_best_move = None
                                try:
                                    from AI.drawback_Bot import current_best_move
                                    if current_best_move:
                                        last_seen_best_move = current_best_move.uci()
                                except (ImportError, AttributeError):
                                    pass
                                
                                # Process the result
                                process_search_result(board, result, last_seen_best_move)
                else:
                    # No search in progress, start one
                    handle_ai_turn(board)
        else:
            # Decrement cooldown timer if it's active
            if state.ai_move_cooldown > 0:
                game_state_manager.update(ai_move_cooldown=state.ai_move_cooldown - 1)
                    
        # Draw everything
        screen.fill(TEXT_COLOR_BLACK)  # Clear screen with black background
        
        # Draw board and pieces
        draw_board(screen, DIMENSION, BOARD_HEIGHT, BOARD_HEIGHT, state.flipped_board, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        draw_pieces(screen, board, state.flipped_board, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        
        # Draw UI elements
        display_drawbacks(screen, board, state.flipped_board)
        display_current_turn(screen, board)
        draw_tinker_button(screen)
        display_ai_status(screen, board)
        
        # Highlight selected square and show legal moves
        if state.selected_square is not None:
            square_size = BOARD_HEIGHT // DIMENSION
            r = chess.square_rank(state.selected_square)
            c = chess.square_file(state.selected_square)
            draw_row, draw_col = (r, 7 - c) if state.flipped_board else (7 - r, c)
            
            # Create highlight surface
            highlight = p.Surface((square_size, square_size), p.SRCALPHA)
            highlight.fill(HIGHLIGHT_COLOR)
            screen.blit(highlight, (BOARD_X_OFFSET + draw_col * square_size, 
                                  BOARD_Y_OFFSET + draw_row * square_size))
                                  
            # Draw indicators for legal moves
            draw_legal_move_indicators(screen, board, state.selected_square, state.flipped_board, 
                                     DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
                                     
        # Display winner message if game is over
        if state.game_over:
            display_winner(screen, state.winner_color, state.end_message)
            
        # Update display and control frame rate    
        clock.tick(FPS)
        p.display.flip()
        
        # Give more time for background tasks
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    asyncio.run(async_main())