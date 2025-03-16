# Game State Management System

This module provides a centralized state management system for the Drawback Chess game. It follows a unidirectional data flow pattern similar to Redux, making game state changes predictable and easy to track.

## Key Components

### GameState

The `GameState` class encapsulates all state variables related to the game:

- Game state (game over, winner, selected square)
- Display state (board flipped)
- AI state (AI players, search status, etc.)

### GameStateManager

The `GameStateManager` class provides a clean interface for state updates and includes:

- History tracking for state changes (undo capability)
- Event subscription system for reactive UI updates
- Validation to ensure state consistency

## How to Use the State Manager

### Importing the State Manager

```python
# Import the centralized state manager
from GameState import game_state_manager

# Access the current state
state = game_state_manager.state
```

### Reading State

```python
# Get the current state
state = game_state_manager.state

# Check if the game is over
if state.game_over:
    print(f"Game over! Winner: {state.winner_color}")

# Check if it's AI's turn to move
if state.is_ai_turn(board):
    # Start AI search
    ...
```

### Updating State

Always use the `update` method to modify state variables:

```python
# Update a single state variable
game_state_manager.update(game_over=True)

# Update multiple state variables in one atomic operation
game_state_manager.update(
    game_over=True,
    winner_color=chess.WHITE,
    end_message="Checkmate!"
)
```

### Subscribing to State Changes

You can subscribe to state changes to update the UI reactively:

```python
def update_game_over_display(value):
    # Update UI when game_over state changes
    if value:
        display_winner_message()
    else:
        hide_winner_message()

# Subscribe to the 'game_over' state change
game_state_manager.state.subscribe('game_over', update_game_over_display)
```

### Undo/Redo Operations

The state manager tracks history, allowing undo operations:

```python
# Undo the last state change
if game_state_manager.undo():
    print("Undid last action")
else:
    print("Nothing to undo")
```

### Resetting State

Reset the game state to initial values:

```python
# Reset all state variables to default
game_state_manager.reset()
```

## Benefits of the State Manager

1. **Single Source of Truth**: All game state is centralized in one place
2. **Predictable Updates**: State changes only happen through explicit update calls
3. **State History**: Track and undo state changes
4. **Debugging**: Easier to debug state changes by setting breakpoints in the update method
5. **Event System**: React to state changes through subscriptions

## Best Practices

1. Always use the `update` method to change state
2. Group related state changes in a single update call
3. Keep UI components subscribed to relevant state variables
4. Use the state manager to track game-level state only (not board-specific state)
5. Consider performance implications when subscribing to frequently changing state variables 