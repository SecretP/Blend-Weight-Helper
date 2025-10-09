import maya.cmds as cmds

def apply_weight(weight_value):
	sels = cmds.ls(selection=True, fl=True)
	if not sels:
		cmds.warning("No vertex selected.")
		return

	skin_cluster = "skinCluster1"  # prototype only
	joint = "joint1"

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

	skin_cluster = "skinCluster1"
	values = []
	for vtx in sels:
		val = cmds.skinPercent(skin_cluster, vtx, query=True, value=True)
		values.append(val)
		print(f"{vtx} : {val}")
	cmds.inViewMessage(amg="Displayed vertex weight values in script editor.", pos="botLeft", fade=True)


def auto_weight():
	cmds.inViewMessage(amg="AUTO WEIGHT prototype triggered.", pos="midCenter", fade=True)
	print("[AUTO WEIGHT] prototype running... (ยังไม่ implement)")
