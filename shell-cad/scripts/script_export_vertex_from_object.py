import bpy
import csv
import os
# --- Configuration ---
# Output filename (will be saved in the same directory as the .blend file)
OUTPUT_FILENAME = "exported_vertices.csv"
# Apply object rotation/scale/location (World Coordinates)?
APPLY_TRANSFORM = True
# ---------------------
def export_verts():
    # Get active object
    obj = bpy.context.active_object
    
    if obj is None:
        print("Error: No active object selected.")
        return
        
    if obj.type != 'MESH':
        print(f"Error: Selected object '{obj.name}' is not a Mesh.")
        return
    # Determine saving path
    if bpy.data.is_saved:
        blend_path = os.path.dirname(bpy.data.filepath)
        filepath = os.path.join(blend_path, OUTPUT_FILENAME)
    else:
        # Fallback if blend file not saved
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", OUTPUT_FILENAME)
        print(f"Blend file not saved. Saving to Desktop: {filepath}")
    print(f"Exporting vertices for '{obj.name}' to {filepath}...")
    # Get Mesh Data
    mesh = obj.data
    matrix_world = obj.matrix_world
    
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Header
        writer.writerow(['index', 'x', 'y', 'z'])
        
        for v in mesh.vertices:
            co = v.co
            if APPLY_TRANSFORM:
                # Multiply by world matrix
                co = matrix_world @ co
            
            writer.writerow([v.index, f"{co.x:.6f}", f"{co.y:.6f}", f"{co.z:.6f}"])
            
    print(f"Successfully exported {len(mesh.vertices)} vertices.")
    
    # Show popup in Blender
    def draw(self, context):
        self.layout.label(text=f"Exported {len(mesh.vertices)} verts to {OUTPUT_FILENAME}")
    bpy.context.window_manager.popup_menu(draw, title="Export Completed", icon='INFO')
if __name__ == "__main__":
    export_verts()