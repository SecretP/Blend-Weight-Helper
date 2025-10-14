import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

def find_skin_cluster(selection=None):
    """Finds the skinCluster node from the given selection or current selection."""
    if not selection:
        selection = cmds.ls(selection=True, o=True)
    if not selection:
        return None
    
    history = cmds.listHistory(selection[0], pdo=True)
    if not history:
        return None
        
    skin_clusters = cmds.ls(history, type="skinCluster")
    return skin_clusters[0] if skin_clusters else None


def get_vertex_weights_all():
    """Corrected: Return [(vertex, joint, weight)] for all selected vertices by looping."""
    sels = cmds.ls(selection=True, fl=True)
    if not sels or not cmds.filterExpand(sels, sm=31):
        return []

    skin_cluster = find_skin_cluster()
    if not skin_cluster:
        return []

    influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
    if not influences:
        return []

    result = []
    for vtx in sels:
        weights = cmds.skinPercent(skin_cluster, vtx, q=True, value=True)
        for i, weight_val in enumerate(weights):
            if weight_val > 0.0001:
                result.append((vtx, influences[i], weight_val))
    return result


def apply_weight(weight_value):
    """Applies weight to selected vertices based on the currently active influence in the Paint Skin Weights Tool."""
    sels = cmds.ls(selection=True, fl=True)
    if not cmds.filterExpand(sels, sm=31):
        cmds.warning("No vertex selected.")
        return

    skin_cluster = find_skin_cluster()
    if not skin_cluster:
        cmds.warning("No skinCluster found on selection.")
        return

    current_context = cmds.currentCtx()
    if cmds.contextInfo(current_context, c=True) != 'artAttrSkin':
        mel.eval("ArtPaintSkinWeightsTool;")
        cmds.warning("Paint Skin Weight Tool was not active. It has been opened. Please select a joint and try again.")
        return
        
    active_joint = cmds.artAttrSkinPaintCtx(current_context, q=True, influence=True)
    if not active_joint:
        cmds.warning("No influence joint is selected in the Paint Skin Weights Tool.")
        return

    cmds.undoInfo(openChunk=True)
    try:
        cmds.skinPercent(skin_cluster, sels, transformValue=[(active_joint, weight_value)], normalize=True)
    finally:
        cmds.undoInfo(closeChunk=True)
    _safe_refresh()


def set_specific_vertex_weight(vertex, joint, weight_value):
    """Sets a specific weight for a single vertex-joint pair."""
    skin_cluster = find_skin_cluster(selection=[vertex])
    if not skin_cluster: return
    weight_value = max(0.0, min(1.0, weight_value))
    cmds.undoInfo(openChunk=True)
    try:
        cmds.skinPercent(skin_cluster, vertex, transformValue=[(joint, weight_value)], normalize=True)
    finally:
        cmds.undoInfo(closeChunk=True)
    cmds.inViewMessage(amg=f"Set <hl>{vertex}</hl> on <hl>{joint}</hl> to <hl>{weight_value:.3f}</hl>", pos="botCenter", fade=True)
    _safe_refresh()


def _get_adjacent_edge_loops(edge_loop):
    """
    Robustly finds one or two adjacent edge loops using a face-to-border-edge conversion.
    Returns: (loop_a, loop_b) where loop_b can be None if only one is found.
    """
    # Step 1: Convert the source edge loop to its adjacent faces. This is reliable.
    faces = cmds.ls(cmds.polyListComponentConversion(edge_loop, fromEdge=True, toFace=True), fl=True)
    if not faces:
        return None, None
    
    # Step 2: From this group of faces, get only the edges on its border.
    # This is the key step. It will reliably return the two outer edge loops.
    border_edges = cmds.ls(cmds.polyListComponentConversion(faces, fromFace=True, toEdge=True, border=True), fl=True)
    
    if not border_edges:
        return None, None
    
    # Step 3: Separate the resulting edges into two distinct loops.
    cmds.select(border_edges[0], r=True)
    mel.eval("polySelectSp -loop;")
    loop_a = cmds.ls(sl=True, fl=True)
    
    loop_b_list = list(set(border_edges) - set(loop_a))
    loop_b = loop_b_list if loop_b_list else None
    
    return loop_a, loop_b


def auto_weight():
    """
    Auto Weight v4: Uses a robust method to find adjacent loops.
    Select 1 middle edge loop to create a blend.
    """
    sel_edges = cmds.ls(selection=True, fl=True)
    if not sel_edges or not cmds.filterExpand(sel_edges, sm=32):
        cmds.warning("Please select one edge loop in the middle of the blend area.")
        return

    skin_cluster = find_skin_cluster()
    if not skin_cluster:
        cmds.warning("No skinCluster found on selection.")
        return

    cmds.undoInfo(openChunk=True)
    try:
        cmds.select(sel_edges, r=True)
        mel.eval("polySelectSp -loop;")
        middle_loop_edges = cmds.ls(sl=True, fl=True)
        middle_loop_vtx = cmds.ls(cmds.polyListComponentConversion(middle_loop_edges, fromEdge=True, toVertex=True), fl=True)
        
        influence_data = {}
        influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
        for vtx in middle_loop_vtx[:5]:
            weights = cmds.skinPercent(skin_cluster, vtx, q=True, value=True)
            for i, w in enumerate(weights):
                jnt = influences[i]
                influence_data[jnt] = influence_data.get(jnt, 0) + w
        
        sorted_influences = sorted(influence_data, key=influence_data.get, reverse=True)
        if len(sorted_influences) < 2:
            cmds.warning("Could not determine two primary influence joints for the selected loop.")
            cmds.undoInfo(closeChunk=True)
            return

        jnt1, jnt2 = sorted_influences[0], sorted_influences[1]
        
        loop_a_edges, loop_b_edges = _get_adjacent_edge_loops(middle_loop_edges)
        
        if loop_a_edges and loop_b_edges:
            # IDEAL CASE: Found 2 loops, perform 3-step blend
            jnt1_pos = om.MVector(*cmds.xform(jnt1, q=True, ws=True, t=True))
            
            loop_a_vtx = cmds.ls(cmds.polyListComponentConversion(loop_a_edges, fromEdge=True, toVertex=True), fl=True)
            loop_b_vtx = cmds.ls(cmds.polyListComponentConversion(loop_b_edges, fromEdge=True, toVertex=True), fl=True)
            
            loop_a_center_pos = om.MVector(*cmds.xform(loop_a_vtx[0], q=True, ws=True, t=True))
            loop_b_center_pos = om.MVector(*cmds.xform(loop_b_vtx[0], q=True, ws=True, t=True))
            
            if (jnt1_pos - loop_a_center_pos).length() < (jnt1_pos - loop_b_center_pos).length():
                parent_loop_vtx, child_loop_vtx = loop_a_vtx, loop_b_vtx
            else:
                parent_loop_vtx, child_loop_vtx = loop_b_vtx, loop_a_vtx
            
            cmds.skinPercent(skin_cluster, parent_loop_vtx, transformValue=[(jnt1, 0.8), (jnt2, 0.2)], normalize=True)
            cmds.skinPercent(skin_cluster, middle_loop_vtx, transformValue=[(jnt1, 0.5), (jnt2, 0.5)], normalize=True)
            cmds.skinPercent(skin_cluster, child_loop_vtx, transformValue=[(jnt1, 0.2), (jnt2, 0.8)], normalize=True)
            cmds.inViewMessage(amg=f"Applied 3-step blend for <hl>{jnt1}</hl> and <hl>{jnt2}</hl>.", pos="midCenter", fade=True)

        elif loop_a_edges and not loop_b_edges:
            # EDGE CASE: Found 1 loop (e.g., end of a limb), perform 2-step blend
            adjacent_loop_vtx = cmds.ls(cmds.polyListComponentConversion(loop_a_edges, fromEdge=True, toVertex=True), fl=True)
            
            cmds.skinPercent(skin_cluster, middle_loop_vtx, transformValue=[(jnt1, 0.5), (jnt2, 0.5)], normalize=True)
            cmds.skinPercent(skin_cluster, adjacent_loop_vtx, transformValue=[(jnt1, 0.8), (jnt2, 0.2)], normalize=True)
            cmds.inViewMessage(amg=f"Applied 2-step (end cap) blend for <hl>{jnt1}</hl> and <hl>{jnt2}</hl>.", pos="midCenter", fade=True)

        else:
            cmds.warning("Could not find any adjacent edge loops. Please check model topology.")
            cmds.undoInfo(closeChunk=True)
            return

        cmds.select(middle_loop_edges, r=True)

    except Exception as e:
        cmds.warning(f"Auto Weight failed. Error: {e}")
    finally:
        cmds.undoInfo(closeChunk=True)


def reset_selected_vertices():
    if not cmds.ls(selection=True):
        cmds.warning("Nothing selected to deselect.")
        return
    cmds.select(clear=True)
    cmds.inViewMessage(amg="Cleared selection.", pos="midCenter", fade=True)


def open_paint_skin_weight_tool():
    mel.eval("ArtPaintSkinWeightsTool;")
    cmds.inViewMessage(amg="Opened Paint Skin Weight Tool.", pos="topCenter", fade=True)


def _safe_refresh():
    try:
        cmds.refresh(cv=True)
    except Exception:
        pass