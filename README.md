# Watchdogs 2D Prototype

This repository contains a small top-down prototype inspired by the hacking gameplay of *Watch Dogs*. The player can move around a simple arena, interact with doors and NPCs, and trigger contextual hacking actions on the nearest object.

## Features

- Keyboard movement (WASD or arrow keys) for the player character.
- Hackable objects with contextual actions:
  - **Doors** can be opened/closed and locked/unlocked.
  - **NPCs** can be distracted with their phone.
- The closest hackable object within range is highlighted and its available actions are listed on the HUD.
- Status messages briefly confirm the outcome of each action.

## Running the prototype

```bash
python main.py
```

The prototype requires [Pygame](https://www.pygame.org/) to be installed:

```bash
python -m pip install pygame
```

Press `Esc` to exit the prototype.
