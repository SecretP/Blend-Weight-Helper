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

        self.setWindowTitle('Blend Weight Helper')
        self.resize(300, 300)

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.current_weight = None


        self.Label = QtWidgets.QLabel("PLEASE SELECT VERTEX THEN CHOOSE WEIGHT VALUE")
        self.mainLayout.addWidget(self.Label)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        for val in [0.2, 0.5, 0.8]:
            button = QtWidgets.QPushButton(str(val))
            button.clicked.connect(partial(self.set_weight, val))
            self.buttonLayout.addWidget(button)
        self.mainLayout.addLayout(self.buttonLayout)

        self.buttonShowVtx = QtWidgets.QPushButton("DISPLAY SELECTED VERTEX LISTS")
        self.buttonShowVtx.clicked.connect(BlndWghtUtil.display_selected_vertices)
        self.mainLayout.addWidget(self.buttonShowVtx)

        self.buttonShowValue = QtWidgets.QPushButton("DISPLAY WEIGHT VALUE BY LIST")
        self.buttonShowValue.clicked.connect(BlndWghtUtil.display_weight_values)
        self.mainLayout.addWidget(self.buttonShowValue)

        self.mainLayout.addWidget(QtWidgets.QLabel("AUTO WEIGHT\nSELECT 3 OR MORE EDGE LOOP"))
        self.buttonAuto = QtWidgets.QPushButton("AUTO")
        self.buttonAuto.clicked.connect(BlndWghtUtil.auto_weight)
        self.mainLayout.addWidget(self.buttonAuto)

        self.buttonApply = QtWidgets.QPushButton("APPLY")
        self.buttonApply.clicked.connect(self.apply_weight)
        self.mainLayout.addWidget(self.buttonApply)

        self.buttonClose = QtWidgets.QPushButton("CLOSE")
        self.buttonClose.clicked.connect(self.close)
        self.mainLayout.addWidget(self.buttonClose)

    def set_weight(self, value):
        self.current_weight = value
        cmds.inViewMessage(amg=f"Selected Weight: <hl>{value}</hl>", pos="midCenter", fade=True)

    def apply_weight(self):
        if self.current_weight is None:
            cmds.warning("Please select a weight value first.")
            return
        BlndWghtUtil.apply_weight(self.current_weight)


def run():
    global ui
    try:
        ui.close()
    except:
        pass

    ptr = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = BlendWeightHelper(parent=ptr)
    ui.show()
