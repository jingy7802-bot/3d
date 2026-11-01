"""Render-only batching of rigid mesh parts. Never saves or edits source blend."""
import bpy,sys
from pathlib import Path
from mathutils import Matrix
s=bpy.context.scene;p=Path(__file__).parent
s.frame_set(1);bpy.context.view_layer.update()
def visible(ob):return not ob.hide_render and not any(c.hide_render or c.hide_viewport for c in ob.users_collection)
def merge(parts,parent=None):
    if len(parts)<2:return
    verts=[];faces=[];materials=[];indices=[];smooth=[]
    inv=parent.matrix_world.inverted_safe() if parent else Matrix.Identity(4)
    for ob in parts:
        offset=len(verts);matrix=inv@ob.matrix_world
        verts.extend([matrix@v.co for v in ob.data.vertices])
        slots=[]
        for mat in ob.data.materials:
            if mat not in materials:materials.append(mat)
            slots.append(materials.index(mat))
        for poly in ob.data.polygons:
            faces.append([offset+i for i in poly.vertices]);indices.append(slots[poly.material_index] if slots else 0);smooth.append(poly.use_smooth)
    me=bpy.data.meshes.new('RENDER_BATCH');me.from_pydata(verts,[],faces)
    for mat in materials:me.materials.append(mat)
    for face,idx,sm in zip(me.polygons,indices,smooth):face.material_index=idx;face.use_smooth=sm
    ob=bpy.data.objects.new('RENDER_BATCH',me);s.collection.objects.link(ob)
    if parent:ob.parent=parent
    for old in parts:bpy.data.objects.remove(old,do_unlink=True)
groups={}
for ob in list(bpy.data.objects):
    if ob.type=='MESH' and ob.parent and not ob.animation_data and not ob.children and visible(ob):groups.setdefault(ob.parent,[]).append(ob)
for parent,parts in groups.items():merge(parts,parent)
bpy.context.view_layer.update()
stat=[]
for ob in list(bpy.data.objects):
    if ob.type!='MESH' or not visible(ob):continue
    par=ob;animated=False
    while par:
        if par.animation_data:animated=True
        par=par.parent
    if not animated:stat.append(ob)
merge(stat)
bpy.context.view_layer.update()
s.display.render_aa='FXAA';s.render.image_settings.file_format='PNG';s.render.resolution_percentage=75
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['1','10']
a,b=map(int,args[:2]);s.frame_start=a;s.frame_end=b
(p/'frames').mkdir(exist_ok=True);s.render.filepath=str(p/'frames'/'frame_')
print('RENDER_BATCHED',len(bpy.data.objects),'FRAMES',a,b,flush=True)
bpy.ops.render.render(animation=True)
