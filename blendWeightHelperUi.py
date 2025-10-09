try:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
except:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance

import maya.OpenMayaUi as omui
import maya.cmds as cmds

import importlib

from . import blendWeightHelperUtil as BlndWghtUtil
importlib.reload(util)

class BlendWeightHelper(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)

		self.setWindowTitle('Blend Weight Helper')
		self.resize(300, 300)

		self.mainLayout = QtWidgets.QVBoxLayout()
		self.setLayout(self.mainLayout)
		self.setStyleSheet()
		
		self.Label = QtWidgets.QLabel("PLEASE SELECT VERTEX THEN CHOOSE WEIGHT VALUE")
		self.mainLayout.addWidget(self.Label)

		self.buttonLayout = QtWidget.QHBoxLayout()
		for var in [0.2, 0.5, 0.8]:
			self.button = QtWidgets.QPushButton(str(val))
			self.button.clicked.connect(lambda _, v=val: self.set_weight(v))
			self.buttonLayout.addWidget(self.button)
		self.mainLayout.addLayout(self.buttonLayout)

		

def run():
	global ui
	try:
		ui.close()
	except:
		pass
	ptr =  wrapInstance(int(omui.MQtUtil.mainWindow()),QtWidgets.QWidget)
	ui = StyleToolDialog(parent=ptr)
	ui.show()