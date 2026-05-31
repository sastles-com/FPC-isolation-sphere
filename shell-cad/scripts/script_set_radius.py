import bpy
import bmesh
import mathutils
# --- Configuration ---
TARGET_RADIUS = 47.0  # (mm) Distance from World Origin (0,0,0)
# ---------------------
def set_radius():
    # Get active object
    obj = bpy.context.active_object
    
    if obj is None:
        print("Error: No active object.")
        return
        
    if obj.type != 'MESH':
        print("Error: Active object is not a mesh.")
        return
    # Check mode
    if obj.mode != 'EDIT':
        print("Error: Please run this script in EDIT mode.")
        return
    # Get BMesh from mesh
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    
    # Get World Matrix (to handle object rotation/location if applied)
    # However, usually we want to modify LOCAL coordinates.
    # If the object is at (0,0,0) and unrotated, Local == World.
    # If the user wants "Distance from Origin", typically it implies World Origin.
    # But usually in edit mode we work in Local space.
    # If the user wants "Distance from Object Origin" -> Local Coords.
    # If the user wants "Distance from World Origin" -> Need to transform.
    
    # Assuming user models "centered at origin" as per Dodecahedron project.
    # So Object Origin == World Origin == Geometry Center.
    # We will modify Local Coordinates `v.co`.
    
    selected_verts = [v for v in bm.verts if v.select]
    
    if not selected_verts:
        print("No vertices selected.")
        return
        
    count = 0
    for v in selected_verts:
        # Current vector from origin
        vec = v.co
        length = vec.length
        
        if length > 0.0001:
            # Normalize and Scale
            v.co = vec.normalized() * TARGET_RADIUS
            count += 1
            
    # Update Mesh
    bmesh.update_edit_mesh(me)
    print(f"Moved {count} vertices to radius {TARGET_RADIUS}.")
if __name__ == "__main__":
    set_radius()
