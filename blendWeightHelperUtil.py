import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

# ============================================================
# FINAL SIMPLE BLEND FUNCTION
# ============================================================
def apply_simple_blend():
    """
    Applies a 3-step weight blend (0.8, 0.5, 0.2) based on a central
    selected vertex loop and the active joint in the Paint Tool.
    """
    # 1. Get user's vertex selection and validate
    selection = cmds.ls(sl=True, fl=True)
    is_edge = cmds.filterExpand(selection, sm=32)
    is_vertex = cmds.filterExpand(selection, sm=31)
    if is_edge:
        cmds.select(selection, r=True); mel.eval("polySelectSp -loop;")
        center_loop_edges = cmds.ls(sl=True, fl=True)
    elif is_vertex:
        center_loop_edges = cmds.ls(cmds.polyListComponentConversion(selection, toEdge=True, internal=True), fl=True)
    else:
        cmds.warning("Please select a central vertex or edge loop."); return
        
    # 2. Get context and joints from Paint Tool
    ctx = cmds.currentCtx()
    if not ctx.startswith('artAttrSkin'):
        cmds.warning("Please open the Paint Skin Weights Tool and select an influence joint."); return
    child_jnt = cmds.artAttrSkinPaintCtx(ctx, q=True, influence=True)
    if not child_jnt:
        cmds.warning("No influence is selected in the Paint Tool window."); return
    parents = cmds.listRelatives(child_jnt, p=True, type="joint", f=True)
    if not parents:
        cmds.warning(f"Could not find a parent joint for '{child_jnt}'."); return
    parent_jnt = parents[0]
    
    # 3. Get skinCluster and other info
    skin_cluster = find_skin_cluster(selection=selection)
    if not skin_cluster:
        cmds.warning("No skinCluster found on selection."); return
    
    cmds.undoInfo(openChunk=True)
    original_selection = cmds.ls(sl=True, long=True)
    try:
        # 4. Find the 3 loops (center, and two adjacent)
        set_loop_c = set(center_loop_edges)
        loop_a_edges, loop_b_edges = _get_adjacent_edge_loops(center_loop_edges)

        if not (loop_a_edges and loop_b_edges):
            cmds.warning("Could not find two adjacent loops. Please select a loop away from mesh borders."); return
            
        # Determine which loop is parent-side vs child-side
        parent_jnt_pos = om.MVector(*cmds.xform(parent_jnt, q=True, ws=True, t=True))
        loop_a_center_vtx = cmds.ls(cmds.polyListComponentConversion(loop_a_edges[0], toVertex=True), fl=True)[0]
        loop_b_center_vtx = cmds.ls(cmds.polyListComponentConversion(loop_b_edges[0], toVertex=True), fl=True)[0]
        loop_a_pos = om.MVector(*cmds.xform(loop_a_center_vtx, q=True, ws=True, t=True))
        loop_b_pos = om.MVector(*cmds.xform(loop_b_center_vtx, q=True, ws=True, t=True))
        
        parent_side_loop, child_side_loop = (loop_a_edges, loop_b_edges) if (parent_jnt_pos - loop_a_pos).length() < (parent_jnt_pos - loop_b_pos).length() else (loop_b_edges, loop_a_edges)
            
        loops_vtx = [
            cmds.ls(cmds.polyListComponentConversion(parent_side_loop, toVertex=True), fl=True),
            cmds.ls(cmds.polyListComponentConversion(center_loop_edges, toVertex=True), fl=True),
            cmds.ls(cmds.polyListComponentConversion(child_side_loop,  toVertex=True), fl=True)
        ]
        
        weights = [
            [(parent_jnt, 0.8), (child_jnt, 0.2)],
            [(parent_jnt, 0.5), (child_jnt, 0.5)],
            [(parent_jnt, 0.2), (child_jnt, 0.8)]
        ]
        
        all_loop_verts = loops_vtx[0] + loops_vtx[1] + loops_vtx[2]
        
        # 5. Prune unrelated influences for a clean result
        all_influences = cmds.skinCluster(skin_cluster, q=True, influence=True)
        relevant_influences = {parent_jnt, child_jnt}
        influences_to_prune = [inf for inf in all_influences if inf not in relevant_influences]
        
        if influences_to_prune:
            prune_weights_list = [(inf, 0.0) for inf in influences_to_prune]
            cmds.skinPercent(skin_cluster, all_loop_verts, transformValue=prune_weights_list, normalize=False)

        # 6. Apply the clean, stepped weights
        for i, loop in enumerate(loops_vtx):
            if loop:
                cmds.skinPercent(skin_cluster, loop, transformValue=weights[i], normalize=True)
        
        cmds.inViewMessage(amg=f"Applied 3-Step Simple Blend.", pos="midCenter", fade=True)

    except Exception as e:
        cmds.warning(f"Simple Blend failed: {e}")
    finally:
        cmds.select(original_selection, r=True)
        cmds.undoInfo(closeChunk=True)
        cmds.refresh(f=True)

# ============================================================
# CORE & HELPER FUNCTIONS
# ============================================================
def find_skin_cluster(selection=None):
    if not selection: 
        selection = cmds.ls(sl=True, long=True)
    if not selection: return None
    node = selection[0]
    if cmds.nodeType(node) == 'joint':
        skin_clusters = cmds.listConnections(node, type='skinCluster')
        if skin_clusters: return list(set(skin_clusters))[0]
    mesh_name = node.split('.')[0]
    shapes = cmds.listRelatives(mesh_name, s=True, ni=True, f=True)
    if shapes:
        for shape in shapes:
            skin_clusters = cmds.listConnections(shape, type='skinCluster')
            if skin_clusters: return list(set(skin_clusters))[0]
    history = cmds.listHistory(mesh_name)
    if history:
        skin_clusters = cmds.ls(history, type="skinCluster")
        if skin_clusters: return skin_clusters[0]
    return None

def _get_adjacent_edge_loops(edge_loop):
    faces = cmds.ls(cmds.polyListComponentConversion(edge_loop, fromEdge=True, toFace=True), fl=True)
    if not faces: return None, None
    border_edges = cmds.ls(cmds.polyListComponentConversion(faces, fromFace=True, toEdge=True, border=True), fl=True)
    if not border_edges: return None, None
    cmds.select(border_edges[0], r=True)
    mel.eval("polySelectSp -loop;")
    loop_a = cmds.ls(sl=True, fl=True)
    loop_b_list = list(set(border_edges) - set(loop_a))
    loop_b = loop_b_list if loop_b_list else None
    original_selection = cmds.ls(sl=True, long=True) # Save selection before returning
    try:
        cmds.select(edge_loop) # Restore selection
    except:
        pass # Handle cases where original selection might be gone
    return loop_a, loop_b

def get_vertex_weights_all():
    sels = cmds.ls(sl=True, fl=True)
    if not sels or not cmds.filterExpand(sels, sm=31): return []
    skin_cluster = find_skin_cluster(selection=sels)
    if not skin_cluster: return []
    influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
    if not influences: return []
    result = []
    for vtx in sels:
        weights = cmds.skinPercent(skin_cluster, vtx, q=True, value=True)
        for i, weight_val in enumerate(weights):
            if weight_val > 0.0001: result.append((vtx, influences[i], weight_val))
    return result

def apply_weight(weight_value):
    sels = cmds.ls(sl=True, fl=True)
    if not cmds.filterExpand(sels, sm=31): cmds.warning("No vertex selected."); return
    skin_cluster = find_skin_cluster(selection=sels)
    if not skin_cluster: cmds.warning("No skinCluster found on selection."); return
    ctx = cmds.currentCtx()
    if cmds.contextInfo(ctx, c=True) != 'artAttrSkin':
        mel.eval("ArtPaintSkinWeightsTool;")
        cmds.warning("Paint Tool was not active. It has been opened."); return
    active_joint = cmds.artAttrSkinPaintCtx(ctx, q=True, inf=True)
    if not active_joint: cmds.warning("No influence joint is selected in the Paint Tool."); return
    cmds.undoInfo(openChunk=True)
    try: cmds.skinPercent(skin_cluster, sels, tv=[(active_joint, weight_value)], normalize=True)
    finally: cmds.undoInfo(closeChunk=True)
    cmds.refresh(f=True)

def set_specific_vertex_weight(vertex, joint, weight_value):
    skin_cluster = find_skin_cluster(selection=[vertex])
    if not skin_cluster: return
    weight_value = max(0.0, min(1.0, weight_value))
    cmds.undoInfo(openChunk=True)
    try: cmds.skinPercent(skin_cluster, vertex, tv=[(joint, weight_value)], normalize=True)
    finally: cmds.undoInfo(closeChunk=True)
    cmds.refresh(f=True)
    
def set_multiple_vertex_weights(weight_data):
    if not weight_data: return
    skin_cluster = find_skin_cluster(selection=[weight_data[0][0]])
    if not skin_cluster: cmds.warning("Could not find a skinCluster for batch operation."); return
    cmds.undoInfo(openChunk=True)
    progress_window = None
    try:
        progress_window = cmds.window(title="Batch Applying Weights", width=300)
        cmds.columnLayout(adj=True); progress_bar = cmds.progressBar(maxValue=len(weight_data), width=300); cmds.showWindow(progress_window)
        all_verts = []
        for vtx, joint, weight in weight_data:
            if cmds.progressBar(progress_bar, q=True, isCancelled=True): break
            weight = max(0.0, min(1.0, weight))
            cmds.skinPercent(skin_cluster, vtx, tv=[(joint, weight)], normalize=False)
            all_verts.append(vtx)
            cmds.progressBar(progress_bar, e=True, step=1)
        if all_verts: cmds.skinCluster(skin_cluster, e=True, nw=True, geo=list(set(all_verts)))
    except Exception as e: cmds.warning(f"Error during batch weight application: {e}")
    finally:
        if progress_window and cmds.window(progress_window, exists=True):
            cmds.deleteUI(progress_window, window=True)
        cmds.undoInfo(closeChunk=True)
        cmds.inViewMessage(amg=f"Batch updated {len(weight_data)} weights.", pos="midCenter", fade=True)
        cmds.refresh(f=True)

def reset_selected_vertices():
    if not cmds.ls(sl=True): cmds.warning("Nothing to deselect."); return
    cmds.select(cl=True)
    cmds.inViewMessage(amg="Selection cleared.", pos="midCenter", fade=True)

def open_paint_skin_weight_tool():
    mel.eval("ArtPaintSkinWeightsTool;")
    cmds.inViewMessage(amg="Opened Paint Skin Weight Tool.", pos="topCenter", fade=True)

def undo_last_action():
    cmds.undo()
    cmds.inViewMessage(amg="Last action undone.", pos="midCenter", fade=True)