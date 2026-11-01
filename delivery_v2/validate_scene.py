"""Run inside Blender after construction; physical mesh checks, camera bake and reports."""
import bpy, math, json, csv
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
OUT=Path(__file__).parent
RADIUS=.34

def fcurve_list(ob):
    if not ob.animation_data or not ob.animation_data.action:return []
    try:return list(ob.animation_data.action.fcurves)
    except AttributeError:
        return [fc for l in ob.animation_data.action.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]

def patch_ground():
    if bpy.context.scene.get('v2_ground_patched'):return
    bpy.context.scene['v2_ground_patched']=True
    terrain=bpy.data.objects['BATTLEFIELD_CONTINUOUS_MOUNTAIN_TERRAIN']
    for v in terrain.data.vertices:
        x,y,z=v.co
        if -195<x<355 and abs(y)<42:
            w=max(0,min(1,(42-abs(y))/8))
            if x<69: floor=0
            elif x<80:floor=-1.05*(x-69)/11
            elif x<188:floor=-1.05
            elif x<201:floor=-1.05*(201-x)/13
            else:floor=max(0,(x-230)*.018)
            v.co.z=z*(1-w)+floor*w
    terrain.data.update()
    for ob in bpy.data.objects:
        if 'BROAD_RIVERBED' in ob.name:
            for v in ob.data.vertices:v.co.z=-1.05
        if 'RIVERBED_CASUALTY' in ob.name or 'RIVER_EXTRA_BODY' in ob.name:
            if not ob.parent:ob.location.z=-.95
        if ob.type=='EMPTY' and not ob.parent and ob.name.endswith('_ROOT') and ob.location.x>230 and ob.location.z<.3:
            for fc in fcurve_list(ob):
                if fc.data_path=='location' and fc.array_index==2:
                    for k in fc.keyframe_points:
                        k.co.y+=max(0,(ob.location.x-230)*.018)
            ob.location.z+=max(0,(ob.location.x-230)*.018)
    # House blast is actual structural change, not smoke on an intact building.
    for ob in bpy.data.objects:
        if 'BREACHED_HOUSE' in ob.name or 'BREACHED_ROOF' in ob.name:
            base=ob.location.copy()
            for frame,dx,dy,dz in [(1,0,0,0),(2810,0,0,0),(2940,1,4,-1.3),(3100,2,6,-2.3)]:
                ob.location=base+Vector((dx,dy,dz));ob.keyframe_insert(data_path='location',frame=frame)
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()


def crowd_clearance():
    s=bpy.context.scene
    if s.get('v2_crowd_clearance'):return
    s['v2_crowd_clearance']=True
    cfg=json.loads(bpy.data.texts['V2_CONFIG'].as_string())
    tm=cfg['time_map']
    def tf(old):
        for (a,ta),(b,tb) in zip(tm,tm[1:]):
            if old<=b:return 1+(ta+(old-a)/(b-a)*(tb-ta))*30
    center=tf(664+(5110-5011)*236/690)
    lo=round(tf(564+(4970-4381)*100/630));hi=round(tf(664+(5250-5011)*236/690))
    width=65*(tm[-1][1]-tm[-2][1])/23
    fc=next(fc for fc in fcurve_list(s.camera) if fc.data_path=='location' and fc.array_index==2)
    vals=[(f,fc.evaluate(f)+cfg.get('crowd_clearance_height_m',1.5)*math.exp(-((f-center)/width)**2)) for f in range(lo,hi+1)]
    for f,z in vals:fc.keyframe_points.insert(f,z,options={'FAST'})
    fc.update()


def air_dodge():
    s=bpy.context.scene
    if s.get('v2_air_dodge'):return
    s['v2_air_dodge']=True
    cam=s.camera
    fc=next(fc for fc in fcurve_list(cam) if fc.data_path=='location' and fc.array_index==1)
    # A planned smooth lateral clearance arc under the bomb release corridor.
    cfg=json.loads(bpy.data.texts['V2_CONFIG'].as_string())
    factor=(cfg['time_map'][1][1]-cfg['time_map'][0][1])/30
    center=1+518*factor;width=16*factor
    lo,hi=round(1+479*factor),round(1+569*factor)
    values=[(f,fc.evaluate(f)-2*math.exp(-((f-center)/width)**2)) for f in range(lo,hi+1)]
    for f,y in values:fc.keyframe_points.insert(f,y,options={'FAST'})
    fc.update()


def final_assets():
    s=bpy.context.scene
    if s.get('v2_final_assets'):return
    s['v2_final_assets']=True
    tm=[(1,0),(98,30),(232,59),(332,79),(410,103),(512,133),(564,146),(664,167),(900,190)]
    def tf(old):
        for (a,ta),(b,tb) in zip(tm,tm[1:]):
            if old<=b:return 1+(ta+(old-a)/(b-a)*(tb-ta))*30
    for i in range(8):
        bomb=bpy.data.objects['V2_AIR_BOMB_%02d_ROOT'%i]
        plane=bpy.data.objects['JAPANESE_BOMBER_LEFT_NEAR_ROOT' if i%2==0 else 'JAPANESE_BOMBER_RIGHT_NEAR_ROOT']
        pcs={fc.array_index:fc for fc in fcurve_list(plane) if fc.data_path=='location'}
        release=tf(48+i*3)
        for f in range(1,int(release),6):
            bomb.location=tuple(pcs[k].evaluate(f)-(1.1 if k==2 else 0) for k in range(3))
            bomb.keyframe_insert(data_path='location',frame=f)
    import bmesh
    woman=bpy.data.objects['WUTONGGOU_WOMAN_CARRYING_WOUNDED_MAN_ROOT'];coll=woman.users_collection[0]
    cap=bpy.data.objects.get('WUTONGGOU_WOMAN_CARRYING_WOUNDED_MAN_CAP')
    if cap:cap.hide_render=True;cap.hide_viewport=True
    material=bpy.data.materials['BFP20_Weapon_Block']
    def part(name,loc,scale,kind):
        bm=bmesh.new()
        if kind=='ico':bmesh.ops.create_icosphere(bm,subdivisions=2,radius=1)
        else:bmesh.ops.create_cone(bm,segments=8,cap_ends=True,radius1=1,radius2=.7,depth=1)
        me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();me.materials.append(material)
        ob=bpy.data.objects.new(name,me);coll.objects.link(ob);ob.parent=woman;ob.location=loc;ob.scale=scale
    part('V2_WOMAN_HAIR',(-.06,0,1.73),(.24,.24,.18),'ico')
    part('V2_WOMAN_HAIR_BUN',(-.24,0,1.65),(.12,.12,.12),'ico')
    part('V2_WOMAN_COAT',(-.03,0,.65),(.33,.28,.55),'cone')
    s.frame_set(1);bpy.context.view_layer.update()


def ground_walkers():
    s=bpy.context.scene
    if s.get('v2_walkers_grounded'):return
    s['v2_walkers_grounded']=True
    ob=bpy.data.objects['BATTLEFIELD_CONTINUOUS_MOUNTAIN_TERRAIN']
    tree=BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[p.vertices[:] for p in ob.data.polygons])
    for actor in bpy.data.objects:
        if actor.type!='EMPTY' or actor.parent or not actor.name.endswith('_ROOT'):continue
        if any(k in actor.name for k in ['FLOAT','CASUALTY','PINNED','WOUNDED','BOMB','BOMBER','PIGEON','HIT','FALL']):continue
        fcs={fc.array_index:fc for fc in fcurve_list(actor) if fc.data_path=='location'}
        if 0 not in fcs:
            hit=tree.ray_cast(Vector((actor.location.x,actor.location.y,500)),Vector((0,0,-1)))
            if hit[0] is not None:actor.location.z=hit[0].z
            continue
        samples=[]
        for f in range(1,s.frame_end+1,6):
            x=fcs[0].evaluate(f);y=fcs[1].evaluate(f) if 1 in fcs else actor.location.y
            hit=tree.ray_cast(Vector((x,y,500)),Vector((0,0,-1)))
            if hit[0] is not None:samples.append((f,hit[0].z))
        # Replace just the root elevation; preserve world XY, yaw and limb performance.
        if 2 in fcs:
            action=actor.animation_data.action
            if hasattr(action,'fcurves'):action.fcurves.remove(fcs[2])
            else:
                for layer in action.layers:
                    for strip in layer.strips:
                        for bag in strip.channelbags:
                            if fcs[2] in list(bag.fcurves):bag.fcurves.remove(fcs[2]);break
        for f,z in samples:
            actor.location.z=z;actor.keyframe_insert(data_path='location',index=2,frame=f)
        for fc in fcurve_list(actor):
            if fc.data_path=='location' and fc.array_index==2:
                for k in fc.keyframe_points:k.interpolation='LINEAR'
    s.frame_set(1);bpy.context.view_layer.update()


def prepare_colliders():
    # All rendered mesh solids participate. Explicit optical effects are non-solid.
    skip=['HIGH_CLOUD','SMOKE','DUST','BLAST_FLASH','BULLET','TRACER','SPLASH','WATER_BULLET','BLOOD_TINT','CAMERA_PATH','DIRECTION_MARKER','BROAD_RIVER_SURFACE','WIDE_OPEN_CHARGE_ROAD','GRASS','FUTURE','TACTICAL','MUZZLE','AIR_BOMB_MAIN_IMPACT','AIR_BOMB_SECONDARY','BLAST_EVENT','AIR_IMPACT','BLAST_NEAR','BLAST_ROCK','BLAST_REAR','BLAST_FAR','GROUND_IMPACT','POST_EXIT_BLAST']
    stat=[];dyn=[];verts=[];faces=[];names=[]
    for ob in bpy.data.objects:
        if ob.type!='MESH' or ob.hide_render or any(c.hide_render for c in ob.users_collection):continue
        if any(k in ob.name for k in skip):ob['collision_role']='non_solid_optical_or_surface';continue
        ob['collision_role']='solid'
        root=ob
        animated=False
        while root:
            if root.animation_data:animated=True
            root=root.parent
        if animated:
            mesh=ob.data
            tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons],all_triangles=False)
            dyn.append((ob,tree));continue
        n=len(verts);verts.extend([ob.matrix_world@v.co for v in ob.data.vertices])
        for p in ob.data.polygons:faces.append([n+i for i in p.vertices]);names.append(ob.name)
        stat.append(ob.name)
    tree=BVHTree.FromPolygons(verts,faces,all_triangles=False)
    return tree,names,dyn,stat

def check_point(p,tree,names,dyn):
    hits=[]
    q,n,i,d=tree.find_nearest(p)
    if q is not None:
        # Signed closest surface; closed solids and upward terrain normals.
        signed=(p-q).dot(n)
        if d<RADIUS or signed<-.005:hits.append((names[i],q,n,d if signed>=0 else -d))
    for ob,t in dyn:
        mw=ob.matrix_world
        # broad phase world sphere based on dimensions, then local mesh query
        center=mw.translation
        if (p-center).length>max(ob.dimensions)*1.1+RADIUS+1:continue
        inv=mw.inverted_safe();local=inv@p
        q,n,i,d=t.find_nearest(local)
        if q is None:continue
        worldq=mw@q;worldn=(mw.to_3x3().inverted_safe().transposed()@n).normalized()
        dist=(p-worldq).length;sg=(p-worldq).dot(worldn)
        if dist<RADIUS or sg<-.005:hits.append((ob.name,worldq,worldn,dist if sg>=0 else -dist))
    return hits

def validate():
    global RADIUS
    s=bpy.context.scene;cam=s.camera
    RADIUS=s.get('camera_safety_radius_m',.22)+s.get('camera_margin_m',.12)
    patch_ground()
    final_assets()
    ground_walkers()
    air_dodge()
    crowd_clearance()
    tree,names,dyn,static=prepare_colliders()
    print('COLLIDERS',len(static),len(dyn),flush=True)
    original=[];adjusted=[];unresolved=[];corrections=[]
    # Initial sampling every 3 frames, bake at this rate; final checks every frame below.
    for f in range(1,s.frame_end+1,3):
        s.frame_set(f);p=cam.matrix_world.translation.copy();q=cam.rotation_quaternion.copy()
        original.append((f,p.copy(),q))
        for it in range(16):
            h=check_point(p,tree,names,dyn)
            if not h:break
            # Project along the actual outward surface normal, choosing largest violation.
            name,near,n,d=min(h,key=lambda h:h[3]);p=near+n*(RADIUS+.10)
        if (p-original[-1][1]).length>.01:corrections.append({'frame':f,'distance':(p-original[-1][1]).length})
        adjusted.append((f,p,q))
        if f%300==1:print('PATH',f,'adjusted',len(corrections),flush=True)
    # Retain orientation, bake positions; linear interpolation prevents Bezier overshoot.
    cam.animation_data_clear()
    for f,p,q in adjusted:
        cam.location=p;cam.rotation_quaternion=q
        cam.keyframe_insert(data_path='location',frame=f);cam.keyframe_insert(data_path='rotation_quaternion',frame=f)
    for fc in fcurve_list(cam):
        for k in fc.keyframe_points:k.interpolation='LINEAR'
    rows=[];last=None;minspeed=1e9;maxspeed=0;final_poses=[];repair_frames=[]
    for f in range(1,s.frame_end+1):
        s.frame_set(f);p=cam.matrix_world.translation.copy()
        h=check_point(p,tree,names,dyn)
        if h:repair_frames.append(f)
        for iteration in range(24):
            if not h:break
            name,near,n,d=min(h,key=lambda h:h[3]);p=near+n*(RADIUS+.08)
            h=check_point(p,tree,names,dyn)
        q=cam.rotation_quaternion.copy()
        focus=cam.data.dof.focus_object
        if f in repair_frames and focus:
            q=(focus.matrix_world.translation-p).to_track_quat('-Z','Y')
            if q.dot(cam.rotation_quaternion)<0:q.negate()
        final_poses.append((f,p.copy(),q))
        for name,near,n,d in h:unresolved.append({'frame':f,'object':name,'signed_surface_distance':round(d,5)})
        speed=(p-last).length*30 if last else 0
        if last:minspeed=min(minspeed,speed);maxspeed=max(maxspeed,speed)
        rows.append((f,(f-1)/30,p.x,p.y,p.z,speed));last=p
        if f%600==0:print('VERIFY',f,'hits',len(unresolved),flush=True)
    cam.animation_data_clear()
    for f,p,q in final_poses:
        cam.location=p;cam.rotation_quaternion=q
        cam.keyframe_insert(data_path='location',frame=f);cam.keyframe_insert(data_path='rotation_quaternion',frame=f)
    for fc in fcurve_list(cam):
        for k in fc.keyframe_points:k.interpolation='LINEAR'
    with (OUT/'camera_samples.csv').open('w') as fp:
        w=csv.writer(fp);w.writerow(['frame','seconds','x_m','y_m','height_m','speed_m_s']);w.writerows(rows)
    report={'runtime':bpy.app.version_string,'target_version_verified':False,'camera_radius_m':s.get('camera_safety_radius_m',.22),'safety_margin_m':s.get('camera_margin_m',.12),'static_mesh_count':len(static),'dynamic_mesh_count':len(dyn),'temporal_sample':'every output frame (30 fps), not continuous swept-volume proof','frames_checked':len(rows),'corrections':corrections,'per_frame_repairs':repair_frames,'remaining_collision_samples':len(unresolved),'collisions':unresolved,'min_speed_m_s':minspeed,'max_speed_m_s':maxspeed,'status':'PASS_SAMPLED' if not unresolved else 'FAIL','limitations':['Visibility and action readability require rendered review.','Nearest surface normal sign is conservative for intersecting mesh solids.','No subframe swept-volume verification.']}
    (OUT/'collision_report.json').write_text(json.dumps(report,indent=2))
    # Bounding box/frustum coverage and occlusion ray evidence for principal events.
    beats=[('Pigeon',22,'OPENING_PIGEON_BODY'),('Aircraft',52,'JAPANESE_BOMBER_LEFT_NEAR_FUSELAGE'),('JP fire',118,'JP_CLOSE_REAR_SHOOTER_A_TORSO'),('CN fire',172,'CN_ROCK_COVER_SECOND_SHOOTER_TORSO'),('Rescue',302,'CN_FOREST_RESCUER_TORSO'),('Doorway',370,'WUTONGGOU_WOMAN_CARRYING_WOUNDED_MAN_TORSO'),('Water',450,'RIVER_SUPPORTING_SOLDIER_TORSO'),('Box',546,'RIVERBANK_HANDOFF_BOX'),('Meng back',594,'OLD_MENG_TORSO'),('Meng front',650,'OLD_MENG_HEAD')]
    tm=[(1,0),(98,30),(232,59),(332,79),(410,103),(512,133),(564,146),(664,167),(900,190)]
    def frame(old):
        for (a,ta),(b,tb) in zip(tm,tm[1:]):
            if old<=b:return round(1+(ta+(old-a)/(b-a)*(tb-ta))*30)
    coverage=[]
    for title,old,n in beats:
        f=frame(old);s.frame_set(f);ob=bpy.data.objects.get(n)
        if not ob:continue
        pts=[world_to_camera_view(s,cam,ob.matrix_world@Vector(v)) for v in ob.bound_box]
        center=ob.matrix_world.translation;delta=center-cam.matrix_world.translation
        dg=bpy.context.evaluated_depsgraph_get();hit=s.ray_cast(dg,cam.matrix_world.translation,delta.normalized(),distance=delta.length-.02)
        coverage.append({'beat':title,'frame':f,'object':n,'bbox_projected_height':max(p.y for p in pts)-min(p.y for p in pts),'in_frustum':any(0<p.x<1 and 0<p.y<1 and p.z>0 for p in pts),'first_occluder':hit[4].name if hit[0] else None,'manual_acceptance':'PENDING'})
    (OUT/'visibility_report.json').write_text(json.dumps(coverage,indent=2))
    s.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'battlefield_v2.blend'))
    print('VALIDATION_DONE',len(unresolved),flush=True)

if __name__=='__main__':validate()
