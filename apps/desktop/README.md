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
   git clone https://github.com/zDox/ConlyseV4.git
   cd ConlyseV4
   ```

2. **Install dependencies**:
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```
   *Note: Ensure you have access to the `conflict-interface` repository as it is a required dependency.*

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
  - `api/`: HTTP client for talking to the Conlyse backend (`services/api`).
  - `widgets/`: Reusable UI components and the custom Dock system.
  - `utils/`: Common helpers and enumerations.
- `assets/`: Icons, styles, and other static resources.
- `app_data/`: Local configuration and keybindings.

## Backend API configuration

The desktop client can connect to the Conlyse backend (`services/api`) using a configurable base URL.

- Default base URL (development): `http://localhost:8000/api/v1`
- These options are stored in `app_data/main_config.json` under the `api` key:
  - `api.base_url`: Base URL for the Conlyse API.
  - `api.timeout_seconds`: Request timeout used by the desktop HTTP client.

You can change these values via the **Settings → API** section in the application UI.
---
Developed by **zDox** and **Niknam3**.
