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
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.min_val, self.max_val)
        self.slider.setFixedWidth(150)
        self.slider.valueChanged.connect(self.value_changed.emit)
        return self.slider

    def get_value(self):
        return self.slider.value()

    def set_value(self, value):
        self.slider.setValue(int(value))

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
from PySide6.QtWidgets import QPushButton

class KeybindingField(SettingsField):
    def _create_widget(self):
        self.button = QPushButton("Press a key...")
        self.button.setFixedWidth(150)
        self.button.setCheckable(True)
        self.button.clicked.connect(self._on_clicked)
        self.button.installEventFilter(self)
        self._current_sequence = ""
        return self.button

    def _on_clicked(self):
        if self.button.isChecked():
            self.button.setText("...")
        else:
            self.button.setText(self._current_sequence or "None")

    def eventFilter(self, obj, event):
        if obj == self.button and self.button.isChecked():
            if event.type() == event.Type.KeyPress:
                key = event.key()
                if key == Qt.Key.Key_Escape:
                    self.button.setChecked(False)
                    self.button.setText(self._current_sequence or "None")
                    return True
                
                modifiers = event.modifiers()
                # Create a QKeyCombination from modifiers and key
                key_comb = QKeyCombination(modifiers, Qt.Key(key))
                sequence = QKeySequence(key_comb).toString()
                self._current_sequence = sequence
                self.button.setText(sequence)
                self.button.setChecked(False)
                self.value_changed.emit(sequence)
                return True
        return super().eventFilter(obj, event)

    def get_value(self):
        return self._current_sequence

    def set_value(self, value):
        self._current_sequence = str(value)
        self.button.setText(self._current_sequence or "None")
