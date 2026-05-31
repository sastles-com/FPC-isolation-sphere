import bpy
import mathutils
# --- Configuration ---
TARGET_RADIUS = 50.0 # (mm) Distance from World Origin
# ---------------------
def set_object_radius():
    # Get selected objects
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("Error: No objects selected.")
        return
    print(f"Processing {len(selected_objects)} objects. Target Radius: {TARGET_RADIUS}")
    count = 0
    for obj in selected_objects:
        # Get current location
        loc = obj.location
        
        # Check if length is non-zero (to avoid division by zero)
        if loc.length > 0.0001:
            # Normalize vector and scale
            new_loc = loc.normalized() * TARGET_RADIUS
            obj.location = new_loc
            count += 1
        else:
            print(f"Skipping '{obj.name}': Location is at Origin (0,0,0). Cannot determine direction.")
    print(f"Moved {count} objects to radius {TARGET_RADIUS}.")
if __name__ == "__main__":
    set_object_radius()
