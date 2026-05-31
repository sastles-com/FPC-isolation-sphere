import bpy

#boolean_type = 'DIFFERENCE'
#root_object = bpy.data.objects['separate09']

selected_objects = bpy.context.selected_objects

for obj in selected_objects:
    print('bevel', obj.name)
    
    
#    obj.mesh.convex_hull()

    
    
    # ベベルモディファイアを追加
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')

    bevel_mod.offset_type = 'PERCENT'
    bevel_mod.width_pct = 18



    # ベベルの幅を設定
#    bevel_mod.width = 1.3
#    bevel_mod.width = 1.1
#    bevel_mod.width = 0.6
    # ベベルのセグメント数を設定
#    bevel_mod.segments = 5
    bevel_mod.segments = 4
#    bevel_mod.object = obj
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="BEVEL")
    
#    obj.mesh.bevel(offset=1, offset_pct=0, segments=5, profile=0.5, release_confirm=True)
    
    
    
    
    
#    
#    
#    bool01 = root_object.modifiers.new(type="BOOLEAN", name="bool_01")
#    bool01.object = obj
#    bool01.operation = boolean_type
#    bpy.context.view_layer.objects.active = obj
#    bpy.ops.object.modifier_apply(modifier="bool_01")




    
                