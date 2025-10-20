import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

# ============================================================
# FINAL SIMPLE BLEND FUNCTION
# ============================================================
def apply_hierarchy_blend():
    """
    Applies a 5-step weight blend. The selected joint is always treated
    as the 'parent' of the blend operation.
    """
    ctx = cmds.currentCtx()
    if not ctx.startswith('artAttrSkin'):
        cmds.warning("Please open the Paint Skin Weights Tool and select an influence joint."); return
    center_jnt = cmds.artAttrSkinPaint-Ctx(ctx, q=True, influence=True)
    if not center_jnt:
        cmds.warning("No influence is selected in the Paint Tool window."); return

    original_context = cmds.currentCtx()
    original_selection = cmds.ls(sl=True, long=True)
    
    cmds.undoInfo(openChunk=True)
    try:
        # --- CORRECTED BLEND PAIR LOGIC ---
        # The selected joint is now always the parent of the blend.
        blend_parent = center_jnt
        blend_child = (cmds.listRelatives(center_jnt, c=True, type="joint", f=True) or [None])[0]

        # If there is no child, we cannot create a blend.
        if not blend_child:
            cmds.warning(f"Cannot create blend. Joint '{center_jnt}' has no child joint."); return

        # Find the full 5-joint chain for loop discovery
        parent_of_blend_parent = (cmds.listRelatives(blend_parent, p=True, type="joint", f=True) or [None])[0]
        child_of_blend_child = (cmds.listRelatives(blend_child, c=True, type="joint", f=True) or [None])[0]

        joint_chain = [
            (cmds.listRelatives(parent_of_blend_parent, p=True, type="joint", f=True) or [None])[0], # Grandparent of Parent
            parent_of_blend_parent, # Parent of Parent
            blend_parent,           # The selected joint (Center)
            blend_child,            # The child
            child_of_blend_child    # The grandchild
        ]
        
        skin_cluster = find_skin_cluster(selection=[center_jnt])
        if not skin_cluster:
            cmds.warning(f"Could not find a skinCluster for '{center_jnt}'."); return
        mesh_name = cmds.listRelatives(cmds.skinCluster(skin_cluster, q=True, g=True)[0], p=True, f=True)[0]
        
        sel_list = om.MSelectionList(); sel_list.add(mesh_name)
        mesh_fn = om.MFnMesh(sel_list.getDagPath(0))
        vertex_positions = mesh_fn.getPoints(om.MSpace.kWorld)

        vertex_loops = []
        all_loop_verts = []
        for i, joint in enumerate(joint_chain):
            if not joint:
                vertex_loops.append([]); continue
            
            joint_pos = om.MPoint(cmds.xform(joint, q=True, ws=True, t=True))
            closest_vtx_index = -1; min_dist_sq = float('inf')
            for vtx_idx, vtx_pos in enumerate(vertex_positions):
                dist_sq = vtx_pos.distanceTo(joint_pos)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq; closest_vtx_index = vtx_idx
            
            closest_vtx_name = f"{mesh_name}.vtx[{closest_vtx_index}]"
            cmds.select(closest_vtx_name, r=True)
            mel.eval("polySelectSp -loop;")
            current_loop = cmds.ls(sl=True, fl=True)
            if not current_loop:
                print(f"Warning: Could not determine vertex loop for joint '{joint.split('|')[-1]}'. Skipping.")
            vertex_loops.append(current_loop)
            all_loop_verts.extend(current_loop)
        
        if not vertex_loops[2]:
             cmds.warning("Failed to identify the central vertex loop. Check mesh topology."); return
            
        weights = [
            [(blend_parent, 1.0), (blend_child, 0.0)],
            [(blend_parent, 0.8), (blend_child, 0.2)],
            [(blend_parent, 0.5), (blend_child, 0.5)],
            [(blend_parent, 0.2), (blend_child, 0.8)],
            [(blend_parent, 0.0), (blend_child, 1.0)]
        ]
        
        unique_loop_verts = list(set(all_loop_verts))
        if not unique_loop_verts:
            cmds.warning("Could not find any vertex loops to apply weights on."); return
            
        all_influences = cmds.skinCluster(skin_cluster, q=True, influence=True)
        relevant_influences = {blend_parent, blend_child}
        influences_to_prune = [inf for inf in all_influences if inf not in relevant_influences]
        
        if influences_to_prune:
            prune_weights_list = [(inf, 0.0) for inf in influences_to_prune]
            cmds.skinPercent(skin_cluster, unique_loop_verts, transformValue=prune_weights_list, normalize=False)

        for i, loop in enumerate(vertex_loops):
            if loop:
                cmds.skinPercent(skin_cluster, loop, transformValue=weights[i], normalize=True)
        
        cmds.inViewMessage(amg=f"Applied 5-Step Blend between '{blend_parent.split('|')[-1]}' and '{blend_child.split('|')[-1]}'.", pos="midCenter", fade=True)

    except Exception as e:
        cmds.warning(f"Hierarchy Blend failed: {e}")
    finally:
        if original_selection: cmds.select(original_selection, r=True)
        else: cmds.select(cl=True)
        cmds.setToolTo(original_context)
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