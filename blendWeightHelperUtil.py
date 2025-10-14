import maya.cmds as cmds
import maya.mel as mel


def find_skin_cluster():
    sels = cmds.ls(selection=True, o=True)
    if not sels:
        return None
    skin_clusters = cmds.ls(cmds.listHistory(sels[0]), type="skinCluster")
    return skin_clusters[0] if skin_clusters else None


def get_vertex_weights_all():
    """Return [(vertex, joint, weight)] for all selected vertices."""
    sels = cmds.ls(selection=True, fl=True)
    if not sels:
        return []

    skin_cluster = find_skin_cluster()
    if not skin_cluster:
        return []

    influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
    if not influences:
        return []

    result = []
    for vtx in sels:
        for jnt in influences:
            val = cmds.skinPercent(skin_cluster, vtx, q=True, t=jnt)
            if val > 0.0001:
                result.append((vtx, jnt, val))
    return result


def apply_weight(weight_value):
    sels = cmds.ls(selection=True, fl=True)
    if not sels:
        cmds.warning("No vertex selected.")
        return

    skin_cluster = find_skin_cluster()
    if not skin_cluster:
        cmds.warning("No skinCluster found on selection.")
        return

    influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
    if not influences:
        cmds.warning("No joint influences found.")
        return

    joint = influences[0]
    cmds.undoInfo(openChunk=True)
    try:
        for vtx in sels:
            cmds.skinPercent(skin_cluster, vtx, tv=[(joint, weight_value)], normalize=True)
    finally:
        cmds.undoInfo(closeChunk=True)

    _safe_refresh()
    cmds.inViewMessage(amg=f"<hl>Applied weight:</hl> {weight_value}", pos="midCenter", fade=True)


def reset_selected_vertices():
    """Just deselect vertices, no weight change."""
    if not cmds.ls(selection=True):
        cmds.warning("No vertex selected to deselect.")
        return
    cmds.select(clear=True)
    cmds.inViewMessage(amg="Cleared selected vertices.", pos="midCenter", fade=True)


def open_paint_skin_weight_tool():
    mel.eval("ArtPaintSkinWeightsTool;")
    cmds.inViewMessage(amg="Opened Paint Skin Weight Tool.", pos="topCenter", fade=True)


def _safe_refresh():
    """Stable refresh avoiding updateAE errors."""
    try:
        cmds.refresh(cv=True)
    except Exception:
        pass


def auto_weight():
    """Example placeholder for auto-weight algorithm."""
    cmds.inViewMessage(amg="Auto weight executed (placeholder).", pos="midCenter", fade=True)
