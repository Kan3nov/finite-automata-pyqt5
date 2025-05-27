import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsTextItem,
                             QVBoxLayout, QPushButton, QHBoxLayout, QInputDialog, QFileDialog,
                             QMessageBox, QWidget)
from PyQt5.QtGui import QPen, QBrush, QFont, QPolygonF, QPainterPath
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsItem
import math


class StateItem(QGraphicsItem):
    def __init__(self, name, x, y, click_callback=None, width=70, height=50):
        super().__init__()
        self.setPos(x, y)
        self.name = name
        self.width = width
        self.height = height
        self.click_callback = click_callback  # store callback
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.is_accept = False
        self.is_start = False
        self.transitions = {}  # Store transitions as symbol -> list of target state names

    def mousePressEvent(self, event):
        if self.click_callback:
            self.click_callback(self)  # notify parent window
        super().mousePressEvent(event)  # keep default behavior (dragging, selecting)

    def boundingRect(self):
        margin = 5
        return QRectF(-self.width / 2 - margin, -self.height / 2 - margin, self.width + 2 * margin, self.height + 2 * margin)

    def paint(self, painter, option, widget=None):
        rect = QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

        # Fill color based on state type
        if self.is_start and self.is_accept:
            brush = QBrush(Qt.darkCyan)
        elif self.is_start:
            brush = QBrush(Qt.green)
        elif self.is_accept:
            brush = QBrush(Qt.cyan)
        else:
            brush = QBrush(Qt.white)

        painter.setBrush(brush)
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)

        # Draw rounded rectangle
        painter.drawRoundedRect(rect, 15, 15)

        # Draw double border if accept state
        if self.is_accept:
            pen2 = QPen(Qt.black, 2)
            pen2.setStyle(Qt.DotLine)
            painter.setPen(pen2)
            inner_rect = rect.adjusted(6, 6, -6, -6)
            painter.drawRoundedRect(inner_rect, 15, 15)

        # Draw state name text centered
        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setPen(Qt.black)
        painter.drawText(rect, Qt.AlignCenter, self.name)

    def set_start(self, is_start=True):
        self.is_start = is_start
        self.update()

    def set_accept(self, is_accept=True):
        self.is_accept = is_accept
        self.update()

    def center(self):
        return self.scenePos()

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(QRectF(-self.width / 2, -self.height / 2, self.width, self.height), 15, 15)
        return path

    def get_border_point_towards(self, target_point):
        """
        Calculate point on border of the rounded rect closest towards target_point.
        Uses ellipse approximation for the rounded rect shape.
        """
        center = self.scenePos()
        dx = target_point.x() - center.x()
        dy = target_point.y() - center.y()
        if dx == 0 and dy == 0:
            return center

        angle = math.atan2(dy, dx)

        w = self.width / 2
        h = self.height / 2

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        denom = math.sqrt((cos_a ** 2) / (w ** 2) + (sin_a ** 2) / (h ** 2))
        x = (cos_a / denom)
        y = (sin_a / denom)

        point_on_border = QPointF(center.x() + x, center.y() + y)
        return point_on_border


class Automaton:
    def __init__(self, is_dfa=True):
        self.states = {}
        self.start_state = None
        self.accept_states = set()
        self.is_dfa = is_dfa

    def add_state(self, state):
        self.states[state.name] = state

    def set_start(self, state):
        # Clear previous start state if any
        if self.start_state and self.start_state != state.name:
            old_start = self.states.get(self.start_state)
            if old_start:
                old_start.set_start(False)

        self.start_state = state.name
        state.set_start(True)

    def set_accept(self, state):
        state.set_accept(True)
        self.accept_states.add(state.name)

    def add_transition(self, from_state, symbol, to_state):
        trans = from_state.transitions
        if symbol not in trans:
            trans[symbol] = []
        if to_state.name not in trans[symbol]:
            trans[symbol].append(to_state.name)

    def simulate(self, input_str):
        if not self.start_state:
            return False
        if self.is_dfa:
            current = self.start_state
            for char in input_str:
                state = self.states.get(current)
                if not state or char not in state.transitions:
                    return False
                current = state.transitions[char][0]
            return current in self.accept_states
        else:
            current_states = set([self.start_state])
            for char in input_str:
                next_states = set()
                for state_name in current_states:
                    state = self.states[state_name]
                    if char in state.transitions:
                        next_states.update(state.transitions[char])
                current_states = next_states
            return any(s in self.accept_states for s in current_states)


class AutomataWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finite Automata Builder (PyQt5)")
        self.setGeometry(100, 100, 1000, 700)
        self.automaton = Automaton(is_dfa=True)
        self.selected_state = None
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()

        font = QFont("Segoe UI", 10)
        buttons = {
            "Add State": self.add_state,
            "Set Start": self.set_start_state,
            "Set Accept": self.set_accept_state,
            "Add Transition": self.add_transition,
            "Simulate": self.simulate_input,
            "Save": self.save_automaton,
            "Load": self.load_automaton,
        }

        for label, func in buttons.items():
            btn = QPushButton(label)
            btn.setFont(font)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #5A9BD5;
                    color: white;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #4178BE;
                }
                QPushButton:pressed {
                    background-color: #2A5D9F;
                }
            """)
            btn.clicked.connect(func)
            btn_layout.addWidget(btn)

        layout.addWidget(self.view)
        layout.addLayout(btn_layout)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def add_state(self):
        name, ok = QInputDialog.getText(self, "State Name", "Enter state name:")
        if ok and name:
            if name in self.automaton.states:
                QMessageBox.warning(self, "Duplicate state", f"State '{name}' already exists.")
                return
            x, y = len(self.automaton.states) * 100 + 50, 150
            state = StateItem(name, x, y, click_callback=self.on_state_clicked)
            self.scene.addItem(state)
            self.automaton.add_state(state)

    def on_state_clicked(self, state):
        self.selected_state = state

    def set_start_state(self):
        if self.selected_state:
            self.automaton.set_start(self.selected_state)

    def set_accept_state(self):
        if self.selected_state:
            self.automaton.set_accept(self.selected_state)

    def add_transition(self):
        if not self.selected_state:
            QMessageBox.warning(self, "No state selected", "Please select a source state first.")
            return
        from_state = self.selected_state
        to_name, ok = QInputDialog.getText(self, "To State", "Enter destination state name:")
        if not ok or not to_name:
            return
        symbol, ok2 = QInputDialog.getText(self, "Symbol", "Enter transition symbol (single character):")
        if not ok2 or not symbol:
            return
        if len(symbol) != 1:
            QMessageBox.warning(self, "Invalid Symbol", "Transition symbol must be a single character.")
            return
        to_state = self.automaton.states.get(to_name)
        if not to_state:
            QMessageBox.warning(self, "Invalid State", f"Destination state '{to_name}' does not exist.")
            return

        try:
            self.automaton.add_transition(from_state, symbol, to_state)
            self.draw_arrow(from_state, to_state, symbol)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add transition: {e}")

    def simulate_input(self):
        input_str, ok = QInputDialog.getText(self, "Simulate", "Enter input string:")
        if ok:
            result = self.automaton.simulate(input_str)
            QMessageBox.information(self, "Result", "Accepted" if result else "Rejected")

    def save_automaton(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Automaton", "", "JSON Files (*.json)")
        if not path:
            return
        data = {
            "states": list(self.automaton.states.keys()),
            "start": self.automaton.start_state,
            "accept": list(self.automaton.accept_states),
            "transitions": {s.name: s.transitions for s in self.automaton.states.values()}
        }
        with open(path, 'w') as f:
            import json
            json.dump(data, f)

    def load_automaton(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Automaton", "", "JSON Files (*.json)")
        if not path:
            return
        with open(path, 'r') as f:
            import json
            data = json.load(f)
        self.scene.clear()
        self.automaton = Automaton(is_dfa=True)
        for i, name in enumerate(data["states"]):
            x, y = i * 100 + 50, 150
            state = StateItem(name, x, y, click_callback=self.on_state_clicked)
            self.scene.addItem(state)
            self.automaton.add_state(state)
        if data["start"]:
            self.automaton.set_start(self.automaton.states[data["start"]])
        for name in data["accept"]:
            self.automaton.set_accept(self.automaton.states[name])
        for from_state, trans in data["transitions"].items():
            from_obj = self.automaton.states.get(from_state)
            if not from_obj:
                continue
            for symbol, to_list in trans.items():
                for to_name in to_list:
                    to_obj = self.automaton.states.get(to_name)
                    if not to_obj:
                        continue
                    self.automaton.add_transition(from_obj, symbol, to_obj)
                    self.draw_arrow(from_obj, to_obj, symbol)

    def draw_arrow(self, from_state, to_state, symbol):
        start = from_state.get_border_point_towards(to_state.scenePos())
        end = to_state.get_border_point_towards(from_state.scenePos())

        line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line.setPen(QPen(Qt.black, 2))
        self.scene.addItem(line)

        self.draw_arrowhead(start, end)

        mid_x = (start.x() + end.x()) / 2
        mid_y = (start.y() + end.y()) / 2
        text = QGraphicsTextItem(symbol)
        text.setPos(mid_x + 5, mid_y + 5)
        self.scene.addItem(text)

    def draw_arrowhead(self, start, end):
        arrow_size = 10
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())

        p1 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi / 6),
            end.y() - arrow_size * math.sin(angle - math.pi / 6)
        )
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi / 6),
            end.y() - arrow_size * math.sin(angle + math.pi / 6)
        )
        arrow_head = QPolygonF([end, p1, p2])
        self.scene.addPolygon(arrow_head, QPen(Qt.black), QBrush(Qt.black))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutomataWindow()
    window.show()
    sys.exit(app.exec_())
