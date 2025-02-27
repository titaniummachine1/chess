import pygame as p
import chess

class Button:
    """Generic button component for UI."""
    def __init__(self, x, y, width, height, text, text_color=(255, 255, 255), 
                 bg_color=(100, 100, 100), active_color=(150, 150, 255), font=None):
        self.rect = p.Rect(x, y, width, height)
        self.text = text
        self.text_color = text_color
        self.bg_color = bg_color
        self.active_color = active_color
        self.active = False
        self.font = font or p.font.SysFont(None, 24)

    def draw(self, surface):
        # Draw the button background
        color = self.active_color if self.active else self.bg_color
        p.draw.rect(surface, color, self.rect)
        
        # Draw the button text
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
        
    def set_active(self, active):
        self.active = active


class Checkbox:
    """Checkbox component for toggling options."""
    def __init__(self, x, y, size, text, text_color=(255, 255, 255), bg_color=(200, 200, 200), font=None):
        self.rect = p.Rect(x, y, size, size)
        self.text = text
        self.text_color = text_color
        self.bg_color = bg_color
        self.checked = False
        self.font = font or p.font.SysFont(None, 20)

    def draw(self, surface):
        # Draw checkbox
        p.draw.rect(surface, self.bg_color, self.rect)
        
        # Draw X if checked
        if self.checked:
            p.draw.line(surface, (0, 0, 0), 
                      (self.rect.left + 2, self.rect.top + 2),
                      (self.rect.right - 2, self.rect.bottom - 2), 2)
            p.draw.line(surface, (0, 0, 0), 
                      (self.rect.left + 2, self.rect.bottom - 2),
                      (self.rect.right - 2, self.rect.top + 2), 2)
        
        # Draw label
        label = self.font.render(self.text, True, self.text_color)
        surface.blit(label, (self.rect.right + 5, self.rect.centery - label.get_height() / 2))
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
        
    def toggle(self):
        self.checked = not self.checked


class Slider:
    """Slider component for selecting numeric values."""
    def __init__(self, x, y, width, height, min_val, max_val, initial_val, 
                 text="Slider", text_color=(255, 255, 255), track_color=(150, 150, 150), 
                 thumb_color=(200, 200, 200), font=None):
        self.track_rect = p.Rect(x, y, width, height)
        self.thumb_size = height * 2
        
        # Calculate position based on initial_val
        thumb_x = self.calculate_thumb_x(initial_val, min_val, max_val)
        self.thumb_rect = p.Rect(thumb_x - self.thumb_size//2, y - self.thumb_size//4, 
                                self.thumb_size, self.thumb_size)
        
        self.text = text
        self.text_color = text_color
        self.track_color = track_color
        self.thumb_color = thumb_color
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.font = font or p.font.SysFont(None, 24)
        self.is_dragging = False

    def calculate_thumb_x(self, value, min_val, max_val):
        """Calculate the x position of the thumb based on value."""
        range_val = max_val - min_val
        if range_val == 0:
            return self.track_rect.left
        
        percentage = (value - min_val) / range_val
        return self.track_rect.left + int(percentage * self.track_rect.width)

    def update_value_from_pos(self, x):
        """Update the current value based on thumb position."""
        # Constrain x to track bounds
        x = max(self.track_rect.left, min(x, self.track_rect.right))
        
        # Calculate percentage
        percentage = (x - self.track_rect.left) / self.track_rect.width
        
        # Calculate actual value
        self.value = self.min_val + percentage * (self.max_val - self.min_val)
        
        # For integer sliders, round to nearest integer
        if isinstance(self.min_val, int) and isinstance(self.max_val, int):
            self.value = round(self.value)
        
        # Update thumb position
        self.thumb_rect.centerx = x
        
        return self.value

    def draw(self, surface):
        # Draw track
        p.draw.rect(surface, self.track_color, self.track_rect)
        
        # Draw thumb
        p.draw.rect(surface, self.thumb_color, self.thumb_rect)
        
        # Draw label with current value
        label = self.font.render(f"{self.text}: {self.value}", True, self.text_color)
        surface.blit(label, (self.track_rect.left, self.track_rect.top - 25))
        
        # Draw min/max markers
        if isinstance(self.min_val, int) and isinstance(self.max_val, int):
            # Add tick marks for each integer value
            for val in range(self.min_val, self.max_val + 1):
                x = self.calculate_thumb_x(val, self.min_val, self.max_val)
                p.draw.line(surface, self.text_color, 
                           (x, self.track_rect.bottom + 2),
                           (x, self.track_rect.bottom + 10), 2)
                
                # Draw value labels
                val_label = p.font.SysFont(None, 20).render(str(val), True, self.text_color)
                val_rect = val_label.get_rect(center=(x, self.track_rect.bottom + 20))
                surface.blit(val_label, val_rect)
                
    def is_clicked(self, pos):
        """Check if the thumb or track was clicked."""
        return self.thumb_rect.collidepoint(pos) or self.track_rect.inflate(0, 20).collidepoint(pos)
    
    def start_drag(self, pos):
        """Start dragging the slider thumb."""
        self.is_dragging = True
        self.update_value_from_pos(pos[0])
        return self.value
    
    def stop_drag(self):
        """Stop dragging the slider thumb."""
        self.is_dragging = False
        return self.value
    
    def update_drag(self, pos):
        """Update the slider value while dragging."""
        if self.is_dragging:
            self.update_value_from_pos(pos[0])
            return self.value
        return None


class SearchBox:
    """Text input box for searching."""
    def __init__(self, x, y, width, height, placeholder="Search...", 
                 text_color=(0, 0, 0), bg_color=(200, 200, 200), 
                 placeholder_color=(120, 120, 120), font=None):
        self.rect = p.Rect(x, y, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.text_color = text_color
        self.placeholder_color = placeholder_color
        self.bg_color = bg_color
        self.font = font or p.font.SysFont(None, 24)
        self.small_font = p.font.SysFont(None, 20) if font is None else font
        self.active = False

    def draw(self, surface):
        # Draw box background
        border = 0 if self.active else 2
        p.draw.rect(surface, self.bg_color, self.rect, border)
        
        # Draw text or placeholder
        if self.text:
            text_surf = self.font.render(self.text, True, self.text_color)
            surface.blit(text_surf, (self.rect.x + 5, self.rect.y + 5))
        else:
            placeholder_surf = self.small_font.render(self.placeholder, True, self.placeholder_color)
            surface.blit(placeholder_surf, (self.rect.x + 5, self.rect.y + 7))
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
        
    def handle_key(self, event):
        """Handle key press events for the search box."""
        if not self.active:
            return False
            
        if event.key == p.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key == p.K_RETURN:
            return True  # Signal search submission
        elif event.unicode:
            self.text += event.unicode
        return False  # Still editing


class DrawbackButton:
    """Button for selecting a drawback with hover description."""
    def __init__(self, x, y, width, height, drawback_id, display_name, description="", 
                 color=chess.WHITE, active=False, font=None):
        self.rect = p.Rect(x, y, width, height)
        self.id = drawback_id
        self.text = display_name
        self.description = description
        self.color = color
        self.active = active
        self.font = font or p.font.SysFont(None, 20)
        self.text_color = (255, 255, 255)
        self.bg_color = (100, 100, 100)
        self.active_color = (150, 150, 255)
    
    def draw(self, surface, y_offset=0):
        """Draw the button with vertical scrolling offset."""
        # Adjust rect for scrolling
        adjusted_rect = p.Rect(
            self.rect.x, 
            self.rect.y - y_offset,
            self.rect.width,
            self.rect.height
        )
        
        # Only draw if in view (assuming window height is around 600px)
        if adjusted_rect.y < 0 or adjusted_rect.y > 600:
            return False
            
        # Draw button
        color = self.active_color if self.active else self.bg_color
        p.draw.rect(surface, color, adjusted_rect)
        
        # Draw text
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(midleft=(adjusted_rect.x + 10, adjusted_rect.y + adjusted_rect.height/2))
        surface.blit(text_surf, text_rect)
        
        return True  # Indicates the button was drawn
    
    def is_clicked(self, pos, y_offset=0):
        """Check if the button was clicked with scrolling offset."""
        adjusted_rect = p.Rect(
            self.rect.x, 
            self.rect.y - y_offset,
            self.rect.width,
            self.rect.height
        )
        return adjusted_rect.collidepoint(pos)
