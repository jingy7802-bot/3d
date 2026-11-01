import bpy,json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
p=Path(__file__).parent;s=bpy.context.scene;cam=s.camera
metrics=json.loads((p/'visibility_report.json').read_text())
for row in metrics:
    s.frame_set(row['frame']);ob=bpy.data.objects[row['object']]
    points=[world_to_camera_view(s,cam,ob.matrix_world@Vector(v)) for v in ob.bound_box]
    row['bbox_projected_height']=max(v.y for v in points)-min(v.y for v in points)
    row['in_frustum']=any(0<v.x<1 and 0<v.y<1 and v.z>0 for v in points)
    d=ob.matrix_world.translation-cam.matrix_world.translation
    hit=s.ray_cast(bpy.context.evaluated_depsgraph_get(),cam.matrix_world.translation,d.normalized(),distance=d.length-.02)
    row['first_occluder']=hit[4].name if hit[0] else None
(p/'visibility_report.json').write_text(json.dumps(metrics,indent=2))
for f in ['battlefield_v2.py','validate_scene.py','render_fast.py','render_previs.py','README_运行与验收.md','验收记录.md','collision_report.json','structure_checks.json','visibility_report.json','old_meng_os.srt','video_validation.json','repeatability_check.json']:
    t=bpy.data.texts.get(f) or bpy.data.texts.new(f);t.clear();t.write((p/f).read_text())
s['delivery_status']='V2 implementation draft; final storyboard acceptance NOT PASSED; see 验收记录.md'
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(p/'battlefield_v2.blend'))
print('SEALED_PROJECT',flush=True)
