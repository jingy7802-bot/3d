import bpy,runpy,json,math,csv
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
v=runpy.run_path(str(P/'validate_scene.py'),run_name='validation_module')
v['final_assets']()
s=bpy.context.scene;s.frame_set(1)
if not s.get('v2_air_dodge'):
    cc={fc.array_index:fc for fc in v['fcurve_list'](s.camera) if fc.data_path=='location'}
    for fc in cc.values():
        a,b=fc.evaluate(518),fc.evaluate(521)
        for f in [519,520]:fc.keyframe_points.insert(f,a+(b-a)*(f-518)/3,options={'FAST','REPLACE'})
        fc.update()
    v['air_dodge']()
if not s.get('v2_crowd_clearance'):
    cc={fc.array_index:fc for fc in v['fcurve_list'](s.camera) if fc.data_path=='location'}
    for left,right in [(5090,5100),(5118,5128)]:
        for fc in cc.values():
            a,b=fc.evaluate(left),fc.evaluate(right)
            for f in range(left+1,right):fc.keyframe_points.insert(f,a+(b-a)*(f-left)/(right-left),options={'FAST'})
            fc.update()
    for f in range(5011,5251):cc[1].keyframe_points.insert(f,0,options={'FAST'})
    cc[1].update();v['crowd_clearance']()
tree,names,dyn,stat=v['prepare_colliders']()
hits=[];asset_repairs=[]
changed=list(range(1,902))+list(range(2371,3092))+list(range(4970,5251))
for f in changed:
    s.frame_set(f)
    p=s.camera.matrix_world.translation.copy();hs=v['check_point'](p,tree,names,dyn)
    if hs:
        asset_repairs.append(f)
        for it in range(20):
            if not hs:break
            n,q,normal,d=min(hs,key=lambda h:h[3]);p=q+normal*.42
            hs=v['check_point'](p,tree,names,dyn)
        s.camera.location=p;s.camera.keyframe_insert(data_path='location',frame=f)
    for n,q,normal,d in hs:hits.append({'frame':f,'object':n,'distance':d})
report=json.loads((P/'collision_report.json').read_text())
report['supplemental_asset_check']={'frames_checked':len(changed),'scope':'Before release attached bombs; village carrier clothing. All other solids retained from full 5701-frame run.','static_mesh_count':len(stat),'dynamic_mesh_count':len(dyn),'collisions':hits}
report['remaining_collision_samples']=len(report['collisions'])+len(hits)
report['asset_repair_frames']=asset_repairs
report['status']='FAIL' if report['remaining_collision_samples'] else 'PASS_SAMPLED'
cc={fc.array_index:fc for fc in v['fcurve_list'](s.camera) if fc.data_path=='location'}
rows=[];prev=None
for f in range(1,s.frame_end+1):
    pos=Vector([cc[k].evaluate(f) for k in range(3)])
    speed=(pos-prev).length*30 if prev is not None else 0
    rows.append((f,(f-1)/30,*pos,speed));prev=pos
with (P/'camera_samples.csv').open('w') as fp:
    w=csv.writer(fp);w.writerow(['frame','seconds','x_m','y_m','height_m','speed_m_s']);w.writerows(rows)
report['min_speed_m_s']=min(r[-1] for r in rows[1:]);report['max_speed_m_s']=max(r[-1] for r in rows[1:])
(P/'collision_report.json').write_text(json.dumps(report,indent=2))
# Data-level invariants, not visual acceptance.
def oldframe(old):
    tm=[(1,0),(98,30),(232,59),(332,79),(410,103),(512,133),(564,146),(664,167),(900,190)]
    for (a,ta),(b,tb) in zip(tm,tm[1:]):
        if old<=b:return round(1+(ta+(old-a)/(b-a)*(tb-ta))*30)
checks={}
checks['fps_30']=s.render.fps==30
checks['frame_end']=s.frame_end
checks['single_camera']=s.camera.name
for label,n in [('pigeon','OPENING_PIGEON_ROOT'),('meng','OLD_MENG_ROOT'),('carrier','WUTONGGOU_WOMAN_CARRYING_WOUNDED_MAN_ROOT'),('wounded','WUTONGGOU_WOUNDED_MAN_ON_BACK_ROOT'),('box','RIVERBANK_HANDOFF_BOX')]:checks[label+'_exists']=n in bpy.data.objects
checks['surface_float_count']=len([o for o in bpy.data.objects if o.type=='EMPTY' and ('RIVER_SURFACE_FLOAT' in o.name or 'V2_FLOAT_' in o.name)])
checks['major_wader_count']=len([o for o in bpy.data.objects if o.type=='EMPTY' and 'CROWD_WADER' in o.name and o.name.endswith('_ROOT')])
checks['bank_runner_count']=len([o for o in bpy.data.objects if o.type=='EMPTY' and o.name.startswith('V2_BANK_RUN') and o.name.endswith('_ROOT')])
checks['aircraft_count']=len([o for o in bpy.data.objects if o.type=='EMPTY' and 'BOMBER' in o.name and o.name.endswith('_ROOT')])
checks['bomb_count']=len([o for o in bpy.data.objects if o.type=='EMPTY' and 'AIR_BOMB' in o.name and o.name.endswith('_ROOT')])
angles=[]
for f in range(oldframe(594),oldframe(650)+1):
    s.frame_set(f);p=s.camera.location;angles.append(math.atan2(p.y,p.x-250))
checks['orbit_start_degrees']=math.degrees(angles[0]);checks['orbit_end_degrees']=math.degrees(angles[-1]);checks['orbit_angular_travel_degrees']=sum(abs(math.degrees(math.atan2(math.sin(b-a),math.cos(b-a)))) for a,b in zip(angles,angles[1:]))
checks['runtime']=bpy.app.version_string;checks['blender_5_2_verified']=False
(P/'structure_checks.json').write_text(json.dumps(checks,indent=2))
# Record event tracks for editing and traceability.
with (P/'event_tracks.csv').open('w') as fp:
    w=csv.writer(fp);w.writerow(['object','track_start_frame','track_end_frame','channels'])
    for ob in bpy.data.objects:
        fcs=v['fcurve_list'](ob)
        if fcs:
            keys=[k.co.x for fc in fcs for k in fc.keyframe_points]
            if keys:w.writerow([ob.name,min(keys),max(keys),';'.join(sorted(set(fc.data_path for fc in fcs)))])
# Pack current scripts in engineering scene so delivery opens with matching source.
for f in ['battlefield_v2.py','validate_scene.py','render_previs.py','render_fast.py']:
    txt=bpy.data.texts.get(f) or bpy.data.texts.new(f);txt.clear();txt.write((P/f).read_text())
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'battlefield_v2.blend'))
print('FINAL_AUDIT',checks,'ADDITIONAL_COLLISIONS',hits,flush=True)
