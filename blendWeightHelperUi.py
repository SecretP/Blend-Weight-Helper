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

        self.last_selection = []

        layout = QtWidgets.QVBoxLayout(self)

        # === Weight Buttons ===
        layout.addWidget(QtWidgets.QLabel("SELECT VERTEX THEN CLICK WEIGHT VALUE"))
        weight_layout = QtWidgets.QHBoxLayout()
        for val in [0.0, 0.2, 0.5, 0.8, 1.0]:
            btn = QtWidgets.QPushButton(str(val))
            btn.clicked.connect(partial(self.apply_weight_from_button, val))
            weight_layout.addWidget(btn)
        layout.addLayout(weight_layout)
        self.weight_buttons = weight_layout

        # === Auto Weight ===
        layout.addWidget(QtWidgets.QLabel("AUTO WEIGHT (SELECT 3 EDGE LOOPS)"))
        auto_btn = QtWidgets.QPushButton("AUTO GRADIENT WEIGHT")
        auto_btn.clicked.connect(self.run_auto_weight)
        layout.addWidget(auto_btn)

        # === Maya Tool Shortcuts ===
        layout.addWidget(QtWidgets.QLabel("MAYA TOOL SHORTCUTS"))
        paint_btn = QtWidgets.QPushButton("OPEN PAINT SKIN WEIGHT TOOL")
        paint_btn.clicked.connect(BlndWghtUtil.open_paint_skin_weight_tool)
        layout.addWidget(paint_btn)

        # === Smooth Skin Editor View ===
        layout.addWidget(QtWidgets.QLabel("SMOOTH SKIN EDITOR VIEW (DOUBLE-CLICK TO EDIT)"))
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Vertex", "Joint", "Weight"])
        self.table.itemChanged.connect(self.on_weight_edited) # Connect signal for editing
        layout.addWidget(self.table)

        # === Buttons ===
        btn_row = QtWidgets.QHBoxLayout()
        reset_btn = QtWidgets.QPushButton("CLEAR SELECTED VERTEX")
        reset_btn.clicked.connect(BlndWghtUtil.reset_selected_vertices)
        btn_row.addWidget(reset_btn)

        close_btn = QtWidgets.QPushButton("CLOSE")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        
        # === Timer for auto-refresh ===
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_selection_change)
        self.timer.start(1000)  # check every 1s
        
        self.check_selection_change() # Initial population

    # === Logic ===
    def apply_weight_from_button(self, value):
        """Apply weight when a number button is clicked."""
        cmds.inViewMessage(amg=f"Applying Weight: <hl>{value}</hl>", pos="midCenter", fade=True)
        BlndWghtUtil.apply_weight(value)
        self.populate_smooth_skin_table()

    def run_auto_weight(self):
        """Wrapper for the auto weight utility."""
        BlndWghtUtil.auto_weight()
        self.populate_smooth_skin_table()
        
    def check_selection_change(self):
        current = cmds.ls(selection=True, fl=True) or []
        if current != self.last_selection:
            self.last_selection = current
            self.populate_smooth_skin_table()

    def on_weight_edited(self, item):
        """Called when a user edits a cell in the weight column."""
        if item.column() == 2: # Only trigger for the 'Weight' column
            try:
                new_weight = float(item.text())
            except ValueError:
                cmds.warning("Invalid weight value. Please enter a number.")
                self.populate_smooth_skin_table() # Revert to original value
                return
            
            row = item.row()
            vtx_item = self.table.item(row, 0)
            joint_item = self.table.item(row, 1)
            
            if vtx_item and joint_item:
                vertex = vtx_item.text()
                joint = joint_item.text()
                BlndWghtUtil.set_specific_vertex_weight(vertex, joint, new_weight)
                
                # A small delay before refreshing to ensure Maya updates
                QtCore.QTimer.singleShot(50, self.populate_smooth_skin_table)

    def populate_smooth_skin_table(self):
        """Refresh weight table for all selected vertices."""
        self.table.blockSignals(True) # Block signals to prevent edit triggers
        try:
            data = BlndWghtUtil.get_vertex_weights_all()
            self.table.setRowCount(0)
            if not data:
                return

            self.table.setRowCount(len(data))
            for row, (vtx, joint, value) in enumerate(data):
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(vtx))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(joint))
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{value:.3f}"))

        finally:
            self.table.blockSignals(False) # Re-enable signals


def run():
    global ui
    try:
        ui.close()
        ui.deleteLater()
    except:
        pass
    
    ptr = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = BlendWeightHelper(parent=ptr)
    ui.show()