"""
GameState package - contains the game logic and rule variations for Drawback Chess.
"""

# Import the state manager to make it available through the package
from GameState.state_manager import game_state_manager

# Don't directly import DrawbackBoard here to avoid circular imports
# Classes will be imported when needed by other modules

__all__ = ['game_state_manager']
