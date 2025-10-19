import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
from collections import Counter

# (ฟังก์ชันอื่นๆ ตั้งแต่ find_skin_cluster จนถึง _determine_joint_hierarchy ยังอยู่เหมือนเดิม)
# ...
def find_skin_cluster(selection=None):
    """Robustly finds the skinCluster node from the given selection."""
    if not selection:
        selection = cmds.ls(selection=True, o=True, fl=True)
    if not selection: return None
    for obj in selection:
        mesh_name = obj.split('.')[0]
        shapes = cmds.listRelatives(mesh_name, shapes=True, noIntermediate=True, fullPath=True)
        if not shapes: continue
        for shape in shapes:
            connections = cmds.listConnections(shape, type='skinCluster')
            if connections: return list(set(connections))[0]
    history = cmds.listHistory(selection[0])
    if history:
        skin_clusters = cmds.ls(history, type="skinCluster")
        if skin_clusters: return skin_clusters[0]
    return None

def _determine_joint_hierarchy(jnt_a, jnt_b):
    """Checks the full path hierarchy to determine which joint is the parent."""
    path_a = cmds.listRelatives(jnt_a, allParents=True, fullPath=True) or []
    path_b = cmds.listRelatives(jnt_b, allParents=True, fullPath=True) or []
    if any(jnt_b == p or p.endswith("|" + jnt_b) for p in path_a): return jnt_b, jnt_a
    if any(jnt_a == p or p.endswith("|" + jnt_a) for p in path_b): return jnt_a, jnt_b
    return jnt_a, jnt_b

# (ฟังก์ชัน get_vertex_weights_all, apply_weight, set_specific_vertex_weight ก็ยังอยู่เหมือนเดิม)
# ...
def get_vertex_weights_all():
    """Returns [(vertex, joint, weight)] for all selected vertices."""
    sels = cmds.ls(selection=True, fl=True)
    if not sels or not cmds.filterExpand(sels, sm=31): return []
    skin_cluster = find_skin_cluster(selection=sels)
    if not skin_cluster: return []
    influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
    if not influences: return []
    result = []
    for vtx in sels:
        weights = cmds.skinPercent(skin_cluster, vtx, q=True, value=True)
        for i, weight_val in enumerate(weights):
            if weight_val > 0.0001:
                result.append((vtx, influences[i], weight_val))
    return result

def apply_weight(weight_value):
    """Applies weight based on the active influence in the Paint Skin Weights Tool."""
    sels = cmds.ls(selection=True, fl=True)
    if not cmds.filterExpand(sels, sm=31):
        cmds.warning("No vertex selected."); return
    skin_cluster = find_skin_cluster(selection=sels)
    if not skin_cluster:
        cmds.warning("No skinCluster found on selection."); return
    current_context = cmds.currentCtx()
    if cmds.contextInfo(current_context, c=True) != 'artAttrSkin':
        mel.eval("ArtPaintSkinWeightsTool;")
        cmds.warning("Paint Tool was not active. It has been opened. Please select a joint and try again."); return
    active_joint = cmds.artAttrSkinPaintCtx(current_context, q=True, influence=True)
    if not active_joint:
        cmds.warning("No influence joint is selected in the Paint Tool."); return
    cmds.undoInfo(openChunk=True)
    try:
        cmds.skinPercent(skin_cluster, sels, transformValue=[(active_joint, weight_value)], normalize=True)
    finally:
        cmds.undoInfo(closeChunk=True)
    cmds.refresh(force=True)

def set_specific_vertex_weight(vertex, joint, weight_value):
    """Sets a specific weight for a single vertex-joint pair from the table."""
    skin_cluster = find_skin_cluster(selection=[vertex])
    if not skin_cluster: return
    weight_value = max(0.0, min(1.0, weight_value))
    cmds.undoInfo(openChunk=True)
    try:
        cmds.skinPercent(skin_cluster, vertex, transformValue=[(joint, weight_value)], normalize=True)
    finally:
        cmds.undoInfo(closeChunk=True)
    cmds.refresh(force=True)

## --- NEW CAPSULE WEIGHT FUNCTION (Placeholder) ---
def auto_capsule_weight(radius):
    """
    Placeholder for capsule weighting. Detects the selected influence from the
    Paint Skin Weights Tool, and finds its parent and mesh automatically.
    """
    # 1. Check if we are in the Paint Skin Weights Tool context.
    current_context = cmds.currentCtx()
    if not current_context.startswith('artAttrSkin'):
        cmds.warning("Please open the Paint Skin Weights Tool and select an influence.")
        return

    # 2. Get the currently selected influence (joint) from the tool's UI.
    child_jnt = cmds.artAttrSkinPaintCtx(current_context, q=True, influence=True)
    if not child_jnt:
        cmds.warning("No influence is selected in the Paint Tool window. Please click on a joint name.")
        return
        
    # 3. Find the parent of the selected joint.
    parents = cmds.listRelatives(child_jnt, parent=True, type="joint", fullPath=True)
    if not parents:
        cmds.warning(f"Could not find a parent joint for '{child_jnt}'. Cannot create a capsule.")
        return
    parent_jnt = parents[0]
    
    # 4. Find the skinCluster and the mesh automatically.
    skin_clusters = cmds.listConnections(child_jnt, type='skinCluster')
    if not skin_clusters:
        cmds.warning(f"Could not find a skinCluster connected to '{child_jnt}'.")
        return
    skin_cluster = list(set(skin_clusters))[0]
    
    geometry_shapes = cmds.skinCluster(skin_cluster, q=True, geometry=True)
    if not geometry_shapes:
        cmds.warning(f"Could not find the mesh connected to {skin_cluster}.")
        return
    mesh_name = cmds.listRelatives(geometry_shapes[0], parent=True, fullPath=True)[0]

    # 5. Print confirmation (Placeholder for actual logic)
    print("="*50)
    print("AUTO CAPSULE WEIGHT - VALIDATION SUCCESS (Paint Tool Workflow)")
    print(f"  Mesh (auto): {mesh_name}")
    print(f"  Child Joint (selected): {child_jnt}")
    print(f"  Parent Joint (auto): {parent_jnt}")
    print(f"  Skin Cluster (auto): {skin_cluster}")
    print(f"  Capsule Radius: {radius}")
    print("="*50)
    
    cmds.inViewMessage(amg="Selection from Paint Tool successful!", pos="midCenter", fade=True)
    # Next step: Implement the capsule math here.
# (ฟังก์ชัน reset_selected_vertices, open_paint_skin_weight_tool ยังอยู่เหมือนเดิม)
# ...
def reset_selected_vertices():
    if not cmds.ls(selection=True): cmds.warning("Nothing selected to deselect."); return
    cmds.select(clear=True)
    cmds.inViewMessage(amg="Cleared selection.", pos="midCenter", fade=True)

def open_paint_skin_weight_tool():
    mel.eval("ArtPaintSkinWeightsTool;")
    cmds.inViewMessage(amg="Opened Paint Skin Weight Tool.", pos="topCenter", fade=True)