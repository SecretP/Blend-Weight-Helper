#blendWeightHelperUtil.py
import maya.cmds as cmds
import maya.mel as mel

def apply_weight(weight_value):
	sels = cmds.ls(selection=True, fl=True)
	if not sels:
		cmds.warning("No vertex selected.")
		return

	skin_cluster = find_skin_cluster()
	if not skin_cluster:
		cmds.warning("No skinCluster found on selection.")
		return

	influences = cmds.skinCluster(skin_cluster, query = True, influence = True)
	if not influences:
		cmds.warning("No joint influences found.")
		return
	
	joint = influences[0]

	for vtx in sels:
		cmds.skinPercent(skin_cluster, vtx, transformValue=[(joint, weight_value)])
	
	cmds.inViewMessage(amg=f"Applied weight {weight_value}", pos="midCenter", fade=True)


def display_selected_vertices():
	sels = cmds.ls(selection=True, fl=True)
	if not sels:
		cmds.warning("No vertex selected.")
		return
	
	print("Selected vertices:")
	for vtx in sels:
		print(vtx)
	
	cmds.inViewMessage(amg=f"Listed {len(sels)} selected vertices in script editor.", pos="botLeft", fade=True)


def display_weight_values():
	sels = cmds.ls(selection=True, fl=True)
	if not sels:
		cmds.warning("No vertex selected.")
		return

	skin_cluster = find_skin_cluster()
	if not skin_cluster:
		cmds.warning("No skinCLuster found.")
		return

	for vtx in sels:
		val = cmds.skinPercent(skin_cluster, vtx, query=True, value=True)
		print(f"{vtx} : {val}")
	cmds.inViewMessage(amg="Displayed vertex weight values in script editor.", pos="botLeft", fade=True)


def auto_weight():
	cmds.inViewMessage(amg="AUTO WEIGHT prototype triggered.", pos="midCenter", fade=True)
	print("[AUTO WEIGHT] prototype running... (no implement)")

def find_skin_cluster():
	sels = cmds.ls(selection=True, o=True)
	if not sels:
		return None
	
	history = cmds.listHistory(sels[0])
	if not history:
		return None

	skin_cluster = cmds.ls(history, type="skinCluster")
	return skin_cluster[0] if skin_cluster else None

# MAYA TOOL SHOTCUTS
def open_paint_skin_weight_tool():
    try:
        mel.eval("ArtPaintSkinWeightsTool;")  # เปิด tool
        # เปิด tool settings window ด้วย
        cmds.ToolSettingsWindow()  
        cmds.inViewMessage(
            amg="Opened Paint Skin Weights Tool with Tool Settings.",
            pos="topCenter", fade=True
        )
    except Exception as e:
        cmds.warning(f"Failed to open Paint Skin Weights Tool: {e}")

		
def open_smooth_skin_editor():
	try:
		mel.eval("ComponentEditor; showEditorComponent 'SmoothSkin'")
		cmds.inViewMessage(amg="Opened Component Editor > Smooth Skin tab", pos = "topCenter", fade = True)
	except Exception as e:
		cmds.warning(f"Failed to open Component Editor: {e}")

def get_vertex_weights():
    """Return [(joint, weight)] for the first selected vertex."""
    sels = cmds.ls(selection=True, fl=True)
    if not sels:
        cmds.warning("No vertex selected.")
        return []

    skin_cluster = find_skin_cluster()
    if not skin_cluster:
        cmds.warning("No skinCluster found.")
        return []

    vtx = sels[0]
    values = cmds.skinPercent(skin_cluster, vtx, query=True, value=True) 
    if not isinstance(values, list):
        values = [values]
    joints = cmds.skinCluster(skin_cluster, query=True, influence=True)

    return list(zip(joints, values))
