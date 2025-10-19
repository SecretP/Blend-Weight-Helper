try:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
except ImportError:
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
        super(BlendWeightHelper, self).__init__(parent)
        self.setWindowTitle("Blend Weight Helper v2.0 (Capsule)")
        self.resize(340, 480) # Increased height
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

        # === Capsule Auto Weight ===
        layout.addWidget(QtWidgets.QLabel("AUTO CAPSULE WEIGHT"))
        
        # --- NEW CAPSULE WIDGETS ---
        capsule_layout = QtWidgets.QHBoxLayout()
        capsule_layout.addWidget(QtWidgets.QLabel("Capsule Radius:"))
        self.radius_spinbox = QtWidgets.QDoubleSpinBox()
        self.radius_spinbox.setRange(0.01, 100.0)
        self.radius_spinbox.setSingleStep(0.1)
        self.radius_spinbox.setValue(1.0)
        capsule_layout.addWidget(self.radius_spinbox)
        layout.addLayout(capsule_layout)
        
        # --- UPDATED LABEL ---
        layout.addWidget(QtWidgets.QLabel("In Paint Tool, select 1 influence joint, then click"))
        auto_btn = QtWidgets.QPushButton("AUTO CAPSULE WEIGHT")
        auto_btn.clicked.connect(self.run_auto_capsule_weight)
        layout.addWidget(auto_btn)
        # --------------------------

        # === Maya Tool Shortcuts ===
        layout.addWidget(QtWidgets.QLabel("MAYA TOOL SHORTCUT"))
        paint_btn = QtWidgets.QPushButton("OPEN PAINT SKIN WEIGHT TOOL")
        paint_btn.clicked.connect(BlndWghtUtil.open_paint_skin_weight_tool)
        layout.addWidget(paint_btn)

        # === Smooth Skin Editor View ===
        layout.addWidget(QtWidgets.QLabel("SMOOTH SKIN EDITOR VIEW (DOUBLE-CLICK TO EDIT)"))
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Vertex", "Joint", "Weight"])
        self.table.itemChanged.connect(self.on_weight_edited)
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
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_selection_change)
        self.timer.start(500)
        self.check_selection_change()

    def apply_weight_from_button(self, value):
        BlndWghtUtil.apply_weight(value)
        self.populate_smooth_skin_table()

    def run_auto_capsule_weight(self):
        radius = self.radius_spinbox.value()
        BlndWghtUtil.auto_capsule_weight(radius) # Call new function with radius
        self.populate_smooth_skin_table()

    def check_selection_change(self):
        current = cmds.ls(selection=True, fl=True) or []
        if current != self.last_selection:
            self.last_selection = current
            self.populate_smooth_skin_table()

    def on_weight_edited(self, item):
        if item.column() != 2: return
        try:
            new_weight = float(item.text())
        except (ValueError, TypeError):
            cmds.warning("Invalid weight value."); self.populate_smooth_skin_table(); return
        row, vtx_item, joint_item = item.row(), self.table.item(item.row(), 0), self.table.item(item.row(), 1)
        if vtx_item and joint_item:
            BlndWghtUtil.set_specific_vertex_weight(vtx_item.text(), joint_item.text(), new_weight)
            QtCore.QTimer.singleShot(50, self.populate_smooth_skin_table)

    def populate_smooth_skin_table(self):
        self.table.blockSignals(True)
        try:
            data = BlndWghtUtil.get_vertex_weights_all()
            self.table.setRowCount(0)
            if not data: return
            self.table.setRowCount(len(data))
            for row, (vtx, joint, value) in enumerate(data):
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(vtx))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(joint))
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{value:.3f}"))
        finally:
            self.table.blockSignals(False)

def run():
    global ui
    try:
        ui.close(); ui.deleteLater()
    except: pass
    maya_main_window = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = BlendWeightHelper(parent=maya_main_window)
    ui.show()