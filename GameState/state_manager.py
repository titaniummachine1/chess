"""
Game State Manager
Centralizes all game state variables and provides a clean interface for state updates.
Replaces the use of global variables with proper OOP encapsulation.
"""
import chess
from typing import Optional, Dict, List, Any, Set, Callable
import copy

class GameState:
    """
    Represents the complete state of the game.
    A single source of truth for all game state information.
    """
    def __init__(self):
        # Game state
        self.game_over = False
        self.winner_color = None
        self.end_message = None
        self.selected_square = None
        
        # Display state
        self.flipped_board = False
        
        # AI state
        self.ai_move_cooldown = 0
        self.search_in_progress = False
        self.white_ai = False
        self.black_ai = False
        self.ai_depth = 7
        self.time_limit = 10  # seconds
        self.use_smart_time_management = True
        
        # Event subscribers
        self._subscribers: Dict[str, List[Callable]] = {}
        
    def update(self, **kwargs) -> None:
        """
        Update state variables in a controlled way.
        Triggers all appropriate event subscribers.
        
        Args:
            **kwargs: Key-value pairs of state variables to update
        """
        changed_keys = set()
        
        # Update attributes that exist on the class
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                setattr(self, key, value)
                
                # Only record as changed if the value actually changed
                if old_value != value:
                    changed_keys.add(key)
        
        # Notify subscribers of changes
        self._notify_subscribers(changed_keys)
    
    def subscribe(self, event_key: str, callback: Callable) -> None:
        """
        Subscribe to state changes on a specific key.
        
        Args:
            event_key: The state variable to track
            callback: Function to call when the variable changes
        """
        if event_key not in self._subscribers:
            self._subscribers[event_key] = []
        self._subscribers[event_key].append(callback)
    
    def _notify_subscribers(self, changed_keys: Set[str]) -> None:
        """
        Notify all subscribers of state changes.
        
        Args:
            changed_keys: Set of keys that were changed
        """
        for key in changed_keys:
            if key in self._subscribers:
                value = getattr(self, key)
                for callback in self._subscribers[key]:
                    callback(value)
    
    def is_ai_turn(self, board) -> bool:
        """
        Determine if it's an AI's turn to move.
        
        Args:
            board: The current board state
            
        Returns:
            True if an AI should move now, False otherwise
        """
        return (self.white_ai and board.turn == chess.WHITE) or \
               (self.black_ai and board.turn == chess.BLACK)


class GameStateManager:
    """
    Manager class that provides an interface to the game state.
    Maintains state history and allows for undo operations.
    """
    def __init__(self):
        self.state = GameState()
        self._history: List[GameState] = []
        
    def update(self, **kwargs) -> None:
        """
        Update state variables and record history.
        
        Args:
            **kwargs: Key-value pairs of state variables to update
        """
        # Save current state to history
        self._history.append(copy.deepcopy(self.state))
        
        # Update the state
        self.state.update(**kwargs)
    
    def undo(self) -> bool:
        """
        Restore the previous state from history.
        
        Returns:
            True if undo was successful, False if no history
        """
        if not self._history:
            return False
            
        self.state = self._history.pop()
        return True
    
    def reset(self) -> None:
        """Reset the game state to initial values and clear history."""
        self.state = GameState()
        self._history.clear()

# Create a singleton instance to be imported by other modules
game_state_manager = GameStateManager() 