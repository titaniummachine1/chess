import os
import sys
import pygame
import traceback

# Try to import pygame_gui with better error handling
try:
    import pygame_gui
    from pygame_gui.elements import UIButton, UIDropDownMenu, UILabel, UIPanel, UIWindow
    # Check what version we're working with
    print(f"Using pygame_gui version: {pygame_gui.__version__ if hasattr(pygame_gui, '__version__') else 'unknown'}")
    PYGAME_GUI_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Could not import pygame_gui module: {e}")
    traceback.print_exc()
    PYGAME_GUI_AVAILABLE = False

import chess
from GameState.drawback_manager import DRAWBACKS, get_drawback_params, update_drawback_params, get_drawback_info

# Custom checkbox class since pygame_gui might not have UICheckbox in this version
class Checkbox:
    def __init__(self, relative_rect, text, manager, container=None, starting_state=False):
        self.rect = pygame.Rect(relative_rect)
        self.text = text
        self.checked = starting_state
        self.manager = manager
        self.container = container
        
        # Create the UI elements we need
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=self.rect,
            manager=manager,
            container=container,
            object_id=f"checkbox_panel_{id(self)}"
        )
        
        # The checkbox square (20x20 px)
        checkbox_rect = pygame.Rect(0, 0, 20, 20)
        self.checkbox_button = pygame_gui.elements.UIButton(
            relative_rect=checkbox_rect,
            text="",
            manager=manager,
            container=self.panel,
            object_id=f"checkbox_button_{id(self)}"
        )
        
        # Label next to checkbox
        label_rect = pygame.Rect(25, 0, self.rect.width - 25, self.rect.height)
        self.label = pygame_gui.elements.UILabel(
            relative_rect=label_rect,
            text=text,
            manager=manager,
            container=self.panel
        )
        
        # Update visual state
        self.update_appearance()
    
    def update_appearance(self):
        """Update the checkbox appearance based on checked state"""
        if self.checked:
            self.checkbox_button.set_text("✓")
        else:
            self.checkbox_button.set_text("")
    
    def process_event(self, event):
        """Process events for this checkbox"""
        if event.type == pygame.USEREVENT:
            if (event.user_type == pygame_gui.UI_BUTTON_PRESSED and 
                event.ui_element == self.checkbox_button):
                self.checked = not self.checked
                self.update_appearance()
                return True
        return False
    
    def kill(self):
        """Clean up the UI elements"""
        self.panel.kill()

class TinkerPanel:
    def __init__(self, board_reference=None, ai_settings=None):
        """Initialize the Tinker Panel"""
        # Verify pygame_gui is available
        if not PYGAME_GUI_AVAILABLE:
            print("Cannot create TinkerPanel: pygame_gui module is missing")
            raise ImportError("pygame_gui module is required for TinkerPanel")
            
        pygame.init()
        print("Initializing Tinker Panel window...")
        
        # Store reference to game window size to restore later
        self.previous_display_info = pygame.display.Info()
        
        # Set up window
        self.window_size = (800, 600)
        try:
            self.screen = pygame.display.set_mode(self.window_size)
            pygame.display.set_caption("Drawback Chess - Tinker Panel")
        except pygame.error as e:
            print(f"Error creating Tinker Panel window: {e}")
            raise
            
        # Initialize UI manager
        try:
            self.manager = pygame_gui.UIManager(self.window_size)
        except Exception as e:
            print(f"Error creating UI manager: {e}")
            traceback.print_exc()
            raise
            
        self.clock = pygame.time.Clock()
        self.is_running = True
        self.result = None
        
        # Store references
        self.board = board_reference
        self.white_drawback = self.board.get_active_drawback(chess.WHITE) if self.board else None
        self.black_drawback = self.board.get_active_drawback(chess.BLACK) if self.board else None
        
        # AI settings
        self.ai_settings = ai_settings or {
            "WHITE_AI": False,
            "BLACK_AI": True,
            "AI_DEPTH": 4
        }
        
        # UI options
        self.options = {
            "FLIP_BOARD": False
        }
        
        # Custom UI elements we need to track separately
        self.custom_elements = []
        
        print("Building Tinker Panel UI...")
        try:
            self._init_ui()
            print("Tinker Panel UI initialized successfully")
        except Exception as e:
            print(f"Error building UI: {e}")
            traceback.print_exc()
            raise
            
    def _init_ui(self):
        """Initialize the UI components"""
        # Main panel
        panel_width = 780
        panel_height = 550
        self.panel = UIPanel(
            relative_rect=pygame.Rect((10, 10), (panel_width, panel_height)),
            manager=self.manager
        )
        
        # Title
        title_label = UILabel(
            relative_rect=pygame.Rect((20, 10), (740, 30)),
            text="Drawback Chess - Tinker Panel",
            manager=self.manager,
            container=self.panel
        )
        
        # White drawback selection
        white_label = UILabel(
            relative_rect=pygame.Rect((20, 50), (100, 30)),
            text="White:",
            manager=self.manager,
            container=self.panel
        )
        
        # Get all available drawbacks with proper display names
        drawback_options = ["None"]
        drawback_display_names = {}
        
        # Get display names for each drawback
        for name, info in DRAWBACKS.items():
            if info.get("supported", False):
                # Make it prettier for display
                display_name = name.replace("_", " ").title()
                drawback_display_names[display_name] = name
                drawback_options.append(display_name)
        
        # Sort options alphabetically
        drawback_options = ["None"] + sorted([opt for opt in drawback_options if opt != "None"])
        
        # Store the mapping
        self.drawback_display_to_name = drawback_display_names
        self.drawback_name_to_display = {v: k for k, v in drawback_display_names.items()}
        
        # Get current drawback display name
        white_display = "None"
        if self.white_drawback:
            white_display = self.white_drawback.replace("_", " ").title()
        
        # Create the dropdown
        self.white_drawback_dropdown = UIDropDownMenu(
            options_list=drawback_options,
            starting_option=white_display,
            relative_rect=pygame.Rect((120, 50), (200, 30)),
            manager=self.manager,
            container=self.panel
        )
        
        # Config section for white drawback
        self.white_config_section = UIPanel(
            relative_rect=pygame.Rect((330, 50), (430, 40)),
            manager=self.manager,
            container=self.panel
        )
        
        # Initialize white config section if needed
        self._update_config_section(chess.WHITE)
        
        # Black drawback selection
        black_label = UILabel(
            relative_rect=pygame.Rect((20, 100), (100, 30)),
            text="Black:",
            manager=self.manager,
            container=self.panel
        )
        
        # Get current black drawback display name
        black_display = "None"
        if self.black_drawback:
            black_display = self.black_drawback.replace("_", " ").title()
        
        self.black_drawback_dropdown = UIDropDownMenu(
            options_list=drawback_options,
            starting_option=black_display,
            relative_rect=pygame.Rect((120, 100), (200, 30)),
            manager=self.manager,
            container=self.panel
        )
        
        # Config section for black drawback
        self.black_config_section = UIPanel(
            relative_rect=pygame.Rect((330, 100), (430, 40)),
            manager=self.manager,
            container=self.panel
        )
        
        # Initialize black config section if needed
        self._update_config_section(chess.BLACK)
        
        # AI settings
        ai_title = UILabel(
            relative_rect=pygame.Rect((20, 150), (740, 30)),
            text="AI Settings",
            manager=self.manager,
            container=self.panel
        )
        
        # White AI checkbox - using custom Checkbox class
        self.white_ai_checkbox = Checkbox(
            relative_rect=pygame.Rect((20, 190), (150, 20)),
            text="White AI",
            manager=self.manager,
            container=self.panel,
            starting_state=self.ai_settings.get("WHITE_AI", False)
        )
        self.custom_elements.append(self.white_ai_checkbox)
        
        # Black AI checkbox
        self.black_ai_checkbox = Checkbox(
            relative_rect=pygame.Rect((20, 220), (150, 20)),
            text="Black AI",
            manager=self.manager,
            container=self.panel,
            starting_state=self.ai_settings.get("BLACK_AI", True)
        )
        self.custom_elements.append(self.black_ai_checkbox)
        
        # AI depth selection
        depth_label = UILabel(
            relative_rect=pygame.Rect((20, 250), (100, 30)),
            text="AI Depth:",
            manager=self.manager,
            container=self.panel
        )
        
        self.depth_dropdown = UIDropDownMenu(
            options_list=[str(i) for i in range(1, 7)],
            starting_option=str(self.ai_settings.get("AI_DEPTH", 4)),
            relative_rect=pygame.Rect((120, 250), (60, 30)),
            manager=self.manager,
            container=self.panel
        )
        
        # UI options
        ui_title = UILabel(
            relative_rect=pygame.Rect((20, 300), (740, 30)),
            text="UI Options",
            manager=self.manager,
            container=self.panel
        )
        
        # Flip board checkbox
        self.flip_board_checkbox = Checkbox(
            relative_rect=pygame.Rect((20, 340), (150, 20)),
            text="Flip Board",
            manager=self.manager,
            container=self.panel,
            starting_state=self.options.get("FLIP_BOARD", False)
        )
        self.custom_elements.append(self.flip_board_checkbox)
        
        # Apply/Cancel buttons
        self.apply_button = UIButton(
            relative_rect=pygame.Rect((panel_width - 200, panel_height - 50), (90, 40)),
            text="Apply",
            manager=self.manager,
            container=self.panel
        )
        
        self.cancel_button = UIButton(
            relative_rect=pygame.Rect((panel_width - 100, panel_height - 50), (90, 40)),
            text="Cancel",
            manager=self.manager,
            container=self.panel
        )
    
    def _update_config_section(self, color):
        """Update the configuration section for a drawback"""
        drawback = self.white_drawback if color == chess.WHITE else self.black_drawback
        config_section = self.white_config_section if color == chess.WHITE else self.black_config_section
        color_value = 0 if color == chess.WHITE else 1  # Use numeric values for object IDs
        
        # Clear existing widgets from the section
        for element in config_section.elements[:]:
            element.kill()
        
        if not drawback or drawback == "None":
            label = UILabel(
                relative_rect=pygame.Rect((10, 10), (410, 20)),
                text="No configuration available",
                manager=self.manager,
                container=config_section
            )
            return
        
        # Get parameters directly from drawback dictionary 
        drawback_info = DRAWBACKS.get(drawback, {})
        
        # Check if it's configurable
        if not drawback_info.get("configurable", False):
            label = UILabel(
                relative_rect=pygame.Rect((10, 10), (410, 20)),
                text="No configuration available",
                manager=self.manager,
                container=config_section
            )
            return
            
        # Get parameters for this drawback
        config_type = drawback_info.get("config_type", "")
        config_name = drawback_info.get("config_name", "Parameter")
        params = drawback_info.get("params", {})
        
        if not config_type:
            label = UILabel(
                relative_rect=pygame.Rect((10, 10), (410, 20)),
                text="No configuration available",
                manager=self.manager,
                container=config_section
            )
            return
            
        # Config name label
        config_label = UILabel(
            relative_rect=pygame.Rect((10, 10), (150, 20)),
            text=f"{config_name}:",
            manager=self.manager,
            container=config_section
        )
        
        if config_type == "square":
            # Create file dropdown (A-H)
            file_options = ["a", "b", "c", "d", "e", "f", "g", "h"]
            sun_square = params.get("sun_square", chess.E4)
            file_idx = chess.square_file(sun_square)
            rank_idx = chess.square_rank(sun_square)
            
            file_dropdown = UIDropDownMenu(
                options_list=file_options,
                starting_option=file_options[file_idx],
                relative_rect=pygame.Rect((170, 10), (50, 20)),
                manager=self.manager,
                container=config_section,
                object_id=f"file_dropdown_{color_value}"
            )
            
            # Create rank dropdown (1-8)
            rank_options = ["1", "2", "3", "4", "5", "6", "7", "8"]
            rank_dropdown = UIDropDownMenu(
                options_list=rank_options,
                starting_option=rank_options[rank_idx],
                relative_rect=pygame.Rect((230, 10), (50, 20)),
                manager=self.manager,
                container=config_section,
                object_id=f"rank_dropdown_{color_value}"
            )
            
        elif config_type == "rank":
            # Create rank dropdown (1-8)
            rank_options = ["1", "2", "3", "4", "5", "6", "7", "8"]
            rank = params.get("rank", 3)
            
            # Add 1 to display rank in 1-indexed form for users
            display_rank = min(7, max(0, rank)) + 1
            
            rank_dropdown = UIDropDownMenu(
                options_list=rank_options,
                starting_option=str(display_rank),
                relative_rect=pygame.Rect((170, 10), (50, 20)),
                manager=self.manager,
                container=config_section,
                object_id=f"rank_dropdown_{color_value}"
            )

    def _save_config_values(self):
        """Save the current configuration values for drawbacks"""
        # White drawback
        if self.white_drawback and self.white_drawback != "None":
            # Get drawback info directly from DRAWBACKS to ensure we're looking at the same info
            drawback_info = DRAWBACKS.get(self.white_drawback, {})
            
            # Only process if it's configurable
            if drawback_info.get("configurable", False):
                config_type = drawback_info.get("config_type", "")
                
                if config_type == "square":
                    # Get file and rank dropdown elements by object ID
                    file_dropdown = None
                    rank_dropdown = None
                    
                    for element in self.white_config_section.elements:
                        if hasattr(element, "object_id") and element.object_id == "file_dropdown_0":
                            file_dropdown = element
                        elif hasattr(element, "object_id") and element.object_id == "rank_dropdown_0":
                            rank_dropdown = element
                    
                    if file_dropdown and rank_dropdown:
                        try:
                            file_idx = "abcdefgh".index(file_dropdown.selected_option.lower())
                            rank_idx = int(rank_dropdown.selected_option) - 1  # Convert from 1-indexed to 0-indexed
                            square = chess.square(file_idx, rank_idx)
                            print(f"Updating white {self.white_drawback} sun_square to {chess.square_name(square)}")
                            DRAWBACKS[self.white_drawback]["params"]["sun_square"] = square
                        except Exception as e:
                            print(f"Error updating white drawback: {e}")
                
                elif config_type == "rank":
                    rank_dropdown = None
                    for element in self.white_config_section.elements:
                        if hasattr(element, "object_id") and element.object_id == "rank_dropdown_0":
                            rank_dropdown = element
                    
                    if rank_dropdown:
                        try:
                            # Convert from 1-indexed to 0-indexed
                            rank = int(rank_dropdown.selected_option) - 1
                            print(f"Updating white {self.white_drawback} rank to {rank}")
                            DRAWBACKS[self.white_drawback]["params"]["rank"] = rank
                        except Exception as e:
                            print(f"Error updating white drawback rank: {e}")
        
        # Black drawback - similar logic as white
        if self.black_drawback and self.black_drawback != "None":
            # Get drawback info directly from DRAWBACKS
            drawback_info = DRAWBACKS.get(self.black_drawback, {})
            
            # Only process if it's configurable
            if drawback_info.get("configurable", False):
                config_type = drawback_info.get("config_type", "")
                
                if config_type == "square":
                    # Get file and rank dropdown elements by object ID
                    file_dropdown = None
                    rank_dropdown = None
                    
                    for element in self.black_config_section.elements:
                        if hasattr(element, "object_id") and element.object_id == "file_dropdown_1":
                            file_dropdown = element
                        elif hasattr(element, "object_id") and element.object_id == "rank_dropdown_1":
                            rank_dropdown = element
                    
                    if file_dropdown and rank_dropdown:
                        try:
                            file_idx = "abcdefgh".index(file_dropdown.selected_option.lower())
                            rank_idx = int(rank_dropdown.selected_option) - 1  # Convert from 1-indexed to 0-indexed
                            square = chess.square(file_idx, rank_idx)
                            print(f"Updating black {self.black_drawback} sun_square to {chess.square_name(square)}")
                            DRAWBACKS[self.black_drawback]["params"]["sun_square"] = square
                        except Exception as e:
                            print(f"Error updating black drawback: {e}")
                
                elif config_type == "rank":
                    rank_dropdown = None
                    for element in self.black_config_section.elements:
                        if hasattr(element, "object_id") and element.object_id == "rank_dropdown_1":
                            rank_dropdown = element
                    
                    if rank_dropdown:
                        try:
                            # Convert from 1-indexed to 0-indexed
                            rank = int(rank_dropdown.selected_option) - 1
                            print(f"Updating black {self.black_drawback} rank to {rank}")
                            DRAWBACKS[self.black_drawback]["params"]["rank"] = rank
                        except Exception as e:
                            print(f"Error updating black drawback rank: {e}")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                self.result = None
                return
            
            # Process events for custom UI components
            for element in self.custom_elements:
                element.process_event(event)
            
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.apply_button:
                        # Save config values before applying drawback changes
                        self._save_config_values()
                        
                        # Get selected drawback names
                        white_display = self.white_drawback_dropdown.selected_option
                        black_display = self.black_drawback_dropdown.selected_option
                        
                        # Convert from display names to internal names
                        white_drawback = None if white_display == "None" else self.drawback_display_to_name.get(white_display, white_display.lower().replace(" ", "_"))
                        black_drawback = None if black_display == "None" else self.drawback_display_to_name.get(black_display, black_display.lower().replace(" ", "_"))
                        
                        # Debug output
                        print(f"Setting drawbacks - White: {white_drawback}, Black: {black_drawback}")
                        
                        # Create result with AI settings
                        self.ai_settings = {
                            "WHITE_AI": self.white_ai_checkbox.checked,
                            "BLACK_AI": self.black_ai_checkbox.checked,
                            "AI_DEPTH": int(self.depth_dropdown.selected_option)
                        }
                        
                        self.options = {
                            "FLIP_BOARD": self.flip_board_checkbox.checked
                        }
                        
                        self.result = (white_drawback, black_drawback, self.ai_settings, self.options)
                        
                        # Update the board drawbacks
                        if self.board:
                            self.board.set_white_drawback(white_drawback)
                            self.board.set_black_drawback(black_drawback)
                        
                        self.is_running = False
                        
                    elif event.ui_element == self.cancel_button:
                        self.is_running = False
                        self.result = None
                
                elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                    if event.ui_element == self.white_drawback_dropdown:
                        # Convert from display name to actual drawback name
                        if event.text == "None":
                            self.white_drawback = None
                        else:
                            self.white_drawback = self.drawback_display_to_name.get(event.text, event.text.lower().replace(" ", "_"))
                        self._update_config_section(chess.WHITE)
                    elif event.ui_element == self.black_drawback_dropdown:
                        # Convert from display name to actual drawback name
                        if event.text == "None":
                            self.black_drawback = None
                        else:
                            self.black_drawback = self.drawback_display_to_name.get(event.text, event.text.lower().replace(" ", "_"))
                        self._update_config_section(chess.BLACK)
            
            self.manager.process_events(event)
    
    def run(self):
        while self.is_running:
            time_delta = self.clock.tick(60)/1000.0
            self.handle_events()
            
            self.screen.fill((50, 50, 50))
            self.manager.update(time_delta)
            self.manager.draw_ui(self.screen)
            
            pygame.display.update()
        
        return self.result
