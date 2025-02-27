import pygame as p
import sys
import os
import chess
from GameState.drawback_manager import get_drawback_info, DRAWBACKS
from ui.components import Button, Checkbox, Slider, SearchBox
from ui.drawback_list import DrawbackList

class TinkerPanel:
    """
    A simplified separate control panel for selecting drawbacks without pygame_gui dependency.
    Features:
    - Split screen with White drawbacks on left, Black on right
    - Search functionality to find drawbacks by name
    - Immediate application of selected drawbacks to the game
    - AI player control selection
    """
    def __init__(self, width=800, height=600, board_reference=None, callback=None, ai_settings=None):
        self.width = width
        self.height = height
        self.board = board_reference  # Reference to the chess board
        self.callback = callback  # Callback to update the main game
        
        # AI control settings
        self.ai_settings = ai_settings or {"WHITE_AI": False, "BLACK_AI": True, "AI_DEPTH": 3}
        
        # Initialize Pygame if not already done
        if not p.get_init():
            p.init()
        
        # Create the window
        self.window = p.display.set_mode((width, height), p.RESIZABLE)
        p.display.set_caption("Drawback Chess - Tinker's Control Panel")
        
        # Font settings
        self.title_font = p.font.SysFont(None, 36)
        self.normal_font = p.font.SysFont(None, 24)
        self.small_font = p.font.SysFont(None, 20)
        
        # UI colors
        self.bg_color = (50, 50, 50)
        self.text_color = (255, 255, 255)
        
        # Initialize UI components
        self._init_ui_components()
        
        # Initialize drawback lists
        self._init_drawback_lists()
        
        # Running flag
        self.running = True
        
        # Clock for limiting frame rate
        self.clock = p.time.Clock()
        
        # Results flags
        self.flip_board = False
    
    def _init_ui_components(self):
        """Initialize UI components like buttons, checkboxes, etc."""
        # Action buttons
        self.close_button = Button(
            self.width/2 - 60, self.height - 60, 120, 40, "Close",
            bg_color=(150, 50, 50)
        )
        
        self.restart_button = Button(
            self.width/2 - 150, self.height - 60, 80, 40, "Restart",
            bg_color=(0, 150, 0)
        )
        
        self.flip_button = Button(
            self.width/2 + 70, self.height - 60, 80, 40, "Flip",
            bg_color=(150, 100, 0)
        )
        
        # AI controls
        self.white_ai_checkbox = Checkbox(
            40, 60, 15, "AI Control", font=self.small_font
        )
        self.white_ai_checkbox.checked = self.ai_settings.get("WHITE_AI", False)
        
        self.black_ai_checkbox = Checkbox(
            int(self.width/2) + 30, 60, 15, "AI Control", font=self.small_font
        )
        self.black_ai_checkbox.checked = self.ai_settings.get("BLACK_AI", True)
        
        # AI Depth slider
        self.ai_depth_slider = Slider(
            self.width/2 - 120, 85, 240, 10, 1, 5,
            self.ai_settings.get("AI_DEPTH", 3),
            text="AI Depth"
        )
    
    def _init_drawback_lists(self):
        """Initialize the white and black drawback lists."""
        # Create drawback lists
        self.white_drawbacks = DrawbackList(
            20, 110, int(self.width/2) - 30, self.height - 180, chess.WHITE, self.small_font
        )
        
        self.black_drawbacks = DrawbackList(
            int(self.width/2) + 10, 110, int(self.width/2) - 30, self.height - 180, chess.BLACK, self.small_font
        )
        
        # Load current drawbacks from the board if available
        if self.board:
            white_drawback = self.board.get_active_drawback(chess.WHITE)
            black_drawback = self.board.get_active_drawback(chess.BLACK)
            
            if white_drawback:
                self.white_drawbacks.selected_drawback = white_drawback
            
            if black_drawback:
                self.black_drawbacks.selected_drawback = black_drawback
        
        # Populate drawback lists
        self.white_drawbacks.populate_list(self.white_drawbacks.selected_drawback)
        self.black_drawbacks.populate_list(self.black_drawbacks.selected_drawback)
    
    def wrap_text(self, text, font, max_width):
        """Wrap text to fit within a given width."""
        if not text:
            return []
            
        words = text.split(' ')
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            word_surface = font.render(word + ' ', True, self.text_color)
            word_width = word_surface.get_width()
            
            if current_width + word_width > max_width:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
            else:
                current_line.append(word)
                current_width += word_width
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines
    
    def draw(self):
        """Draw all UI components to the screen."""
        # Fill background
        self.window.fill(self.bg_color)
        
        # Draw title
        title_surf = self.title_font.render("Drawback Chess - Tinker's Control Panel", True, self.text_color)
        title_rect = title_surf.get_rect(center=(self.width/2, 30))
        self.window.blit(title_surf, title_rect)
        
        # Draw divider line
        p.draw.line(self.window, (150, 150, 150), 
                   (self.width/2, 60), 
                   (self.width/2, self.height - 70), 2)
        
        # Draw AI controls
        self.white_ai_checkbox.draw(self.window)
        self.black_ai_checkbox.draw(self.window)
        self.ai_depth_slider.draw(self.window)
        
        # Draw drawback lists
        white_hover = self.white_drawbacks.draw(self.window)
        black_hover = self.black_drawbacks.draw(self.window)
        
        # Draw buttons
        self.close_button.draw(self.window)
        self.restart_button.draw(self.window)
        self.flip_button.draw(self.window)
        
        # Display hover description for drawback (from either list)
        hover_description = white_hover or black_hover
        if hover_description:
            # Create a semi-transparent background
            desc_surf = p.Surface((self.width, 60), p.SRCALPHA)
            desc_surf.fill((0, 0, 0, 180))
            self.window.blit(desc_surf, (0, self.height - 110))
            
            # Wrap and render description text
            wrapped_lines = self.wrap_text(hover_description, self.small_font, self.width - 40)
            
            for i, line in enumerate(wrapped_lines):
                desc_text = self.small_font.render(line, True, (255, 255, 255))
                desc_rect = desc_text.get_rect(center=(self.width/2, self.height - 100 + i*20))
                self.window.blit(desc_text, desc_rect)
        
        # Update display
        p.display.flip()
    
    def handle_event(self, event):
        """Handle pygame events for the panel."""
        if event.type == p.QUIT:
            self.running = False
            return True

        elif event.type == p.MOUSEBUTTONDOWN:
            pos = event.pos
            
            # Handle button clicks
            if self.close_button.is_clicked(pos):
                self.running = False
                return True
            
            if self.restart_button.is_clicked(pos):
                # Signal to restart the game
                if self.board:
                    self.board.reset()
                return True
            
            if self.flip_button.is_clicked(pos):
                self.flip_board = True
                return True
            
            # Handle AI checkboxes
            if self.white_ai_checkbox.is_clicked(pos):
                self.white_ai_checkbox.toggle()
                self.ai_settings["WHITE_AI"] = self.white_ai_checkbox.checked
                return True
            
            if self.black_ai_checkbox.is_clicked(pos):
                self.black_ai_checkbox.toggle()
                self.ai_settings["BLACK_AI"] = self.black_ai_checkbox.checked
                return True
            
            # Handle AI depth slider
            if self.ai_depth_slider.is_clicked(pos):
                self.ai_depth_slider.start_drag(pos)
                return True
            
            # Handle drawback list clicks - pass the board for immediate application
            if self.white_drawbacks.handle_click(pos, self.board):
                return True
            
            if self.black_drawbacks.handle_click(pos, self.board):
                return True
        
        elif event.type == p.MOUSEBUTTONUP:
            # Handle AI depth slider release
            if self.ai_depth_slider.is_dragging:
                self.ai_depth_slider.stop_drag()
                self.ai_settings["AI_DEPTH"] = self.ai_depth_slider.value
                return True
        
        elif event.type == p.MOUSEMOTION:
            # Handle AI depth slider drag
            if self.ai_depth_slider.is_dragging:
                self.ai_depth_slider.update_drag(event.pos)
                return True
        
        elif event.type == p.KEYDOWN:
            if event.key == p.K_ESCAPE:
                self.running = False
                return True
            
            # Handle search box input
            if self.white_drawbacks.handle_key(event):
                return True
            
            if self.black_drawbacks.handle_key(event):
                return True
        
        # Handle mouse wheel scrolling
        elif event.type == p.MOUSEWHEEL:
            # Determine which list to scroll based on mouse position
            mouse_x = p.mouse.get_pos()[0]
            if mouse_x < self.width/2:
                self.white_drawbacks.handle_scroll(event.y)
            else:
                self.black_drawbacks.handle_scroll(event.y)
            return True
        
        return False
    
    def run(self):
        """Main loop for the Tinker's Control Panel."""
        while self.running:
            for event in p.event.get():
                self.handle_event(event)
            
            # Draw the UI
            self.draw()
            
            # Cap the frame rate
            self.clock.tick(60)
        
        # Return the selected drawbacks, AI settings, and other options
        return (self.white_drawbacks.selected_drawback, self.black_drawbacks.selected_drawback, 
                self.ai_settings, {"FLIP_BOARD": self.flip_board})
