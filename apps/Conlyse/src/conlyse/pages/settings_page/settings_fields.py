from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal

class SettingsField(QWidget):
    """Base class for a settings field with a label and a widget."""
    value_changed = Signal(object)

    def __init__(self, label_text: str, description: str = "", parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 4, 0, 4)

        self.label_layout = QHBoxLayout()
        self.label = QLabel(label_text)
        self.label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.label_layout.addWidget(self.label)

        if description:
            self.label.setToolTip(description)

        self.layout.addLayout(self.label_layout)
        self.layout.addItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.widget = self._create_widget()
        if self.widget:
            self.layout.addWidget(self.widget)

    def _create_widget(self) -> QWidget:
        return None

    def get_value(self):
        raise NotImplementedError

    def set_value(self, value):
        raise NotImplementedError

from PySide6.QtWidgets import QCheckBox

class ToggleField(SettingsField):
    def _create_widget(self):
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(lambda state: self.value_changed.emit(state == Qt.CheckState.Checked.value))
        return self.checkbox

    def get_value(self):
        return self.checkbox.isChecked()

    def set_value(self, value):
        self.checkbox.setChecked(bool(value))

from PySide6.QtWidgets import QSlider

class SliderField(SettingsField):
    def __init__(self, label_text: str, min_val: int, max_val: int, description: str = "", parent=None):
        self.min_val = min_val
        self.max_val = max_val
        super().__init__(label_text, description, parent)

    def _create_widget(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.value_label = QLabel()
        self.value_label.setFixedWidth(30)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.min_val, self.max_val)
        self.slider.setFixedWidth(150)
        
        def on_value_changed(val):
            self.value_label.setText(str(val))
            self.value_changed.emit(val)
            
        self.slider.valueChanged.connect(on_value_changed)
        
        layout.addWidget(self.value_label)
        layout.addWidget(self.slider)
        return container

    def get_value(self):
        return self.slider.value()

    def set_value(self, value):
        self.slider.setValue(int(value))
        self.value_label.setText(str(value))

from PySide6.QtWidgets import QComboBox

class ComboField(SettingsField):
    def __init__(self, label_text: str, items: list[str], description: str = "", parent=None):
        self.items = items
        super().__init__(label_text, description, parent)

    def _create_widget(self):
        self.combo = QComboBox()
        self.combo.addItems(self.items)
        self.combo.currentTextChanged.connect(self.value_changed.emit)
        return self.combo

    def get_value(self):
        return self.combo.currentText()

    def set_value(self, value):
        index = self.combo.findText(str(value))
        if index >= 0:
            self.combo.setCurrentIndex(index)

from PySide6.QtCore import Qt, Signal, QKeyCombination
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QPushButton, QHBoxLayout
from conlyse.widgets.mui.icon_button import CIconButton

class KeybindingField(SettingsField):
    def _create_widget(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.button = QPushButton("Press a key...")
        self.button.setFixedWidth(150)
        self.button.setCheckable(True)
        self.button.clicked.connect(self._on_clicked)
        self.button.installEventFilter(self)

        self.clear_button = CIconButton("fa5s.times", color="error", size=20)
        self.clear_button.setToolTip("Clear keybinding")
        self.clear_button.clicked.connect(self._on_clear_clicked)

        layout.addWidget(self.button)
        layout.addWidget(self.clear_button)

        self._current_sequence = ""
        return container

    def _on_clicked(self):
        if self.button.isChecked():
            self.button.setText("...")
        else:
            self.button.setText(self._current_sequence or "None")

    def _on_clear_clicked(self):
        self._current_sequence = ""
        self.button.setText("None")
        self.button.setChecked(False)
        self.value_changed.emit("")

    def eventFilter(self, obj, event):
        if obj == self.button and self.button.isChecked():
            if event.type() == event.Type.KeyPress:
                key = event.key()
                if key == Qt.Key.Key_Escape:
                    self.button.setChecked(False)
                    self.button.setText(self._current_sequence or "None")
                    return True
                
                modifiers = event.modifiers()
                
                # If the key is one of the modifier keys, don't finish yet
                is_modifier = key in [
                    Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, 
                    Qt.Key.Key_Meta, Qt.Key.Key_AltGr
                ]
                
                if not is_modifier:
                    # Create a QKeyCombination from modifiers and key
                    key_comb = QKeyCombination(modifiers, Qt.Key(key))
                    sequence = QKeySequence(key_comb).toString()
                    self._current_sequence = sequence
                    self.button.setText(sequence)
                    self.button.setChecked(False)
                    self.value_changed.emit(sequence)
                else:
                    # Update button text to show modifiers being held
                    sequence = QKeySequence(modifiers).toString()
                    if sequence:
                        self.button.setText(sequence + "+...")
                    else:
                        self.button.setText("...")
                return True

            elif event.type() == event.Type.KeyRelease:
                modifiers = event.modifiers()
                sequence = QKeySequence(modifiers).toString()
                if sequence:
                    self.button.setText(sequence + "+...")
                else:
                    self.button.setText("...")
                return True

        return super().eventFilter(obj, event)

    def get_value(self):
        return self._current_sequence

    def set_value(self, value):
        self._current_sequence = str(value)
        self.button.setText(self._current_sequence or "None")
