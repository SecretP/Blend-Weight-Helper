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

class WeightTableWidget(QtWidgets.QTableWidget):
    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            selected_items = self.selectedItems()
            weight_items = [item for item in selected_items if item.column() == 2]
            if len(weight_items) > 1:
                self.batch_edit_weights(weight_items)
                return
        super(WeightTableWidget, self).keyPressEvent(event)

    def batch_edit_weights(self, items):
        num_items = len(items); current_value = float(items[0].text())
        result = cmds.promptDialog(title='Batch Edit Weights', message=f'Enter New Weight for {num_items} Items:', text=str(current_value), button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel')
        if result == 'OK':
            try:
                new_weight = float(cmds.promptDialog(query=True, text=True))
                weight_update_data = []
                for item in items:
                    row, vtx_item, joint_item = item.row(), self.item(item.row(), 0), self.item(item.row(), 1)
                    if vtx_item and joint_item:
                        weight_update_data.append((vtx_item.text(), joint_item.text(), new_weight))
                if weight_update_data:
                    BlndWghtUtil.set_multiple_vertex_weights(weight_update_data)
                    self.parent().populate_smooth_skin_table()
            except (ValueError, TypeError): cmds.warning("Invalid number entered.")

class BlendWeightHelper(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BlendWeightHelper, self).__init__(parent)
        self.setWindowTitle("Blend Weight Helper (Dual Mode)")
        self.resize(340, 600)
        self.setMinimumWidth(340)

        self.last_selection = []
        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel("SELECT VERTEX THEN CLICK WEIGHT VALUE"))
        weight_layout = QtWidgets.QHBoxLayout()
        for val in [0.0, 0.2, 0.5, 0.8, 1.0]:
            btn = QtWidgets.QPushButton(str(val))
            btn.clicked.connect(partial(self.apply_weight_from_button, val))
            weight_layout.addWidget(btn)
        layout.addLayout(weight_layout)

        auto_blend_group = QtWidgets.QGroupBox("Auto Blend Methods")
        auto_blend_layout = QtWidgets.QVBoxLayout()

        # --- Method 1: Localized Capsule ---
        auto_blend_layout.addWidget(QtWidgets.QLabel("<b>1. Localized Capsule Blend (Detailed)</b>"))
        capsule_options_layout = QtWidgets.QGridLayout()
        capsule_options_layout.addWidget(QtWidgets.QLabel("Capsule Radius:"), 0, 0)
        self.radius_spinbox = QtWidgets.QDoubleSpinBox()
        self.radius_spinbox.setRange(0.01, 100.0); self.radius_spinbox.setSingleStep(0.1); self.radius_spinbox.setValue(1.5)
        capsule_options_layout.addWidget(self.radius_spinbox, 0, 1)
        capsule_options_layout.addWidget(QtWidgets.QLabel("Blend Falloff:"), 1, 0)
        self.falloff_spinbox = QtWidgets.QDoubleSpinBox()
        self.falloff_spinbox.setRange(0.1, 5.0); self.falloff_spinbox.setSingleStep(0.1); self.falloff_spinbox.setValue(1.0)
        capsule_options_layout.addWidget(self.falloff_spinbox, 1, 1)
        auto_blend_layout.addLayout(capsule_options_layout)
        auto_blend_layout.addWidget(QtWidgets.QLabel("Select vertices, then in Paint Tool, select a joint:"))
        auto_capsule_btn = QtWidgets.QPushButton("APPLY LOCALIZED CAPSULE")
        auto_capsule_btn.clicked.connect(self.run_localized_capsule)
        auto_blend_layout.addWidget(auto_capsule_btn)
        
        # --- Method 2: Simple Hierarchy ---
        auto_blend_layout.addWidget(QtWidgets.QLabel("<b>2. 5-Step Hierarchy Blend (Simple)</b>"))
        auto_blend_layout.addWidget(QtWidgets.QLabel("In Paint Tool, select 1 central joint:"))
        auto_hierarchy_btn = QtWidgets.QPushButton("APPLY 5-STEP HIERARCHY")
        auto_hierarchy_btn.clicked.connect(self.run_hierarchy_blend)
        auto_blend_layout.addWidget(auto_hierarchy_btn)

        auto_blend_group.setLayout(auto_blend_layout)
        layout.addWidget(auto_blend_group)

        layout.addWidget(QtWidgets.QLabel("MAYA TOOL SHORTCUT"))
        paint_btn = QtWidgets.QPushButton("OPEN PAINT SKIN WEIGHT TOOL")
        paint_btn.clicked.connect(BlndWghtUtil.open_paint_skin_weight_tool)
        layout.addWidget(paint_btn)

        layout.addWidget(QtWidgets.QLabel("SMOOTH SKIN EDITOR VIEW (MULTI-SELECT + PRESS ENTER)"))
        self.table = WeightTableWidget(parent=self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Vertex", "Joint", "Weight"])
        self.table.itemChanged.connect(self.on_weight_edited)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.table)

        btn_row = QtWidgets.QHBoxLayout()
        undo_btn = QtWidgets.QPushButton("UNDO LAST")
        undo_btn.clicked.connect(BlndWghtUtil.undo_last_action)
        btn_row.addWidget(undo_btn)
        reset_btn = QtWidgets.QPushButton("CLEAR SELECTION")
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

    def run_localized_capsule(self):
        radius = self.radius_spinbox.value()
        falloff = self.falloff_spinbox.value()
        BlndWghtUtil.apply_localized_capsule_blend(radius, falloff)
        self.populate_smooth_skin_table()

    def run_hierarchy_blend(self):
        BlndWghtUtil.apply_hierarchy_blend()
        self.populate_smooth_skin_table()

    def apply_weight_from_button(self, value):
        BlndWghtUtil.apply_weight(value); self.populate_smooth_skin_table()
    def check_selection_change(self):
        current = cmds.ls(selection=True, fl=True) or []
        if current != self.last_selection: self.last_selection = current; self.populate_smooth_skin_table()
    def on_weight_edited(self, item):
        if item.column() != 2 or len(self.table.selectedItems()) > 1: return
        try: new_weight = float(item.text())
        except (ValueError, TypeError): cmds.warning("Invalid weight value."); self.populate_smooth_skin_table(); return
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
        finally: self.table.blockSignals(False)

def run():
    global ui
    try: ui.close(); ui.deleteLater()
    except: pass
    maya_main_window = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = BlendWeightHelper(parent=maya_main_window)
    ui.show()