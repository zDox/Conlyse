# Conlyse

Conlyse is a high-performance, interactive replay analytics tool for **Conflict of Nations**. Built with Python, PySide6, and OpenGL, it provides a comprehensive suite for analyzing game replays with a smooth, modern interface.

## Features

- **Interactive Tactical Map**: High-performance OpenGL-based map rendering with smooth zoom and pan.
- **Multiple Map Views**: Switch between Political, Terrain, and Resource views to gain different strategic insights.
- **Comprehensive Data Visualization**:
  - **Player List**: Detailed statistics and status for all nations in the game.
  - **Province & Army Tracking**: Monitor province ownership and military movements.
- **Advanced Playback Controls**:
  - Precision timeline for jumping to specific moments in the game.
  - Variable simulation rates for fast-forwarding or detailed analysis.
- **Docking System**: Customizable UI with dockable panels for Army Info, City Lists, Game Events, and more.
- **Themed Interface**: Modern Dark/Light mode support with custom QSS styling.

## Prerequisites

- **Python 3.12**
- **OpenGL 3.3+** support

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/zDox/ConflictInterface.git
   cd ConflictInterface
   ```

2. **Install dependencies**:
   It is recommended to use a virtual environment.
   ```bash
   cd apps/desktop
   pip install -e .
   ```
   *Note: This will automatically install the `conflict-interface` library as a dependency.*

## 🏃 Usage

Run the application using:
```bash
python -m conlyse
```

### Keybindings
- `D`: Toggle Navigation Drawer
- `P`: Toggle Performance Window
- `F11`: Toggle Fullscreen

## Project Structure

- `src/conlyse/`: Core application logic.
  - `managers/`: State and resource management (Assets, Config, Events, Replays, Styles).
  - `pages/`: Main application views (Map, Replay List, Player List, Settings).
  - `widgets/`: Reusable UI components and the custom Dock system.
  - `utils/`: Common helpers and enumerations.
- `assets/`: Icons, styles, and other static resources.
- `app_data/`: Local configuration and keybindings.
---
Developed by **zDox** and **Niknam3**.
