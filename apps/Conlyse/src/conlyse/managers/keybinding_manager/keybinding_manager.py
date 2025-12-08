from __future__ import annotations

from typing import Any
from typing import Callable
from typing import TYPE_CHECKING

from PyQt6.QtCore import QKeyCombination
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import QWidget

from conlyse.logger import get_logger
from conlyse.managers.keybinding_manager.key_action import KeyAction

if TYPE_CHECKING:
    from conlyse.app import App

logger = get_logger()


def sequence_str_to_combination(seq_str: str) -> QKeyCombination:
    """
    Safely converts a QKeySequence to a single QKeyCombination.
    Returns an empty QKeyCombination if the sequence has no keys.
    """
    seq = QKeySequence(seq_str)
    if seq.isEmpty():
        return QKeyCombination()  # null/empty

    # Take the first key in the sequence
    first_int = seq[0]  # QKeySequence behaves like a list of int key codes
    kc = QKeyCombination(first_int)
    return kc

class KeybindingManager:
    def __init__(self, app: App):
        self.app = app
        self.keybindings: dict[KeyAction, QKeyCombination] = {}
        self.callbacks: dict[KeyAction, Callable[[], Any]] = {}
        self.shortcuts: dict[KeyAction, QShortcut] = {}

        self.load_keybindings()

    def load_keybindings(self):
        """Loads keybindings from the config manager."""
        keybinding_config = self.app.config_manager.keybindings
        for action_str, key_combination in keybinding_config.get("actions").items():
            try:
                action = KeyAction(action_str)
                self.set_keybinding(action, key_combination)
            except KeyError:
                logger.warning(f"Unknown key action '{action_str}' in keybindings config.")

    def set_keybinding(self, action: KeyAction, key_combination: str):
        """Sets a keybinding for the given action."""
        key_sequence =  sequence_str_to_combination(key_combination)
        self.keybindings[action] = key_sequence
        if action in self.callbacks:
            if action in self.shortcuts:
                self.shortcuts[action].deleteLater()
            shortcut = QShortcut(key_sequence, self.app.main_window)
            shortcut.activated.connect(self.callbacks[action])
            self.shortcuts[action] = shortcut

    def remove_keybinding(self, action):
        """Removes the keybinding for the given action."""
        if action in self.keybindings:
            self.shortcuts[action].deleteLater()

            del self.shortcuts[action]
            del self.keybindings[action]

    def has_keybinding(self, action):
        """Checks if a keybinding exists for the given action."""
        return action in self.keybindings

    def get_keybinding(self, action: KeyAction) -> QKeyCombination | None:
        """Gets the keybinding for the given action."""
        return self.keybindings.get(action, None)

    def get_key(self, action: KeyAction) -> Qt.Key | None:
        """Gets the Qt.Key for the given action's keybinding."""
        key_combination = self.get_keybinding(action)
        if key_combination:
            return key_combination.key()
        return None

    def register_action(self, action: KeyAction, function: Callable, widget: QWidget=None):
        """Registers a callback function for the given action."""
        self.callbacks[action] = function
        if self.has_keybinding(action):
            key_sequence = self.keybindings[action]
            if widget is None:
                widget = self.app.main_window
            shortcut = QShortcut(QKeySequence(key_sequence), widget)
            shortcut.activated.connect(function)
            self.shortcuts[action] = shortcut

    def unregister_action(self, action):
        """Unregisters the callback function for the given action."""
        if action in self.callbacks:
            del self.callbacks[action]
        if action in self.shortcuts:
            self.shortcuts[action].deleteLater()
            del self.shortcuts[action]