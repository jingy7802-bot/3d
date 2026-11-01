import bpy,json
from pathlib import Path
s=bpy.context.scene
for n in ['WOODLAND_BOULDER_00_01','OLD_MENG_ROOT','OLD_MENG_HEAD','OLD_MENG_TORSO']:
 ob=bpy.data.objects[n];print(n,list(ob.matrix_world.translation),list(ob.dimensions))
for f in [1031,2191,2722,3444,4246,4923]:
 s.frame_set(f);c=s.camera;print(f,'CAM',list(c.location),'Q',list(c.rotation_quaternion))
print('ACTORS',len([o for o in bpy.data.objects if o.name.endswith('_ROOT') and o.type=='EMPTY']))
