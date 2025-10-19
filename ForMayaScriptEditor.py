import sys
import os
import importlib


#Change the folder path to you folder location

sys.path.append(r"C:\Users\Pitinan\Documents\SIlpakorn Homework\2568\Applied Programming II\Final")


#ZIP File from github the naime is contain Blend-Weight-Helper-Tool-Main
#You must change the folder name to BlendWeightHelperTool

import BlendWeightHelperTool.blendWeightHelperUi as BlndWghtUi



importlib.reload(BlndWghtUi)
BlndWghtUi.run()