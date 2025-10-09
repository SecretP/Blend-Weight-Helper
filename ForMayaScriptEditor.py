import sys
import os
import importlib

sys.path.append(r"C:\Users\Pitinan\Documents\SIlpakorn Homework\2568\Applied Programming II\Final")


import BlendWeightHelperTool.blendWeightHelperUi as BlndWghtUi

importlib.reload(BlndWghtUi)
BlndWghtUi.run()