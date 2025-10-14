try:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
except:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui
import maya.cmds as cmds
from functools import partial
import importlib

from . import blendWeightHelperUtil as BlndWghtUtil
importlib.reload(BlndWghtUtil)


class BlendWeightHelper(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Blend Weight Helper")
        self.resize(340, 420)
        self.setMinimumWidth(340)

        self.current_weight = None
        self.last_selection = []

        layout = QtWidgets.QVBoxLayout(self)

        # === Weight Buttons ===
        layout.addWidget(QtWidgets.QLabel("SELECT VERTEX THEN CHOOSE WEIGHT VALUE"))
        weight_layout = QtWidgets.QHBoxLayout()
        for val in [0.0, 0.2, 0.5, 0.8, 1.0]:
            btn = QtWidgets.QPushButton(str(val))
            btn.setCheckable(True)
            btn.clicked.connect(partial(self.toggle_weight, val))
            weight_layout.addWidget(btn)
        layout.addLayout(weight_layout)
        self.weight_buttons = weight_layout

        # === Auto Weight ===
        layout.addWidget(QtWidgets.QLabel("AUTO WEIGHT (SELECT 3+ EDGE LOOP)"))
        auto_btn = QtWidgets.QPushButton("AUTO")
        auto_btn.clicked.connect(BlndWghtUtil.auto_weight)
        layout.addWidget(auto_btn)

        # === Maya Tool Shortcuts ===
        layout.addWidget(QtWidgets.QLabel("MAYA TOOL SHORTCUTS"))
        paint_btn = QtWidgets.QPushButton("OPEN PAINT SKIN WEIGHT TOOL")
        paint_btn.clicked.connect(BlndWghtUtil.open_paint_skin_weight_tool)
        layout.addWidget(paint_btn)

        # === Smooth Skin Editor View ===
        layout.addWidget(QtWidgets.QLabel("SMOOTH SKIN EDITOR VIEW (AUTO REFRESH)"))
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Vertex", "Joint", "Weight"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # === Buttons ===
        btn_row = QtWidgets.QHBoxLayout()
        reset_btn = QtWidgets.QPushButton("CLEAR SELECTED VERTEX")
        reset_btn.clicked.connect(BlndWghtUtil.reset_selected_vertices)
        btn_row.addWidget(reset_btn)

        self.apply_btn = QtWidgets.QPushButton("APPLY (No Weight Selected)")
        self.apply_btn.clicked.connect(self.apply_weight)
        btn_row.addWidget(self.apply_btn)
        layout.addLayout(btn_row)

        close_btn = QtWidgets.QPushButton("CLOSE")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        # === Timer for auto-refresh ===
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_selection_change)
        self.timer.start(1000)  # check every 1s

    # === Logic ===
    def toggle_weight(self, value):
        """Toggle selection of weight button."""
        self.current_weight = value
        for i in range(self.weight_buttons.count()):
            btn = self.weight_buttons.itemAt(i).widget()
            btn.setChecked(float(btn.text()) == value)
        self.apply_btn.setText(f"APPLY (Current: {value})")
        cmds.inViewMessage(amg=f"Selected Weight: <hl>{value}</hl>", pos="midCenter", fade=True)
        BlndWghtUtil.apply_weight(value)
        self.populate_smooth_skin_table()

    def apply_weight(self):
        """Apply current selected weight again."""
        if self.current_weight is None:
            cmds.warning("Please select a weight value first.")
            return
        BlndWghtUtil.apply_weight(self.current_weight)
        self.populate_smooth_skin_table()

    def check_selection_change(self):
        current = cmds.ls(selection=True, fl=True) or []
        if current != self.last_selection:
            self.last_selection = current
            self.populate_smooth_skin_table()

    def populate_smooth_skin_table(self):
        """Refresh weight table for all selected vertices."""
        data = BlndWghtUtil.get_vertex_weights_all()
        self.table.setRowCount(0)
        if not data:
            return
        for vtx, joint, value in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(vtx))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(joint))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(round(value, 3))))


def run():
    global ui
    try:
        ui.close()
    except:
        pass
    ptr = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = BlendWeightHelper(parent=ptr)
    ui.show()
