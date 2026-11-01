"""blender -b battlefield_v2.blend --python render_previs.py -- [checkpoints|full]"""
import bpy,sys
from pathlib import Path
s=bpy.context.scene
out=Path(__file__).parent
s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100
mode=sys.argv[-1]
if mode=='full':
    (out/'frames').mkdir(exist_ok=True)
    s.render.filepath=str(out/'frames'/'frame_');s.render.use_file_extension=True
    bpy.ops.render.render(animation=True)
else:
    (out/'checkpoints').mkdir(exist_ok=True)
    frames=[1,196,400,700,880,1050,1220,1440,1600,1771,1950,2150,2290,2520,2630,2720,2800,2930,3091,3280,3450,3660,3900,4050,4230,4381,4650,4770,4890,5011,5300,5490,5701]
    for f in frames:
        s.frame_set(f);s.render.filepath=str(out/'checkpoints'/('%05d.png'%f));bpy.ops.render.render(write_still=True)
