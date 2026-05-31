import bpy
def cleanup_mesh():
    # Get selected objects
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("Error: No objects selected.")
        return
    print(f"Processing {len(selected_objects)} objects...")
    # Iterate over all selected objects
    for obj in selected_objects:
        if obj.type != 'MESH':
            continue
            
        # Set as active object
        bpy.context.view_layer.objects.active = obj
        
        # Ensure we are in Object Mode to start (clean state)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Enter Edit Mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 1. Select All
        bpy.ops.mesh.select_all(action='SELECT')
        
        # 2. Convex Hull
        # Creates a convex hull around the selection. 
        # By default this replaces the selection if delete_unused is True?
        # Standard behavior essentially "wraps" the object.
        bpy.ops.mesh.convex_hull()
        
        # 3. Limited Dissolve
        # Cleans up planar geometry (collapses triangles on flat surfaces)
        bpy.ops.mesh.dissolve_limited()
        
        # 4. Make Normals Consistent (Outward)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        # 5. Exit Edit Mode (Toggle or clear Set)
        bpy.ops.object.mode_set(mode='OBJECT')
        
    print("Cleanup Mesh sequence completed.")
if __name__ == "__main__":
    cleanup_mesh()
