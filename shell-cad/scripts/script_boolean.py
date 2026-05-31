import bpy

boolean_type = 'DIFFERENCE'
#boolean_type = 'INTERSECT'
#boolean_type = 'UNION'
#root_object = bpy.data.objects['48.013']
#root_object = bpy.data.objects['voronoi_004']
root_object = bpy.data.objects['012.010']
#root_object = bpy.data.objects['sphere-48.001']

selected_objects = bpy.context.selected_objects


# reselect root object
bpy.ops.object.select_all(action='DESELECT')
#bpy.ops.object.select_all(action='DESELECT')
#bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = root_object

#iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii


for obj in selected_objects:
    print('boolean', obj.name)




#    
#    # ベベルモディファイアを追加
#    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
#    # ベベルの幅を設定
#    bevel_mod.width = 1.0
#    # ベベルのセグメント数を設定
#    bevel_mod.segments = 5 
##    bevel_mod.object = obj
#    bpy.context.view_layer.objects.actpathive = obj
#    bpy.ops.object.modifier_apply(modifier="BEVEL")
#    
##    obj.mesh.bevel(offset=1, offset_pct=0, segments=5, profile=0.5, release_confirm=True)
#    
    
    
    
    
#    name = 'bool-' + obj.name.split('-')[1] + '-' + obj.name.split('-')[2] 
    name = obj.name
    
    bpy.ops.object.modifier_add(type='BOOLEAN')
#    root_object.modifier_add(type='BOOLEAN')

    boolean = bpy.context.object.modifiers["Boolean"]
    boolean.operation = boolean_type
#    boolean.solver = 'FAST'
    boolean.solver = 'EXACT'
    boolean.use_self = True
    boolean.use_hole_tolerant = True
    boolean.object = bpy.data.objects[name]
    


#    root_object.modifier_apply(modifier="Boolean")
    bpy.ops.object.modifier_apply(modifier="Boolean")



    
#    bool01 = root_object.modifiers.new(type="BOOLEAN", name=name)
#    bool01.object = obj
#    bool01.operation = boolean_type
#    bpy.context.view_layer.objects.active = obj
#    bpy.ops.object.modifier_apply(modifier=name, report=True)

#    bpy.context.object.modifiers[name].use_self = True
#    bpy.context.object.modifiers[name].use_hole_tolerant = True

#    bpy.context.object.modifiers[name].modifier_apply(modifier="Boolean")




##    # apply this modifier
#    bpy.ops.object.modifier_apply(
#                modifier=modifier.name
#            )
#    
