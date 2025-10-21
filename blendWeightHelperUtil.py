import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

# ============================================================
# AUTO BLEND METHOD: LOCALIZED CAPSULE
# ============================================================
def apply_localized_capsule_blend(radius, falloff):
    selected_verts = cmds.ls(sl=True, fl=True)
    selected_verts = cmds.filterExpand(selected_verts, sm=31)
    if not selected_verts:
        cmds.warning("Please select vertices to apply the blend to."); return
        
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

    skin_cluster = find_skin_cluster(selection=[child_jnt])
    if not skin_cluster:
        cmds.warning(f"Could not find a skinCluster for '{child_jnt}'."); return
    
    mesh_name_from_skin = cmds.listRelatives(cmds.skinCluster(skin_cluster, q=True, g=True)[0], p=True, f=True)[0]
    mesh_name_from_selection = selected_verts[0].split('.')[0]
    try:
        unique_skin_mesh_path = cmds.ls(mesh_name_from_skin, long=True)[0]
        unique_selection_mesh_path = cmds.ls(mesh_name_from_selection, long=True)[0]
        if unique_skin_mesh_path != unique_selection_mesh_path:
            cmds.warning("Selection Mismatch: Your vertices and Paint Tool are on different meshes."); return
    except IndexError:
        cmds.warning("Could not resolve mesh names for validation."); return

    parent_pos = om.MPoint(cmds.xform(parent_jnt, q=True, ws=True, t=True))
    child_pos = om.MPoint(cmds.xform(child_jnt, q=True, ws=True, t=True))
    grandchildren = cmds.listRelatives(child_jnt, c=True, type="joint", f=True)
    if not grandchildren:
        cmds.warning(f"'{child_jnt}' has no child joint to define capsule end."); return
    grandchild_pos = om.MPoint(cmds.xform(grandchildren[0], q=True, ws=True, t=True))

    weights_to_set = {}
    for vtx in selected_verts:
        vtx_pos = om.MPoint(cmds.xform(vtx, q=True, ws=True, t=True))
        _, dist_parent = get_closest_point_on_segment(vtx_pos, parent_pos, child_pos)
        _, dist_child = get_closest_point_on_segment(vtx_pos, child_pos, grandchild_pos)
        
        in_parent = dist_parent < radius
        in_child = dist_child < radius
        tv = []
        if in_parent and in_child:
            total_dist = dist_parent + dist_child
            if total_dist > 0.001:
                ratio = dist_parent / total_dist
                smoothed_ratio = pow(ratio, falloff)
                tv = [(parent_jnt, 1.0 - smoothed_ratio), (child_jnt, smoothed_ratio)]
        elif in_parent: tv = [(parent_jnt, 1.0), (child_jnt, 0.0)]
        elif in_child: tv = [(parent_jnt, 0.0), (child_jnt, 1.0)]
        if tv:
            weights_to_set[vtx] = tv

    if not weights_to_set:
        cmds.warning("None of the selected vertices were within the capsule radius."); return
    
    _apply_weights_with_progress(skin_cluster, weights_to_set, "Localized Capsule", [parent_jnt, child_jnt])

# ============================================================
# CORE & HELPER FUNCTIONS
# ============================================================
def _apply_weights_with_progress(skin_cluster, weights_to_set, method_name, relevant_joints, apply_weights=True):
    cmds.undoInfo(openChunk=True)
    progress_window = None
    try:
        if apply_weights:
            progress_window = cmds.window(title=f"Applying {method_name}", width=300)
            cmds.columnLayout(adj=True); progress_bar = cmds.progressBar(maxValue=len(weights_to_set), width=300); cmds.showWindow(progress_window)
        
        all_verts = list(weights_to_set.keys())
        all_influences = cmds.skinCluster(skin_cluster, q=True, influence=True)
        influences_to_prune = [inf for inf in all_influences if inf not in relevant_joints]
        
        if influences_to_prune and all_verts:
            prune_weights_list = [(inf, 0.0) for inf in influences_to_prune]
            cmds.skinPercent(skin_cluster, all_verts, transformValue=prune_weights_list, normalize=False)
            
        if apply_weights:
            for vtx, tv in weights_to_set.items():
                if progress_window and cmds.progressBar(progress_bar, q=True, isCancelled=True): break
                if tv:
                    cmds.skinPercent(skin_cluster, vtx, transformValue=tv, normalize=False)
                if progress_window:
                    cmds.progressBar(progress_bar, e=True, step=1)
            
            if all_verts:
                cmds.skinCluster(skin_cluster, e=True, normalizeWeights=True, geometry=all_verts)
    except Exception as e:
        cmds.warning(f"Error during weight application: {e}")
    finally:
        if progress_window and cmds.window(progress_window, exists=True):
            cmds.deleteUI(progress_window, window=True)
        cmds.undoInfo(closeChunk=True)
        if apply_weights:
            cmds.inViewMessage(amg=f"Applied {method_name} to {len(weights_to_set)} vertices.", pos="midCenter", fade=True)
        cmds.refresh(f=True)

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

def get_closest_point_on_segment(point, seg_start, seg_end):
    segment_vec = seg_end - seg_start
    point_vec = point - seg_start
    segment_len_sq = segment_vec.length() ** 2
    if segment_len_sq == 0: return seg_start, (point - seg_start).length()
    t = (point_vec * segment_vec) / segment_len_sq
    t = max(0.0, min(1.0, t))
    closest_point = seg_start + (segment_vec * t)
    distance = (point - closest_point).length()
    return closest_point, distance

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



