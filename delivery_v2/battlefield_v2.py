# -*- coding: utf-8 -*-
"""
Battlefield One-Take Previs V2 implementation draft.
Baseline: user requirements V1.0; original attachment V1.2 remains unchanged.
Runtime tested: Blender 4.3.2. Blender 5.2.x is NOT verified.
Default master timeline: 190 seconds, 30 FPS; one active animated camera.
Entry point at file end: main_v2(), then companion validate_scene.py.
Edit CFG and V2_KEYS near the lower part of this file for pacing and camera.
Construction helpers inherited from V1.2 precede the V2 implementation section.
See 验收记录.md for tests and unresolved acceptance criteria.
"""

import bpy
import math
import random
import traceback
import os
from mathutils import Vector, Quaternion

# ============================================================
# CONFIG
# ============================================================

VERSION = "V2.0"
FPS = 30
FRAME_START = 1
FRAME_END = 900
SEED = 20261030
random.seed(SEED)

COLLECTIONS = [
    "BFP_V20_01_LAND",
    "BFP_V20_02_FOREST",
    "BFP_V20_03_RAVINE",
    "BFP_V20_04_VILLAGE",
    "BFP_V20_05_RIVER",
    "BFP_V20_06_WEST_PASS",
    "BFP_V20_07_WIDE_ROAD",
    "BFP_V20_08_FUTURE_MARKERS",
    "BFP_V20_09_CAMERA",
    "BFP_V20_10_PATH_DEBUG",
    "BFP_V20_11_LIGHTS",
    "BFP_V20_12_SMOKE_PLACEHOLDERS",
    "BFP_V20_13_GROUND_GRASS",
    "BFP_V20_14_TACTICAL_MARKERS",
    "BFP_V20_15_GROUND_ROCKS",
    "BFP_V20_16_CHARACTERS",
    "BFP_V20_17_PROPS",
    "BFP_V20_18_BATTLE_FX",
    "BFP_V20_19_STORYBOARD_ACTIONS",
    "BFP_V20_20_TERRAIN_REFERENCE",
]

REPORT = []
STATUS = {}
MATS = {}


# ============================================================
# REPORT / COLLECTION MANAGEMENT
# ============================================================

def log(msg):
    REPORT.append(str(msg))
    print("[BFP V2]", msg)


def get_script_directory():
    """Resolve the folder containing this script, including Blender Text Editor execution."""
    candidates = []
    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass
    try:
        for text_block in bpy.data.texts:
            fp = getattr(text_block, "filepath", "")
            if fp and ("V1_2" in text_block.name or fp.lower().endswith(".py")):
                resolved = bpy.path.abspath(fp)
                candidates.append(os.path.dirname(os.path.abspath(resolved)))
    except Exception:
        pass
    try:
        if bpy.data.filepath:
            candidates.append(os.path.dirname(os.path.abspath(bpy.data.filepath)))
    except Exception:
        pass
    candidates.extend([os.getcwd(), bpy.path.abspath("//")])
    for folder in candidates:
        if folder and os.path.isdir(folder):
            return folder
    return os.getcwd()


def get_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if bpy.context.scene.collection.children.get(coll.name) is None:
        try:
            bpy.context.scene.collection.children.link(coll)
        except RuntimeError:
            pass
    return coll


def clear_generated_collections():
    """Remove only V1.2-generated collections so every older version remains recoverable."""
    for name in list(COLLECTIONS):
        coll = bpy.data.collections.get(name)
        if coll is None:
            continue
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        try:
            bpy.data.collections.remove(coll, do_unlink=True)
        except Exception:
            try:
                bpy.data.collections.remove(coll)
            except Exception:
                pass


def hide_legacy_versions():
    """Hide older generated versions without deleting their collections or objects."""
    prefixes = (
        "BFP_V02_", "BFP_V03_", "BFP_V04_", "BFP_V05_",
        "BFP_V06_", "BFP_V07_", "BFP_V08_", "BFP_V09_",
        "BFP_V10_", "BFP_V11_", "BFP_01_", "BFP_02_",
        "BFP_03_", "BFP_04_", "BFP_05_"
    )
    for coll in bpy.data.collections:
        if coll.name.startswith(prefixes):
            coll.hide_viewport = True
            coll.hide_render = True



def run_stage(name, func):
    log("START " + name)
    try:
        result = func()
        STATUS[name] = "PASS"
        log("PASS " + name)
        return result
    except Exception as exc:
        STATUS[name] = "FAIL: " + repr(exc)
        log("FAIL " + name + " | " + repr(exc))
        log(traceback.format_exc())
        return None


# ============================================================
# MATERIALS
# ============================================================

def mat(name, color, roughness=0.9, alpha=1.0, emission=0.0):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.diffuse_color = (color[0], color[1], color[2], alpha)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if emission > 0:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (color[0], color[1], color[2], 1.0)
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emission
    if alpha < 1:
        try:
            material.surface_render_method = 'DITHERED'
        except Exception:
            pass
    return material


def create_materials():
    global MATS
    MATS = {
        "ground": mat("BFP20_Land_Green", (0.25, 0.34, 0.22)),
        "slope": mat("BFP20_Slope_Olive", (0.30, 0.35, 0.23)),
        "mountain": mat("BFP20_Mountain_Distant", (0.22, 0.29, 0.25)),
        "rock": mat("BFP20_Rock_Gray", (0.39, 0.41, 0.40)),
        "rock_light": mat("BFP20_Rock_Light", (0.52, 0.51, 0.47)),
        "trunk": mat("BFP20_Tree_Trunk", (0.24, 0.17, 0.11)),
        "leaf": mat("BFP20_Tree_Canopy", (0.10, 0.24, 0.12)),
        "leaf_light": mat("BFP20_Tree_Canopy_Light", (0.19, 0.34, 0.16)),
        "branch": mat("BFP20_Branch", (0.20, 0.15, 0.10)),
        "water": mat("BFP20_River_Water", (0.10, 0.38, 0.53), alpha=0.48),
        "riverbed": mat("BFP20_River_Bed", (0.23, 0.28, 0.26)),
        "road": mat("BFP20_Wide_Dirt_Road", (0.43, 0.39, 0.29)),
        "road_edge": mat("BFP20_Road_Edge", (0.31, 0.32, 0.27)),
        "smoke": mat("BFP20_Blast_Smoke", (0.48, 0.49, 0.48), alpha=0.48),
        "dust": mat("BFP20_Blast_Dust", (0.55, 0.49, 0.39), alpha=0.58),
        "grass": mat("BFP20_Dry_Grass", (0.55, 0.48, 0.29)),
        "grass_light": mat("BFP20_Dry_Grass_Light", (0.68, 0.59, 0.38)),
        "ruin": mat("BFP20_Ruin_Wall", (0.47, 0.39, 0.28)),
        "roof": mat("BFP20_Ruin_Roof", (0.28, 0.27, 0.23)),
        "path": mat("BFP20_Camera_Path_Yellow", (1.0, 0.68, 0.06), emission=0.8),
        "marker": mat("BFP20_Future_Marker_Orange", (1.0, 0.25, 0.04), emission=0.8),
        "cloud": mat("BFP20_Cloud_Gray", (0.63, 0.67, 0.69)),
        "cn_soldier": mat("BFP20_Chinese_Soldier_Block", (0.30, 0.36, 0.42)),
        "jp_soldier": mat("BFP20_Japanese_Soldier_Block", (0.52, 0.43, 0.28)),
        "old_meng": mat("BFP20_Old_Meng_Block", (0.17, 0.20, 0.23)),
        "casualty_cn": mat("BFP20_Chinese_Casualty_Block", (0.22, 0.27, 0.31)),
        "casualty_jp": mat("BFP20_Japanese_Casualty_Block", (0.38, 0.32, 0.23)),
        "casualty_charred": mat("BFP20_Charred_Casualty_Block", (0.12, 0.13, 0.13)),
        "blood_water": mat("BFP20_River_Blood_Tint", (0.25, 0.055, 0.045), alpha=0.42),
        "weapon": mat("BFP20_Weapon_Block", (0.10, 0.12, 0.14)),
        "grenade": mat("BFP20_Grenade_Charge_Block", (0.72, 0.22, 0.08)),
        "box": mat("BFP20_Handoff_Box_Block", (0.46, 0.31, 0.17)),
        "aircraft": mat("BFP20_Japanese_Bomber_Block", (0.31, 0.37, 0.31)),
        "bird": mat("BFP20_Pigeon_Block", (0.62, 0.64, 0.62)),
        "tracer": mat("BFP20_Bullet_Tracer", (1.0, 0.70, 0.20), emission=1.8),
        "blast": mat("BFP20_Blast_Flash", (1.0, 0.30, 0.04), emission=2.5),
    }


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def move_obj(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def cube(name, loc, dims, material, coll, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    obj.rotation_euler = rot
    if material:
        obj.data.materials.append(material)
    return move_obj(obj, coll)


def ico(name, loc, scale, material, coll, sub=1, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rot
    if material:
        obj.data.materials.append(material)
    return move_obj(obj, coll)


def cylinder(name, loc, radius, depth, material, coll, vertices=7, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=loc
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rot
    if material:
        obj.data.materials.append(material)
    return move_obj(obj, coll)


def beam_between(name, a, b, radius, material, coll):
    a = Vector(a)
    b = Vector(b)
    delta = b - a
    obj = cylinder(
        name,
        (a + b) * 0.5,
        radius,
        delta.length,
        material,
        coll,
        vertices=6
    )
    obj.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()
    return obj


def empty(name, loc, coll, display='SPHERE', size=1.0):
    obj = bpy.data.objects.new(name, None)
    coll.objects.link(obj)
    obj.location = loc
    obj.empty_display_type = display
    obj.empty_display_size = size
    return obj


def ribbon(name, points, half_width, z, material, coll):
    verts, faces = [], []
    pts = [Vector((p[0], p[1], z)) for p in points]
    for i, p in enumerate(pts):
        prev_p = pts[max(0, i - 1)]
        next_p = pts[min(len(pts) - 1, i + 1)]
        tangent = Vector((next_p.x - prev_p.x, next_p.y - prev_p.y, 0))
        if tangent.length < 0.001:
            tangent = Vector((1, 0, 0))
        tangent.normalize()
        side = Vector((-tangent.y, tangent.x, 0))
        left = p + side * half_width
        right = p - side * half_width
        verts.extend([(left.x, left.y, left.z), (right.x, right.y, right.z)])
    for i in range(len(pts) - 1):
        j = i * 2
        faces.append((j, j + 1, j + 3, j + 2))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# ============================================================
# LANDSCAPE: OPEN SKY, DISTANT HORIZON, LOW/MID RELIEF
# ============================================================

def build_landscape():
    """Large continuous mountain terrain based on the supplied Yimeng-style aerial reference."""
    land = get_collection("BFP_V20_01_LAND")

    xmin, xmax = -420.0, 620.0
    ymin, ymax = -320.0, 320.0
    nx, ny = 131, 81

    # Main low corridor follows the complete story route; surrounding ridges rise on both sides.
    story_line = [
        (-285, -30), (-220, -12), (-178, -8), (-145, -6), (-108, 0),
        (-70, 6), (-35, 0), (0, 2), (38, -7), (78, -2), (118, 5),
        (158, -5), (198, 5), (250, 0), (320, 0), (410, 0), (500, 0)
    ]
    river_line = [
        (72, -4), (88, 0), (104, 8), (122, 12), (140, 6),
        (158, -8), (176, -2), (196, 8)
    ]

    def seg_distance(px, py, a, b):
        ax, ay = a; bx, by = b
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        if den < 1e-8:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def line_distance(px, py, pts):
        return min(seg_distance(px, py, pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    # Elliptical mountain masses: center x/y, horizontal radii, height, rotation.
    peaks = [
        (-310, -165, 105, 72, 56, -0.28),
        (-260, 145, 112, 78, 48, 0.22),
        (-165, -170, 95, 70, 52, 0.42),
        (-80, 155, 118, 78, 56, -0.34),
        (45, -165, 110, 72, 50, 0.30),
        (165, 165, 120, 82, 58, -0.24),
        (285, -160, 120, 84, 60, 0.26),
        (430, 150, 132, 92, 64, -0.22),
        (505, -145, 120, 86, 48, 0.18),
    ]

    verts = []
    for j in range(ny):
        y = ymin + (ymax - ymin) * j / (ny - 1)
        for i in range(nx):
            x = xmin + (xmax - xmin) * i / (nx - 1)
            h = 1.2
            for cx, cy, sx, sy, amp, ang in peaks:
                dx, dy = x - cx, y - cy
                ca, sa = math.cos(ang), math.sin(ang)
                rx = (dx * ca - dy * sa) / sx
                ry = (dx * sa + dy * ca) / sy
                h += amp * math.exp(-1.25 * (rx * rx + ry * ry))

            # Long ridgelines add connected mountain shoulders, not isolated dome hills.
            ridge_a = abs(y - (0.31 * (x + 120) - 105))
            ridge_b = abs(y - (-0.24 * (x - 110) + 115))
            h += 17.0 * math.exp(-((ridge_a / 26.0) ** 2))
            h += 13.0 * math.exp(-((ridge_b / 34.0) ** 2))

            # Subtle low-frequency terrain breakup.
            h += 1.6 * math.sin(x * 0.027 + y * 0.012) * math.cos(y * 0.021 - x * 0.008)
            h += 0.7 * math.sin(x * 0.061 + y * 0.044)

            # Keep the story corridor open and walkable while the surrounding mountains remain tall.
            d_story = line_distance(x, y, story_line)
            flatten = math.exp(-((d_story / 27.0) ** 2))
            h = h * (1.0 - 0.88 * flatten) + 0.32 * (0.88 * flatten)

            # A broad depressed river valley sits inside the terrain; the water and riverbed are separate meshes.
            d_river = line_distance(x, y, river_line)
            river_cut = 5.8 * math.exp(-((d_river / 47.0) ** 2))
            h -= river_cut
            h = max(-4.0, h)
            verts.append((x, y, h))

    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            b = a + 1
            c = a + nx + 1
            d = a + nx
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("BFP_V20_CONTINUOUS_MOUNTAIN_TERRAIN_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(MATS["ground"])
    mesh.materials.append(MATS["slope"])
    mesh.materials.append(MATS["mountain"])
    mesh.update()
    terrain = bpy.data.objects.new("BATTLEFIELD_CONTINUOUS_MOUNTAIN_TERRAIN", mesh)
    land.objects.link(terrain)

    for poly in mesh.polygons:
        z = sum(mesh.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
        if z > 27.0:
            poly.material_index = 2
        elif z > 9.0:
            poly.material_index = 1
        else:
            poly.material_index = 0
        poly.use_smooth = True

    # Exposed rock spines echo the broken, steep-sided ridges in the supplied terrain reference.
    spine_specs = [
        ((-235, 92, 22), (38, 18, 25), (0.08, -0.18, 0.32)),
        ((-82, -92, 24), (44, 20, 30), (-0.08, 0.16, -0.24)),
        ((72, 92, 28), (43, 19, 34), (0.04, -0.22, 0.18)),
        ((205, -100, 27), (48, 22, 35), (0.12, 0.18, -0.32)),
        ((350, 96, 32), (52, 23, 42), (-0.12, 0.2, 0.28)),
        ((470, -95, 26), (46, 21, 34), (0.08, -0.15, -0.18)),
    ]
    for i, (loc, scale, rot) in enumerate(spine_specs):
        ico("CONTINUOUS_ROCK_SPINE_%02d" % i, loc, scale, MATS["rock"], land, sub=2, rot=rot)

    # Distant mountain silhouettes extend the environment beyond the immediate action corridor.
    for i, (x, y, z, sx, sy, sz) in enumerate([
        (-360, -245, 48, 90, 52, 48), (-260, 240, 55, 82, 48, 50),
        (-70, -250, 58, 95, 56, 58), (110, 250, 65, 96, 54, 62),
        (310, -250, 62, 100, 58, 60), (500, 235, 72, 112, 60, 70),
    ]):
        ico("DISTANT_MOUNTAIN_MASS_%02d" % i, (x, y, z), (sx, sy, sz),
            MATS["mountain"], land, sub=2)

    # Clouds remain high above the terrain and do not reduce the newly expanded airspace.
    for i in range(34):
        x = random.uniform(-330, -120)
        y = random.uniform(-150, 150)
        z = random.uniform(115, 165)
        ico("HIGH_CLOUD_%03d" % i, (x, y, z),
            (random.uniform(10, 23), random.uniform(8, 18), random.uniform(3, 8)),
            MATS["cloud"], land, sub=1)

    log("Terrain mesh created: %d vertices / %d faces, expanded mountain basin." % (len(verts), len(faces)))


# ============================================================
# FOREST: TREE GATES, LOW BRANCHES, CLOSE PASSES
# ============================================================

FOREST_ROUTE = [
    (-166, -8, 1.6), (-160, -18, 1.45), (-151, -28, 1.4),
    (-143, -18, 1.25), (-137, 0, 1.2), (-132, 18, 1.2),
    (-126, 26, 1.15), (-120, 18, 1.2), (-116, 0, 1.2),
    (-111, -18, 1.1), (-106, -26, 1.05), (-102, -8, 1.25),
    (-98, 8, 1.35), (-94, 2, 1.35), (-90, -4, 1.45), (-81, 5, 1.4)
]


def build_forest():
    forest = get_collection("BFP_V20_02_FOREST")
    random.seed(SEED + 61)

    route_xy = [(p[0], p[1]) for p in FOREST_ROUTE]

    def point_segment_distance(px, py, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        denom = dx * dx + dy * dy
        if denom < 0.0001:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
        qx, qy = ax + t * dx, ay + t * dy
        return math.hypot(px - qx, py - qy)

    def route_clearance(px, py):
        return min(
            point_segment_distance(px, py, route_xy[i], route_xy[i + 1])
            for i in range(len(route_xy) - 1)
        )

    def create_tree(index, x, y, forced_scale=None):
        height = random.uniform(7.0, 13.5) if forced_scale is None else forced_scale
        trunk_radius = random.uniform(0.22, 0.42)
        lean_x = random.uniform(-0.08, 0.08)
        lean_y = random.uniform(-0.08, 0.08)

        cylinder(
            "WOODLAND_TRUNK_%03d" % index,
            (x, y, height * 0.37),
            trunk_radius,
            height * 0.74,
            MATS["trunk"],
            forest,
            vertices=7,
            rot=(lean_x, lean_y, random.uniform(-0.05, 0.05))
        )

        species = random.choice(("broadleaf", "broadleaf", "conifer"))
        if species == "broadleaf":
            crown_z = height * random.uniform(0.76, 0.9)
            crown_scale = random.uniform(2.5, 4.0)
            # Uneven crown lobes create a broken, natural canopy silhouette.
            for lobe in range(random.randint(2, 4)):
                ico(
                    "WOODLAND_BROAD_CROWN_%03d_%02d" % (index, lobe),
                    (
                        x + random.uniform(-1.5, 1.5),
                        y + random.uniform(-1.3, 1.3),
                        crown_z + random.uniform(-0.9, 0.9)
                    ),
                    (
                        crown_scale * random.uniform(0.65, 1.0),
                        crown_scale * random.uniform(0.6, 1.0),
                        random.uniform(2.0, 3.3)
                    ),
                    MATS["leaf"] if lobe % 3 else MATS["leaf_light"],
                    forest,
                    sub=1
                )
        else:
            # Layered irregular conifer masses, not identical cone rows.
            for layer, factor in enumerate((1.0, 0.78, 0.55)):
                ico(
                    "WOODLAND_CONIFER_CROWN_%03d_%02d" % (index, layer),
                    (
                        x + random.uniform(-0.45, 0.45),
                        y + random.uniform(-0.45, 0.45),
                        height * (0.62 + layer * 0.105)
                    ),
                    (
                        random.uniform(2.2, 3.4) * factor,
                        random.uniform(2.0, 3.0) * factor,
                        random.uniform(2.2, 3.3) * factor
                    ),
                    MATS["leaf"] if layer else MATS["leaf_light"],
                    forest,
                    sub=1
                )

        if random.random() < 0.42:
            branch_height = height * random.uniform(0.35, 0.58)
            branch_end = (
                x + random.uniform(-3.0, 3.0),
                y + random.uniform(-3.0, 3.0),
                branch_height + random.uniform(-0.6, 0.8)
            )
            beam_between(
                "WOODLAND_LOW_BRANCH_%03d" % index,
                (x, y, branch_height),
                branch_end,
                random.uniform(0.10, 0.17),
                MATS["branch"],
                forest
            )

    # Trees grow in uneven clusters with overlapping crowns and irregular clearings.
    # There are no paired tree gates and no continuous tree-lined road.
    cluster_centers = [
        (-171, -25), (-157, 9), (-143, -25), (-130, 18),
        (-113, -22), (-98, 22), (-83, -20), (-68, 15),
        (-136, 0), (-101, -4), (-76, 29)
    ]
    tree_positions = []
    for cluster_index, center in enumerate(cluster_centers):
        target_count = random.randint(9, 14)
        accepted = 0
        attempts = 0
        while accepted < target_count and attempts < target_count * 12:
            attempts += 1
            x = random.gauss(center[0], random.uniform(4.0, 7.0))
            y = random.gauss(center[1], random.uniform(3.5, 6.5))
            if x < -192 or x > -51 or y < -39 or y > 39:
                continue
            if route_clearance(x, y) < random.uniform(1.8, 2.7):
                continue
            if any(math.hypot(x - ox, y - oy) < 2.4 for ox, oy in tree_positions):
                continue
            tree_positions.append((x, y))
            accepted += 1

    # A few close trunks sit at the edges of the flight path to force readable passes.
    close_tree_positions = [
        (-166, -17), (-150, -21), (-136, -7), (-124, 2),
        (-113, 11), (-101, 4), (-88, 16), (-78, 2), (-67, -11)
    ]
    for x, y in close_tree_positions:
        if route_clearance(x, y) > 2.1 and all(
            math.hypot(x - ox, y - oy) > 2.2 for ox, oy in tree_positions
        ):
            tree_positions.append((x, y))

    for index, (x, y) in enumerate(tree_positions):
        create_tree(index, x, y)

    # More distant trees merge the separate clusters into a continuous woodland mass.
    for i in range(42):
        x = random.uniform(-198, -48)
        y = random.choice((-1, 1)) * random.uniform(34, 62)
        create_tree(500 + i, x, y, random.uniform(8.0, 15.0))

    # Uneven forest floor: low earth shoulders and shallow dips.
    ground_forms = [
        (-160, -3, (10, 7, 0.8)),
        (-139, 10, (8, 6, 0.65)),
        (-112, -7, (9, 6, 0.9)),
        (-91, 16, (10, 7, 0.75)),
        (-72, -12, (8, 6, 0.7))
    ]
    for i, (x, y, scale) in enumerate(ground_forms):
        ico(
            "WOODLAND_UNEVEN_GROUND_%02d" % i,
            (x, y, -0.35),
            scale,
            MATS["slope"],
            forest,
            sub=1
        )

    # Shrubs, roots and fallen trunks break up the gaps between trees and rocks.
    for i in range(64):
        x = random.uniform(-187, -55)
        y = random.uniform(-32, 32)
        if route_clearance(x, y) < 1.8:
            continue
        ico(
            "WOODLAND_UNDERBRUSH_%03d" % i,
            (x, y, 0.25),
            (
                random.uniform(0.8, 1.8),
                random.uniform(0.7, 1.5),
                random.uniform(0.45, 1.0)
            ),
            MATS["leaf"] if i % 3 else MATS["leaf_light"],
            forest,
            sub=1
        )

    fallen_logs = [
        ((-158, -28, 0.25), (-149, -24, 0.25)),
        ((-132, 18, 0.25), (-124, 14, 0.25)),
        ((-108, -25, 0.2), (-100, -20, 0.2)),
        ((-87, 23, 0.25), (-79, 19, 0.25)),
        ((-68, -22, 0.2), (-60, -17, 0.2))
    ]
    for i, (a, b) in enumerate(fallen_logs):
        beam_between(
            "WOODLAND_FALLEN_TRUNK_%02d" % i,
            a, b,
            random.uniform(0.24, 0.38),
            MATS["trunk"],
            forest
        )

    # Rock clusters interrupt the woodland floor and create real reasons to turn.
    rock_groups = [
        (-157, -5, 3), (-139, -22, 3), (-124, 1, 4),
        (-105, 17, 3), (-89, 2, 4), (-70, -12, 3)
    ]
    for group_index, (cx, cy, count) in enumerate(rock_groups):
        for j in range(count):
            x = cx + random.uniform(-2.2, 2.2)
            y = cy + random.uniform(-1.8, 1.8)
            ico(
                "WOODLAND_BOULDER_%02d_%02d" % (group_index, j),
                (x, y, random.uniform(0.2, 0.65)),
                (
                    random.uniform(1.4, 3.2),
                    random.uniform(1.2, 2.6),
                    random.uniform(0.9, 2.0)
                ),
                MATS["rock"] if j % 2 else MATS["rock_light"],
                forest,
                sub=1,
                rot=(random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), random.uniform(-0.5, 0.5))
            )


def build_tactical_layout():
    tactical = get_collection("BFP_V20_14_TACTICAL_MARKERS")
    forest = get_collection("BFP_V20_02_FOREST")
    ravine = get_collection("BFP_V20_03_RAVINE")

    # Neutral cover forms: these reserve places where later characters can crouch,
    # observe, fire from cover or move toward the next advance lane.
    cover_specs = [
        ("FOREST_COVER_A", (-160, -24), (-164, -27), (-145, -15), forest),
        ("FOREST_COVER_B", (-137, 18), (-141, 21), (-124, -5), forest),
        ("FOREST_COVER_C", (-105, 18), (-109, 21), (-93, 12), forest),
        ("FOREST_COVER_D", (-80, -19), (-84, -22), (-70, -1), forest),
        ("RAVINE_COVER_E", (-39, -12), (-42, -15), (-25, -1), ravine),
        ("RAVINE_COVER_F", (-9, 13), (-12, 16), (4, 0), ravine)
    ]

    for index, (name, cover_xy, soldier_xy, target_xy, owner) in enumerate(cover_specs):
        cx, cy = cover_xy
        ico(
            name + "_ROCK_MASS",
            (cx, cy, 0.7),
            (3.0, 2.2, 1.45),
            MATS["rock"],
            owner,
            sub=1
        )
        ico(
            name + "_LOW_EARTH_SHOULDER",
            (cx - 1.4, cy + 0.7, 0.15),
            (3.8, 2.7, 0.55),
            MATS["slope"],
            owner,
            sub=1
        )

        soldier = empty(
            "FUTURE_SOLDIER_COVER_SLOT_%02d" % index,
            (soldier_xy[0], soldier_xy[1], 0.25),
            tactical,
            display='ARROWS',
            size=1.4
        )
        soldier.rotation_euler.z = 0.0

        start = empty(
            "FUTURE_ADVANCE_LANE_%02d_START" % index,
            (soldier_xy[0], soldier_xy[1], 0.1),
            tactical,
            display='CIRCLE',
            size=0.9
        )
        end = empty(
            "FUTURE_ADVANCE_LANE_%02d_END" % index,
            (target_xy[0], target_xy[1], 0.1),
            tactical,
            display='CIRCLE',
            size=0.9
        )
        dx = target_xy[0] - soldier_xy[0]
        dy = target_xy[1] - soldier_xy[1]
        direction = empty(
            "FUTURE_FIRE_OR_ADVANCE_DIRECTION_%02d" % index,
            (soldier_xy[0], soldier_xy[1], 0.3),
            tactical,
            display='ARROWS',
            size=2.0
        )
        direction.rotation_euler.z = math.atan2(dy, dx)

    # A few additional neutral movement anchors describe staggered advance,
    # without assigning a faction or deciding the final actor count.
    for i, (x, y) in enumerate(((-153, -8), (-128, -12), (-106, 4), (-84, 12), (-54, 2))):
        marker = empty(
            "FUTURE_STAGGERED_ADVANCE_POINT_%02d" % i,
            (x, y, 0.1),
            tactical,
            display='ARROWS',
            size=1.1
        )
        marker.rotation_euler.z = 0.0


# ============================================================
# RAVINE: CLOSE ROCK WALLS AND LOW FLIGHT
# ============================================================

def build_ravine():
    ravine = get_collection("BFP_V20_03_RAVINE")

    for side in (-1, 1):
        for i, x in enumerate((-52, -38, -24, -10, 4)):
            y = side * random.uniform(13.5, 17.0)
            ico(
                "LIXINGOU_CLOSE_RAVINE_WALL_%s_%02d" % (side, i),
                (x, y, random.uniform(5.5, 8.0)),
                (random.uniform(9, 13), random.uniform(5, 8), random.uniform(9, 14)),
                MATS["rock"] if i % 2 else MATS["rock_light"],
                ravine,
                sub=1
            )

    # Scattered boulders define a winding passage through the ravine floor.
    boulders = [
        (-49, -7, 1.0), (-38, 8, 1.2), (-27, -6, 1.0),
        (-17, 7, 1.1), (-7, -8, 1.0), (2, 5, 1.1)
    ]
    for i, (x, y, z) in enumerate(boulders):
        ico(
            "RAVINE_FLOOR_BOULDER_%02d" % i,
            (x, y, z),
            (random.uniform(1.5, 2.8), random.uniform(1.2, 2.1), random.uniform(1.0, 1.8)),
            MATS["rock"],
            ravine,
            sub=1
        )


# ============================================================
# WUTONGGOU RUINS + EXPLOSION FUTURE MARKER
# ============================================================

def build_village():
    village = get_collection("BFP_V20_04_VILLAGE")

    # Surrounding damaged houses; the central house is rebuilt as a breached shell
    # so the camera can pass through its open corridor rather than clipping a solid box.
    houses = [
        (17, -17), (25, 16), (49, 15),
        (58, -16), (7, 13), (42, 27)
    ]

    for i, (x, y) in enumerate(houses):
        w = random.uniform(5.0, 7.5)
        d = random.uniform(4.0, 6.0)
        h = random.uniform(2.5, 4.0)

        cube(
            "WUTONGGOU_BROKEN_HOUSE_%02d" % i,
            (x, y, h * 0.5 - 0.8),
            (w, d, h),
            MATS["ruin"],
            village,
            rot=(0, 0, random.uniform(-0.2, 0.2))
        )
        cube(
            "WUTONGGOU_COLLAPSED_ROOF_%02d" % i,
            (x + random.uniform(-0.6, 0.6), y, h + 0.2),
            (w + 0.8, d + 0.6, 0.25),
            MATS["roof"],
            village,
            rot=(random.uniform(-0.2, 0.2), random.uniform(-0.5, 0.5), random.uniform(-0.2, 0.2))
        )
        for j in range(3):
            cube(
                "WUTONGGOU_RUBBLE_%02d_%02d" % (i, j),
                (x + random.uniform(-4, 4), y + random.uniform(-3, 3), -0.5),
                (random.uniform(0.8, 2.0), random.uniform(0.5, 1.5), random.uniform(0.4, 1.0)),
                MATS["rock"],
                village,
                rot=(random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), random.uniform(-0.5, 0.5))
            )

    # Breached house corridor: camera travels along +X through an open central lane.
    # Two broken side walls and partial roof fragments create a readable "inside" pass.
    cube(
        "WUTONGGOU_BREACHED_HOUSE_LEFT_WALL",
        (37, -13.2, 1.5),
        (17, 1.3, 3.2),
        MATS["ruin"],
        village,
        rot=(0.02, 0.0, -0.03)
    )
    cube(
        "WUTONGGOU_BREACHED_HOUSE_RIGHT_WALL",
        (37, -0.8, 1.45),
        (17, 1.3, 3.0),
        MATS["ruin"],
        village,
        rot=(-0.03, 0.0, 0.02)
    )
    cube(
        "WUTONGGOU_BREACHED_ROOF_FRAGMENT_A",
        (33, -7, 4.4),
        (5.5, 11.5, 0.55),
        MATS["roof"],
        village,
        rot=(0.02, 0.05, 0.02)
    )
    cube(
        "WUTONGGOU_BREACHED_ROOF_FRAGMENT_B",
        (43.5, -7, 4.8),
        (3.5, 8.5, 0.45),
        MATS["roof"],
        village,
        rot=(-0.04, 0.08, -0.03)
    )

    # Rubble stays at the corridor margins, leaving the camera lane open.
    for i in range(12):
        x = random.uniform(29, 46)
        side = random.choice((-1, 1))
        y = -7 + side * random.uniform(5.0, 7.2)
        ico(
            "WUTONGGOU_BREACH_RUBBLE_%02d" % i,
            (x, y, -0.1),
            (random.uniform(0.8, 1.8), random.uniform(0.5, 1.2), random.uniform(0.4, 0.9)),
            MATS["rock"],
            village,
            sub=1
        )

    markers = get_collection("BFP_V20_08_FUTURE_MARKERS")
    empty(
        "FUTURE_HOUSE_EXPLOSION_WUTONGGOU",
        (38, -7, 3.2),
        markers,
        display='CIRCLE',
        size=4.0
    )
    approach = empty(
        "FUTURE_JAPANESE_APPROACH_TO_HOUSE",
        (59, 7, 0),
        markers,
        display='ARROWS',
        size=3.0
    )
    approach.rotation_euler.z = math.pi

    advance_01 = empty(
        "FUTURE_JAPANESE_ADVANCE_POINT_01",
        (53, 4, 0),
        markers,
        display='ARROWS',
        size=2.0
    )
    advance_01.rotation_euler.z = math.pi

    advance_02 = empty(
        "FUTURE_JAPANESE_ADVANCE_POINT_02",
        (46, 0, 0),
        markers,
        display='ARROWS',
        size=2.0
    )
    advance_02.rotation_euler.z = math.pi
    empty(
        "FUTURE_CAMERA_SMOKE_ENTRY",
        (30, -7, 2.4),
        markers,
        display='SPHERE',
        size=1.5
    )
    empty(
        "FUTURE_CAMERA_SMOKE_EXIT",
        (51, -4, 2.5),
        markers,
        display='SPHERE',
        size=1.5
    )
    empty(
        "FUTURE_CAMERA_WATER_ENTRY",
        (75, 1, 0),
        markers,
        display='CIRCLE',
        size=2.0
    )


def build_house_blast_smoke():
    smoke_coll = get_collection("BFP_V20_12_SMOKE_PLACEHOLDERS")

    # Static low-poly smoke masses only: visual volume placeholders, not a simulation.
    smoke_specs = [
        ((31, -7, 4.8), (5.5, 6.5, 4.0), "smoke"),
        ((36, -7, 5.5), (7.0, 7.5, 5.2), "smoke"),
        ((42, -6, 5.8), (7.5, 7.0, 5.8), "smoke"),
        ((47, -4, 4.8), (5.5, 6.0, 4.2), "smoke"),
        ((35, -3, 3.2), (6.0, 5.0, 2.5), "dust"),
        ((42, -10, 3.0), (6.0, 4.5, 2.2), "dust"),
        ((49, -2, 3.2), (4.5, 4.0, 2.2), "dust"),
    ]
    for i, (loc, scale, material_key) in enumerate(smoke_specs):
        ico(
            "WUTONGGOU_BLAST_SMOKE_MASS_%02d" % i,
            loc,
            scale,
            MATS[material_key],
            smoke_coll,
            sub=2
        )

    # A low drifting dust bank stretches across the camera's exit from the house.
    ico(
        "WUTONGGOU_BLAST_DUST_EXIT_BANK",
        (49, -4, 1.8),
        (8.0, 7.0, 1.7),
        MATS["dust"],
        smoke_coll,
        sub=2
    )


# ============================================================
# CURVED RIVER / RIVERBANK
# ============================================================

def build_river():
    river = get_collection("BFP_V20_05_RIVER")
    centerline = [
        (72, -4), (88, 0), (104, 8), (122, 12),
        (140, 6), (158, -8), (176, -2), (196, 8)
    ]
    # Broad shallow crossing: 72m water width, with a wider submerged riverbed.
    ribbon("HUANGCAOGUAN_BROAD_RIVER_SURFACE", centerline, 36.0, 0.38, MATS["water"], river)
    ribbon("HUANGCAOGUAN_BROAD_RIVERBED", centerline, 40.0, -4.15, MATS["riverbed"], river)

    # Irregular gravel bars break the water surface and create shallow crossing lanes.
    for i, (x, y, sx, sy) in enumerate([
        (96, -18, 8.0, 3.2), (116, 23, 9.5, 3.4),
        (139, -24, 7.5, 3.0), (160, 18, 10.0, 3.6),
        (181, -18, 8.0, 3.0)
    ]):
        ico("RIVER_GRAVEL_BAR_%02d" % i, (x, y, 0.08), (sx, sy, 0.38),
            MATS["road_edge"], river, sub=1)

    # Broken rock banks follow the meandering river, with uneven spacing and scale.
    for i, (x, y) in enumerate(centerline):
        for side in (-1, 1):
            yy = y + side * random.uniform(37.0, 45.0)
            ico("RIVERBANK_BOULDER_%02d_%s" % (i, side),
                (x + random.uniform(-3.0, 3.0), yy, random.uniform(0.0, 1.0)),
                (random.uniform(2.5, 5.2), random.uniform(1.7, 3.4), random.uniform(0.8, 2.0)),
                MATS["rock"], river, sub=1)

    for i, (x, y, sx, sy) in enumerate([
        (96, 3, 5.5, 3.2), (119, -2, 6.2, 3.5),
        (145, 3, 5.8, 3.0), (168, -1, 5.0, 3.2)
    ]):
        ico("RIVER_BLOOD_TINT_PATCH_%02d" % i, (x, y, 0.405),
            (sx, sy, 0.045), MATS["blood_water"], river, sub=1)

    submerged = [
        (87, 1, -2.7), (101, 16, -2.7), (126, -22, -2.7),
        (151, 17, -2.6), (173, -16, -2.5), (188, 24, -2.7)
    ]
    for i, (x, y, z) in enumerate(submerged):
        ico("UNDERWATER_ROCK_OBSTACLE_%02d" % i, (x, y, z),
            (2.5, 2.0, 1.2), MATS["rock"], river, sub=1)

    # Fallen branches and timber at the river edge give the camera a reason to dodge.
    beam_between("RIVERBANK_FALLEN_LOG_A", (112, -39, 0.4), (122, -33, 0.4), 0.32, MATS["trunk"], river)
    beam_between("RIVERBANK_FALLEN_LOG_B", (165, 37, 0.25), (178, 32, 0.25), 0.28, MATS["trunk"], river)



def build_wide_road_and_crowd_markers():
    road_coll = get_collection("BFP_V20_07_WIDE_ROAD")
    markers = get_collection("BFP_V20_08_FUTURE_MARKERS")

    # Wide, open dirt road begins immediately after the river exit.
    # Camera and future charging groups travel along +X.
    road_centerline = [
        (190, 6), (208, 4), (230, 2), (252, 0),
        (278, -1), (305, 0), (335, 1), (355, 2)
    ]
    ribbon(
        "WIDE_OPEN_CHARGE_ROAD",
        road_centerline,
        29.0,
        -0.36,
        MATS["road"],
        road_coll
    )

    # Low edge markers define the width without cluttering the central lane.
    for i, x in enumerate((210, 238, 266, 294, 322, 345)):
        for side in (-1, 1):
            ico(
                "WIDE_ROAD_EDGE_ROCK_%02d_%s" % (i, side),
                (x, side * 30.5, -0.15),
                (random.uniform(1.2, 2.2), random.uniform(0.8, 1.4), random.uniform(0.5, 0.9)),
                MATS["road_edge"],
                road_coll,
                sub=1
            )

    # Future actor anchors only. Empty objects do not render as characters.
    # These reserve lanes for groups continuously advancing toward +X.
    for lane_index, y in enumerate((-17, -9, 9, 17)):
        for j, x in enumerate((210, 226, 242, 258, 274, 290, 306)):
            marker = empty(
                "FUTURE_CHARGING_GROUP_LANE_%02d_POINT_%02d" % (lane_index, j),
                (x, y, 0.0),
                markers,
                display='ARROWS',
                size=1.25
            )
            marker.rotation_euler.z = 0.0

    empty(
        "FUTURE_OLD_MENG_POSITION",
        (250, 0, 0),
        markers,
        display='CIRCLE',
        size=3.0
    )
    empty(
        "FUTURE_CHARGE_DIRECTION_POSITIVE_X",
        (270, 0, 0),
        markers,
        display='ARROWS',
        size=3.0
    )
    empty(
        "FUTURE_BOX_HANDOFF_RIVERBANK",
        (202, -4, 0),
        markers,
        display='CUBE',
        size=2.0
    )


# ============================================================
# WEST PASS: HUGE VALLEY AND NATURAL FRAME
# ============================================================

def build_ground_grass():
    grass_coll = get_collection("BFP_V20_13_GROUND_GRASS")

    # Build many thin, slightly curved blades into a small number of meshes.
    # Tufts stay mostly along the road edges so the low camera lane remains clear.
    verts = []
    faces = []
    face_materials = []

    def add_blade(base, height, width, lean_x, lean_y, material_index):
        base = Vector(base)
        mid = base + Vector((lean_x * 0.55, lean_y * 0.55, height * 0.62))
        tip = base + Vector((lean_x, lean_y, height))
        direction = Vector((lean_x, lean_y, 0))
        if direction.length < 0.001:
            direction = Vector((1, 0, 0))
        direction.normalize()
        side = Vector((-direction.y, direction.x, 0)) * width

        start = len(verts)
        verts.extend([
            tuple(base - side),
            tuple(base + side),
            tuple(mid - side * 0.55),
            tuple(mid + side * 0.55),
            tuple(tip),
        ])
        faces.extend([
            (start + 0, start + 1, start + 3, start + 2),
            (start + 2, start + 3, start + 4),
        ])
        face_materials.extend([material_index, material_index])

    random.seed(SEED + 55)

    # Main road margins: fine, silky sedge-like blades lean in the same general wind direction.
    for i in range(210):
        x = random.uniform(205, 302)
        side = random.choice((-1, 1))
        y = side * random.uniform(7.5, 28.0)
        base_z = -0.43
        blade_count = random.randint(3, 5)
        for j in range(blade_count):
            angle = random.uniform(-0.75, 0.75)
            lean_x = random.uniform(0.20, 0.55)
            lean_y = side * random.uniform(0.03, 0.22) + math.sin(angle) * 0.12
            height = random.uniform(0.38, 0.92)
            width = random.uniform(0.025, 0.055)
            add_blade(
                (x + random.uniform(-0.45, 0.45), y + random.uniform(-0.35, 0.35), base_z),
                height, width, lean_x, lean_y,
                0 if random.random() < 0.72 else 1
            )

    # A few taller, nearer foreground tufts provide parallax in the ground-level wide-angle push,
    # but are offset from the exact centerline to avoid blocking the subject.
    for i in range(54):
        x = random.uniform(224, 280)
        side = random.choice((-1, 1))
        y = side * random.uniform(3.0, 8.5)
        for j in range(random.randint(3, 4)):
            add_blade(
                (x + random.uniform(-0.25, 0.25), y + random.uniform(-0.25, 0.25), -0.43),
                random.uniform(0.32, 0.72),
                random.uniform(0.025, 0.055),
                random.uniform(0.25, 0.5),
                side * random.uniform(0.05, 0.18),
                0 if random.random() < 0.7 else 1
            )

    mesh = bpy.data.meshes.new("BFP_V20_GROUND_GRASS_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(MATS["grass"])
    mesh.materials.append(MATS["grass_light"])
    mesh.update()

    obj = bpy.data.objects.new("BFP_V20_LOW_FINE_DRY_GRASS", mesh)
    grass_coll.objects.link(obj)

    for poly, mat_index in zip(mesh.polygons, face_materials):
        poly.material_index = mat_index


# ============================================================
# WEST PASS: HUGE VALLEY AND NATURAL FRAME
# ============================================================

def build_ground_rocks():
    rocks = get_collection("BFP_V20_15_GROUND_ROCKS")

    # Small, low-profile stones sit close to the camera's ground-level path.
    # They are kept outside the exact camera centerline, so they read as foreground
    # parallax and ground texture rather than hard obstacles.
    rock_specs = [
        (226, -3.7, (1.25, 0.85, 0.32)),
        (233, 4.0, (1.55, 0.95, 0.38)),
        (241, -4.4, (1.45, 0.9, 0.34)),
        (249, 3.6, (1.2, 0.8, 0.28)),
        (258, -4.0, (1.65, 1.0, 0.4)),
        (267, 4.5, (1.35, 0.9, 0.32)),
        (276, -3.8, (1.4, 0.85, 0.3)),
        (286, 4.2, (1.5, 0.95, 0.36)),
    ]
    for i, (x, y, scale) in enumerate(rock_specs):
        ico(
            "LOW_CAMERA_FOREGROUND_STONE_%02d" % i,
            (x, y, -0.16),
            scale,
            MATS["rock"] if i % 2 else MATS["rock_light"],
            rocks,
            sub=1,
            rot=(random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), random.uniform(-0.5, 0.5))
        )

    # A few very flat gravel clusters add ground texture without blocking the lens.
    for i in range(60):
        x = random.uniform(215, 300)
        y = random.choice((-1, 1)) * random.uniform(2.5, 6.0)
        ico(
            "LOW_CAMERA_GRAVEL_%02d" % i,
            (x, y, -0.28),
            (random.uniform(0.25, 0.75), random.uniform(0.2, 0.55), random.uniform(0.08, 0.18)),
            MATS["rock"],
            rocks,
            sub=1
        )


# ============================================================
# WEST PASS: HUGE VALLEY AND NATURAL FRAME
# ============================================================

def build_west_pass():
    pass_coll = get_collection("BFP_V20_06_WEST_PASS")
    markers = get_collection("BFP_V20_08_FUTURE_MARKERS")

    # Huge valley walls: wide opening, very tall sides, clear central road.
    for side in (-1, 1):
        for i, x in enumerate((298, 316, 334, 352)):
            y = side * random.uniform(43, 52)
            ico(
                "WEST_VALLEY_MASSIVE_SIDE_WALL_%s_%02d" % (side, i),
                (x, y, random.uniform(24, 34)),
                (random.uniform(22, 29), random.uniform(17, 23), random.uniform(30, 43)),
                MATS["rock"] if i % 2 else MATS["rock_light"],
                pass_coll,
                sub=2
            )

    # High rock crown creates a natural frame above the valley opening.
    # It remains far above the low camera path and does not form a cramped tunnel.
    ico(
        "WEST_VALLEY_HIGH_FRAME_CROWN",
        (322, 0, 66),
        (30, 58, 13),
        MATS["rock"],
        pass_coll,
        sub=2
    )

    # Distant ridges behind the pass give the opening depth.
    ico(
        "WEST_VALLEY_BACK_LEFT_RIDGE",
        (360, -70, 38),
        (38, 28, 43),
        MATS["mountain"],
        pass_coll,
        sub=2
    )
    ico(
        "WEST_VALLEY_BACK_RIGHT_RIDGE",
        (365, 70, 40),
        (40, 30, 45),
        MATS["mountain"],
        pass_coll,
        sub=2
    )

    empty(
        "FUTURE_VALLEY_FRAME_CENTER",
        (322, 0, 2),
        markers,
        display='CIRCLE',
        size=5.0
    )



# ============================================================
# WHITE-BLOCK ACTORS / PROPS / BATTLEFIELD INTERACTIONS
# ============================================================

def child_cube(name, parent, local_loc, dims, material, coll, rot=(0, 0, 0)):
    obj = cube(name, local_loc, dims, material, coll, rot=rot)
    obj.parent = parent
    obj.location = local_loc
    obj.rotation_euler = rot
    return obj


def child_ico(name, parent, local_loc, scale, material, coll, sub=1):
    obj = ico(name, local_loc, scale, material, coll, sub=sub)
    obj.parent = parent
    obj.location = local_loc
    return obj


def child_cylinder(name, parent, local_loc, radius, depth, material, coll, rot=(0, 0, 0)):
    obj = cylinder(name, local_loc, radius, depth, material, coll, vertices=7, rot=rot)
    obj.parent = parent
    obj.location = local_loc
    obj.rotation_euler = rot
    return obj


def animate_actor(actor, path, run=True):
    """
    path entries: (frame, (x, y, z), yaw_radians)
    Camera choreography is keyed against these actor paths and event positions.
    """
    root = actor["root"]
    for frame, loc, yaw in path:
        root.location = loc
        root.rotation_euler.z = yaw
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)

    if run:
        start = path[0][0]
        end = path[-1][0]
        for frame in range(start, end + 1, 4):
            phase = (frame - start) * (2.0 * math.pi / 18.0)
            swing = math.sin(phase) * 0.58
            actor["left_leg"].rotation_euler.y = swing
            actor["right_leg"].rotation_euler.y = -swing
            arm_factor = 0.22 if actor.get("rifle") else 0.78
            actor["left_arm"].rotation_euler.y = -swing * arm_factor
            actor["right_arm"].rotation_euler.y = swing * arm_factor
            for key in ("left_leg", "right_leg", "left_arm", "right_arm"):
                actor[key].keyframe_insert(data_path="rotation_euler", frame=frame)

    for obj in [root, actor["left_leg"], actor["right_leg"], actor["left_arm"], actor["right_arm"]]:
        if obj.animation_data and obj.animation_data.action:
            try:
                for fc in obj.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = 'AUTO_CLAMPED'
                        kp.handle_right_type = 'AUTO_CLAMPED'
            except Exception:
                pass


def make_actor(name, loc, yaw=0.0, faction="cn", posture="stand",
               rifle=False, grenades=0, material_override=None):
    """
    Segmented-color white-block actor:
    sphere head + cuboid torso/arms/legs. No face, cloth texture or rig.
    Local forward direction is +X.
    """
    coll = get_collection("BFP_V20_16_CHARACTERS")
    root = empty(name + "_ROOT", loc, coll, display='PLAIN_AXES', size=0.55)
    root.rotation_euler.z = yaw

    if material_override:
        body_mat = MATS[material_override]
    elif faction == "jp":
        body_mat = MATS["jp_soldier"]
    elif faction == "old_meng":
        body_mat = MATS["old_meng"]
    else:
        body_mat = MATS["cn_soldier"]

    if posture == "crouch":
        torso_z, head_z, shoulder_z, hip_z = 0.83, 1.30, 1.08, 0.45
        torso_dims = (0.50, 0.36, 0.62)
    else:
        torso_z, head_z, shoulder_z, hip_z = 1.03, 1.62, 1.34, 0.68
        torso_dims = (0.52, 0.36, 0.76)

    torso = child_cube(name + "_TORSO", root, (0, 0, torso_z), torso_dims, body_mat, coll)
    head = child_ico(name + "_HEAD", root, (0, 0, head_z), (0.23, 0.22, 0.25), body_mat, coll, sub=1)

    left_arm = empty(name + "_LEFT_ARM_PIVOT", (0, -0.25, shoulder_z), coll, display='PLAIN_AXES', size=0.15)
    right_arm = empty(name + "_RIGHT_ARM_PIVOT", (0, 0.25, shoulder_z), coll, display='PLAIN_AXES', size=0.15)
    left_arm.parent = root
    right_arm.parent = root
    left_arm.location = (0, -0.25, shoulder_z)
    right_arm.location = (0, 0.25, shoulder_z)

    child_cube(name + "_LEFT_ARM", left_arm, (0.03, 0, -0.31), (0.25, 0.23, 0.64), body_mat, coll)
    child_cube(name + "_RIGHT_ARM", right_arm, (0.03, 0, -0.31), (0.25, 0.23, 0.64), body_mat, coll)

    left_leg = empty(name + "_LEFT_LEG_PIVOT", (0, -0.14, hip_z), coll, display='PLAIN_AXES', size=0.13)
    right_leg = empty(name + "_RIGHT_LEG_PIVOT", (0, 0.14, hip_z), coll, display='PLAIN_AXES', size=0.13)
    left_leg.parent = root
    right_leg.parent = root
    left_leg.location = (0, -0.14, hip_z)
    right_leg.location = (0, 0.14, hip_z)

    child_cube(name + "_LEFT_LEG", left_leg, (0, 0, -0.33), (0.28, 0.27, 0.68), body_mat, coll)
    child_cube(name + "_RIGHT_LEG", right_leg, (0, 0, -0.33), (0.28, 0.27, 0.68), body_mat, coll)

    actor = {
        "root": root,
        "torso": torso,
        "head": head,
        "left_arm": left_arm,
        "right_arm": right_arm,
        "left_leg": left_leg,
        "right_leg": right_leg,
    }

    if rifle:
        # Rifle is a small, readable cuboid prop held across the front of the torso.
        gun = child_cube(name + "_RIFLE", root, (0.62, -0.22, torso_z + 0.05),
                         (1.12, 0.10, 0.10), MATS["weapon"], coll)
        child_cube(name + "_RIFLE_STOCK", root, (0.08, -0.22, torso_z + 0.05),
                   (0.34, 0.15, 0.14), MATS["weapon"], coll)
        actor["rifle"] = gun

    if grenades:
        for i in range(grenades):
            angle = (2.0 * math.pi * i) / float(grenades)
            gx = math.cos(angle) * 0.28
            gy = math.sin(angle) * 0.23
            child_cylinder(
                name + "_CHARGE_%02d" % i,
                root,
                (gx, gy, torso_z + 0.02),
                0.085, 0.25,
                MATS["grenade"], coll,
                rot=(0.12, 0.0, angle)
            )

    return actor


def make_casualty(name, loc, yaw=0.0, faction="cn", pose="prone", submerged=False, charred=False):
    """Non-graphic white-block casualty; varied orientation and limb placement."""
    coll = get_collection("BFP_V20_16_CHARACTERS")
    root = empty(name + "_ROOT", loc, coll, display='PLAIN_AXES', size=0.35)
    root.rotation_euler.z = yaw

    if charred:
        body_mat = MATS["casualty_charred"]
    else:
        body_mat = MATS["casualty_jp"] if faction == "jp" else MATS["casualty_cn"]
    if pose == "side":
        body_rot = (0.85, 0.0, 0.0)
        head_loc = (-0.62, 0.10, 0.35)
        arm_a_loc, arm_b_loc = (-0.05, -0.34, 0.30), (0.16, 0.34, 0.24)
        leg_a_rot, leg_b_rot = (0.0, 0.0, -0.28), (0.0, 0.0, 0.32)
    elif pose == "supine":
        body_rot = (math.pi, 0.0, 0.0)
        head_loc = (-0.68, 0.0, 0.36)
        arm_a_loc, arm_b_loc = (-0.05, -0.48, 0.28), (0.16, 0.48, 0.28)
        leg_a_rot, leg_b_rot = (0.0, 0.0, -0.18), (0.0, 0.0, 0.24)
    else:
        body_rot = (0.0, 0.0, 0.0)
        head_loc = (-0.70, -0.04, 0.30)
        arm_a_loc, arm_b_loc = (-0.05, -0.38, 0.27), (0.16, 0.37, 0.26)
        leg_a_rot, leg_b_rot = (0.0, 0.0, random.uniform(-0.25, 0.25)), (0.0, 0.0, random.uniform(-0.25, 0.25))

    child_cube(name + "_BODY", root, (0.0, 0.0, 0.28),
               (1.15, 0.36, 0.28), body_mat, coll, rot=body_rot)
    child_ico(name + "_HEAD", root, head_loc, (0.22, 0.20, 0.21), body_mat, coll, sub=1)

    # Arms and legs deliberately differ in angle to avoid repeated mannequin poses.
    child_cube(name + "_ARM_A", root, arm_a_loc,
               (0.62, 0.18, 0.17), body_mat, coll,
               rot=(0.0, 0.0, random.uniform(-0.55, 0.55)))
    child_cube(name + "_ARM_B", root, arm_b_loc,
               (0.56, 0.18, 0.17), body_mat, coll,
               rot=(0.0, 0.0, random.uniform(-0.55, 0.55)))
    child_cube(name + "_LEG_A", root, (0.72, -0.13, 0.22),
               (0.72, 0.22, 0.20), body_mat, coll, rot=leg_a_rot)
    child_cube(name + "_LEG_B", root, (0.76, 0.14, 0.22),
               (0.68, 0.22, 0.20), body_mat, coll, rot=leg_b_rot)

    if submerged:
        root.location.z = loc[2]
    return root


def make_pigeon():
    """Simple readable pigeon silhouette, with a left-foreground glide and wing beats."""
    props = get_collection("BFP_V20_17_PROPS")
    root = empty("OPENING_PIGEON_ROOT", (-232, -16, 116), props, display='PLAIN_AXES', size=0.55)
    child_ico("OPENING_PIGEON_BODY", root, (0, 0, 0), (0.88, 0.25, 0.25), MATS["bird"], props, sub=2)
    child_ico("OPENING_PIGEON_HEAD", root, (0.72, 0, 0.12), (0.28, 0.22, 0.22), MATS["bird"], props, sub=2)
    child_cube("OPENING_PIGEON_BEAK", root, (1.02, 0, 0.11), (0.22, 0.10, 0.10), MATS["roof"], props)
    child_ico("OPENING_PIGEON_TAIL", root, (-0.82, 0, 0.02), (0.40, 0.22, 0.08), MATS["bird"], props, sub=1)

    left_wing = empty("OPENING_PIGEON_LEFT_WING_PIVOT", (0, -0.16, 0.10), props, display='PLAIN_AXES', size=0.12)
    left_wing.parent = root
    left_wing.location = (0, -0.16, 0.10)
    child_cube("OPENING_PIGEON_LEFT_WING", left_wing, (0.05, -0.74, 0.0), (0.95, 1.55, 0.10), MATS["bird"], props, rot=(0.0, 0.0, -0.08))

    right_wing = empty("OPENING_PIGEON_RIGHT_WING_PIVOT", (0, 0.16, 0.10), props, display='PLAIN_AXES', size=0.12)
    right_wing.parent = root
    right_wing.location = (0, 0.16, 0.10)
    child_cube("OPENING_PIGEON_RIGHT_WING", right_wing, (0.05, 0.74, 0.0), (0.95, 1.55, 0.10), MATS["bird"], props, rot=(0.0, 0.0, 0.08))

    bird_path = [
        (1, (-232, -16, 116), 0.02),
        (18, (-224, -16, 115), 0.00),
        (32, (-214, -19, 112), -0.05),
        (46, (-202, -27, 108), -0.16),
        (58, (-190, -38, 103), -0.28),
        (70, (-177, -52, 98), -0.36),
    ]
    for frame, loc, yaw in bird_path:
        root.location = loc
        root.rotation_euler = (0.0, 0.0, yaw)
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)

    for frame, flap in [
        (1, 0.05), (7, -0.35), (13, 0.18), (19, 0.42), (25, -0.08),
        (31, -0.42), (37, 0.08), (43, 0.36), (49, -0.12), (55, -0.30),
        (61, 0.12), (67, 0.25), (73, 0.0)
    ]:
        left_wing.rotation_euler.x = flap
        right_wing.rotation_euler.x = -flap
        left_wing.keyframe_insert(data_path="rotation_euler", frame=frame)
        right_wing.keyframe_insert(data_path="rotation_euler", frame=frame)
    return root


def make_aircraft_bomb(name, release_frame, release_loc, impact_frame, impact_loc, start_loc=None):
    """A non-powered aviation bomb: attached-position proxy, release, freefall and impact."""
    props = get_collection("BFP_V20_17_PROPS")
    root = empty(name + "_ROOT", release_loc, props, display='PLAIN_AXES', size=0.35)
    child_cylinder(name + "_BODY", root, (0, 0, 0), 0.20, 1.85, MATS["weapon"], props)
    child_ico(name + "_NOSE", root, (0, 0, -1.02), (0.19, 0.19, 0.30), MATS["weapon"], props, sub=1)
    for idx, rot in enumerate(((0, 0, 0), (0, 0, math.pi / 2), (math.pi / 2, 0, 0), (0, math.pi / 2, 0))):
        child_cube(name + "_TAIL_FIN_%02d" % idx, root, (0, 0, 0.72), (0.58, 0.07, 0.34), MATS["aircraft"], props, rot=rot)

    mid1 = (
        release_loc[0] + (impact_loc[0] - release_loc[0]) * 0.30,
        release_loc[1] + (impact_loc[1] - release_loc[1]) * 0.30,
        release_loc[2] - (release_loc[2] - impact_loc[2]) * 0.28,
    )
    mid2 = (
        release_loc[0] + (impact_loc[0] - release_loc[0]) * 0.72,
        release_loc[1] + (impact_loc[1] - release_loc[1]) * 0.72,
        release_loc[2] - (release_loc[2] - impact_loc[2]) * 0.76,
    )
    if start_loc is None:
        start_loc = release_loc
    for frame, loc, pitch in [
        (1, start_loc, 0.12),
        (max(1, release_frame - 2), release_loc, 0.12),
        (release_frame, release_loc, 0.12),
        (release_frame + 8, mid1, 0.20),
        (release_frame + (impact_frame - release_frame) * 0.70, mid2, 0.28),
        (impact_frame, impact_loc, 0.34),
    ]:
        root.location = loc
        root.rotation_euler = (0.0, pitch, 0.0)
        root.keyframe_insert(data_path="location", frame=int(frame))
        root.keyframe_insert(data_path="rotation_euler", frame=int(frame))
    return root


def make_aircraft():
    props = get_collection("BFP_V20_17_PROPS")
    body = MATS["aircraft"]

    def build_bomber(name, path, scale=1.0):
        root = empty(name + "_ROOT", path[0][1], props, display='PLAIN_AXES', size=2.0)
        root.scale = (scale, scale, scale)
        child_cube(name + "_FUSELAGE", root, (0, 0, 0), (7.4, 0.82, 0.82), body, props)
        child_cube(name + "_MAIN_WING", root, (-0.15, 0, -0.02), (1.85, 14.0, 0.24), body, props)
        child_cube(name + "_TAIL_WING", root, (-2.85, 0, 0.02), (1.35, 4.8, 0.20), body, props)
        child_cube(name + "_TAIL_FIN", root, (-2.95, 0, 0.55), (1.2, 0.22, 1.10), body, props)
        child_cube(name + "_COCKPIT", root, (1.45, 0, 0.50), (1.25, 0.50, 0.32), MATS["rock_light"], props)
        for side in (-1, 1):
            child_cube(name + "_ENGINE_%s" % side, root, (0.05, side * 3.0, -0.30), (1.45, 0.82, 0.70), body, props)
            child_cylinder(name + "_PROPELLER_HUB_%s" % side, root, (1.0, side * 3.0, -0.30), 0.12, 0.35, MATS["weapon"], props, rot=(0.0, math.pi / 2.0, 0.0))
            child_cube(name + "_PROP_BLADE_A_%s" % side, root, (1.22, side * 3.0, -0.30), (0.08, 0.18, 1.40), MATS["weapon"], props)
            child_cube(name + "_PROP_BLADE_B_%s" % side, root, (1.22, side * 3.0, -0.30), (0.08, 1.40, 0.18), MATS["weapon"], props)
        for frame, loc, rot in path:
            root.location = loc
            root.rotation_euler = rot
            root.keyframe_insert(data_path="location", frame=frame)
            root.keyframe_insert(data_path="rotation_euler", frame=frame)
        return root

    # Four bombers, two on each side, loose staggered formation; all approach the camera.
    pi = math.pi
    bomber_paths = [
        ("JAPANESE_BOMBER_LEFT_NEAR", [
            (1, (-105, -18, 119), (0.03, 0.02, pi)), (28, (-128, -20, 116), (0.05, 0.02, pi + 0.01)),
            (48, (-154, -22, 112), (0.10, 0.04, pi + 0.02)), (68, (-181, -23, 107), (0.05, 0.02, pi + 0.02)),
            (92, (-214, -24, 101), (0.02, 0.0, pi))]),
        ("JAPANESE_BOMBER_LEFT_FAR", [
            (1, (-78, -48, 125), (-0.05, 0.04, pi - 0.02)), (28, (-101, -50, 121), (-0.02, 0.02, pi - 0.02)),
            (48, (-130, -48, 116), (-0.12, 0.03, pi - 0.03)), (68, (-160, -45, 111), (-0.06, 0.02, pi - 0.02)),
            (92, (-196, -42, 105), (-0.02, 0.0, pi - 0.02))]),
        ("JAPANESE_BOMBER_RIGHT_NEAR", [
            (1, (-92, 20, 122), (0.02, -0.02, pi + 0.03)), (28, (-116, 21, 120), (0.02, -0.04, pi + 0.03)),
            (48, (-144, 19, 115), (-0.10, -0.02, pi + 0.02)), (68, (-174, 17, 109), (-0.04, 0.0, pi + 0.02)),
            (92, (-207, 15, 103), (0.0, 0.0, pi + 0.02))]),
        ("JAPANESE_BOMBER_RIGHT_FAR", [
            (1, (-62, 48, 128), (0.06, 0.04, pi - 0.04)), (28, (-86, 46, 124), (0.04, 0.02, pi - 0.04)),
            (48, (-116, 43, 119), (0.14, 0.05, pi - 0.03)), (68, (-150, 40, 113), (0.08, 0.03, pi - 0.02)),
            (92, (-188, 36, 106), (0.02, 0.0, pi - 0.02))]),
    ]
    bombers = [build_bomber(name, path, 1.0 if "NEAR" in name else 0.88) for name, path in bomber_paths]

    # Four visible bomb trajectories at staggered release / middle / terminal stages.
    make_aircraft_bomb("AIR_BOMB_MAIN", 50, (-156, -20, 110), 90, (-181, -8, 1.1), start_loc=(-105, -18, 118))
    make_aircraft_bomb("AIR_BOMB_LEFT_FAR", 55, (-132, -46, 114), 98, (-191, -29, 1.1), start_loc=(-78, -48, 124))
    make_aircraft_bomb("AIR_BOMB_RIGHT_NEAR", 60, (-146, 17, 111), 104, (-169, 26, 1.1), start_loc=(-92, 20, 121))
    make_aircraft_bomb("AIR_BOMB_RIGHT_FAR", 66, (-118, 41, 116), 110, (-151, 38, 1.1), start_loc=(-62, 48, 128))

    pigeon = make_pigeon()
    return bombers, pigeon



def make_bullet_tracer(name, start, end, start_frame, end_frame):
    fx = get_collection("BFP_V20_18_BATTLE_FX")
    direction = Vector(end) - Vector(start)
    center = (Vector(start) + Vector(end)) * 0.5
    obj = cube(name, center, (max(1.2, direction.length), 0.035, 0.035), MATS["tracer"], fx)
    obj.rotation_euler = direction.to_track_quat('X', 'Z').to_euler()
    obj.location = start
    obj.keyframe_insert(data_path="location", frame=start_frame)
    obj.scale = (0.001, 0.001, 0.001)
    obj.keyframe_insert(data_path="scale", frame=start_frame - 1)
    obj.scale = (1, 1, 1)
    obj.keyframe_insert(data_path="scale", frame=start_frame)
    obj.location = end
    obj.keyframe_insert(data_path="location", frame=end_frame)
    obj.scale = (0.001, 0.001, 0.001)
    obj.keyframe_insert(data_path="scale", frame=end_frame + 1)
    return obj



def animate_hit_fall(actor, hit_frame, down_frame, direction=1.0):
    """Readable non-graphic hit reaction: recoil, loss of balance, then fall."""
    root = actor["root"]
    base = root.location.copy()
    yaw = root.rotation_euler.z
    root.location = base
    root.rotation_euler = (0.0, 0.0, yaw)
    root.keyframe_insert(data_path="location", frame=hit_frame - 3)
    root.keyframe_insert(data_path="rotation_euler", frame=hit_frame - 3)
    root.location = (base.x - 0.15, base.y, base.z + 0.12)
    root.rotation_euler = (0.10, 0.0, yaw)
    root.keyframe_insert(data_path="location", frame=hit_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=hit_frame)
    root.location = (base.x + direction * 0.25, base.y, base.z - 0.30)
    root.rotation_euler = (0.0, direction * 1.32, yaw)
    root.keyframe_insert(data_path="location", frame=down_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=down_frame)


def animate_wounded_body(root, start_frame, end_frame, dx=0.35, dy=0.12):
    """Small restrained movement for a wounded/fallen figure."""
    base = root.location.copy()
    yaw = root.rotation_euler.z
    for frame, loc, rot in [
        (start_frame, (base.x, base.y, base.z), (0.0, 0.0, yaw)),
        ((start_frame + end_frame) // 2,
         (base.x + dx, base.y + dy, base.z + 0.04), (0.0, 0.05, yaw + 0.08)),
        (end_frame, (base.x + dx * 1.25, base.y + dy * 1.2, base.z), (0.0, 0.02, yaw + 0.12)),
    ]:
        root.location = loc
        root.rotation_euler = rot
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)

def animate_head_turn(actor, start_frame, end_frame, angle_z=0.45):
    """Small head turn for close-up readability."""
    head = actor["head"]
    head.rotation_euler = (0.0, 0.0, 0.0)
    head.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    head.rotation_euler = (0.0, 0.0, angle_z)
    head.keyframe_insert(data_path="rotation_euler", frame=(start_frame + end_frame) // 2)
    head.rotation_euler = (0.0, 0.0, 0.0)
    head.keyframe_insert(data_path="rotation_euler", frame=end_frame)



def animate_rifle_burst(actor, shot_frames, recover_frame=None, recoil=0.10):
    """Readable short firing burst: shoulders brace, rifle recoils, then settles."""
    left = actor["left_arm"]
    right = actor["right_arm"]
    left_base = tuple(left.rotation_euler)
    right_base = tuple(right.rotation_euler)
    for arm, base, side in ((left, left_base, -1.0), (right, right_base, 1.0)):
        if shot_frames:
            arm.rotation_euler = base
            arm.keyframe_insert(data_path="rotation_euler", frame=max(1, shot_frames[0] - 2))
        for frame in shot_frames:
            arm.rotation_euler = (base[0] + 0.05, base[1] + side * 0.08, base[2])
            arm.keyframe_insert(data_path="rotation_euler", frame=frame)
            arm.rotation_euler = (base[0], base[1] - side * 0.025, base[2])
            arm.keyframe_insert(data_path="rotation_euler", frame=frame + 1)
            arm.rotation_euler = base
            arm.keyframe_insert(data_path="rotation_euler", frame=frame + 3)
        if recover_frame is not None:
            arm.rotation_euler = base
            arm.keyframe_insert(data_path="rotation_euler", frame=recover_frame)

    rifle = actor.get("rifle")
    if rifle is not None:
        base_loc = rifle.location.copy()
        base_rot = rifle.rotation_euler.copy()
        rifle.location = base_loc
        rifle.rotation_euler = base_rot
        rifle.keyframe_insert(data_path="location", frame=max(1, shot_frames[0] - 2))
        rifle.keyframe_insert(data_path="rotation_euler", frame=max(1, shot_frames[0] - 2))
        for frame in shot_frames:
            rifle.location = (base_loc.x - recoil, base_loc.y, base_loc.z + 0.025)
            rifle.rotation_euler = (base_rot.x, base_rot.y - 0.06, base_rot.z)
            rifle.keyframe_insert(data_path="location", frame=frame)
            rifle.keyframe_insert(data_path="rotation_euler", frame=frame)
            rifle.location = base_loc
            rifle.rotation_euler = base_rot
            rifle.keyframe_insert(data_path="location", frame=frame + 2)
            rifle.keyframe_insert(data_path="rotation_euler", frame=frame + 2)


def animate_hit_fall_performance(actor, hit_frame, down_frame, direction=1.0):
    """Multi-part hit reaction: impact recoil, arm release, loss of balance and fall."""
    root = actor["root"]
    base = root.location.copy()
    yaw = root.rotation_euler.z
    root.location = base
    root.rotation_euler = (0.0, 0.0, yaw)
    root.keyframe_insert(data_path="location", frame=hit_frame - 3)
    root.keyframe_insert(data_path="rotation_euler", frame=hit_frame - 3)
    root.location = (base.x - 0.18, base.y, base.z + 0.10)
    root.rotation_euler = (0.08, direction * 0.16, yaw)
    root.keyframe_insert(data_path="location", frame=hit_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=hit_frame)
    root.location = (base.x + direction * 0.22, base.y, base.z - 0.28)
    root.rotation_euler = (0.0, direction * 1.30, yaw)
    root.keyframe_insert(data_path="location", frame=down_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=down_frame)

    for arm_name, sign in (("left_arm", -1.0), ("right_arm", 1.0)):
        arm = actor[arm_name]
        base_rot = tuple(arm.rotation_euler)
        arm.rotation_euler = base_rot
        arm.keyframe_insert(data_path="rotation_euler", frame=hit_frame - 3)
        arm.rotation_euler = (base_rot[0] + 0.20, base_rot[1] + sign * 0.72, base_rot[2])
        arm.keyframe_insert(data_path="rotation_euler", frame=hit_frame)
        arm.rotation_euler = (base_rot[0] + 0.10, base_rot[1] + sign * 1.05, base_rot[2])
        arm.keyframe_insert(data_path="rotation_euler", frame=down_frame)

    for leg_name, sign in (("left_leg", 1.0), ("right_leg", -1.0)):
        leg = actor[leg_name]
        base_rot = tuple(leg.rotation_euler)
        leg.rotation_euler = base_rot
        leg.keyframe_insert(data_path="rotation_euler", frame=hit_frame - 3)
        leg.rotation_euler = (base_rot[0], base_rot[1] + sign * 0.34, base_rot[2])
        leg.keyframe_insert(data_path="rotation_euler", frame=hit_frame)
        leg.rotation_euler = (base_rot[0], base_rot[1] + sign * 0.62, base_rot[2])
        leg.keyframe_insert(data_path="rotation_euler", frame=down_frame)

    head = actor["head"]
    head.rotation_euler = (0.0, 0.0, 0.0)
    head.keyframe_insert(data_path="rotation_euler", frame=hit_frame - 3)
    head.rotation_euler = (0.12, 0.0, direction * 0.22)
    head.keyframe_insert(data_path="rotation_euler", frame=hit_frame)
    head.rotation_euler = (0.0, 0.0, direction * 0.38)
    head.keyframe_insert(data_path="rotation_euler", frame=down_frame)


def animate_duck_and_recover(actor, start_frame, duck_frame, recover_frame, depth=0.16):
    """Short tactical flinch/duck in response to nearby fire or blast."""
    root = actor["root"]
    base = root.location.copy()
    yaw = root.rotation_euler.z
    root.location = base
    root.rotation_euler = (0.0, 0.0, yaw)
    root.keyframe_insert(data_path="location", frame=start_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    root.location = (base.x - depth * 0.55, base.y, base.z - depth)
    root.rotation_euler = (0.10, 0.0, yaw)
    root.keyframe_insert(data_path="location", frame=duck_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=duck_frame)
    root.location = base
    root.rotation_euler = (0.0, 0.0, yaw)
    root.keyframe_insert(data_path="location", frame=recover_frame)
    root.keyframe_insert(data_path="rotation_euler", frame=recover_frame)

    for arm_name, sign in (("left_arm", -1.0), ("right_arm", 1.0)):
        arm = actor[arm_name]
        base_rot = tuple(arm.rotation_euler)
        arm.rotation_euler = base_rot
        arm.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        arm.rotation_euler = (base_rot[0] + 0.18, base_rot[1] + sign * 0.18, base_rot[2])
        arm.keyframe_insert(data_path="rotation_euler", frame=duck_frame)
        arm.rotation_euler = base_rot
        arm.keyframe_insert(data_path="rotation_euler", frame=recover_frame)


def animate_wading_actor(actor, path):
    """Slow, weighted water-crossing gait; avoids the dry-land running cycle."""
    root = actor["root"]
    for frame, loc, yaw in path:
        root.location = loc
        root.rotation_euler.z = yaw
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    start, end = path[0][0], path[-1][0]
    arm_factor = 0.10 if actor.get("rifle") else 0.22
    for frame in range(start, end + 1, 6):
        phase = (frame - start) * (2.0 * math.pi / 34.0)
        swing = math.sin(phase) * 0.24
        actor["left_leg"].rotation_euler.y = swing
        actor["right_leg"].rotation_euler.y = -swing
        actor["left_arm"].rotation_euler.y = -swing * arm_factor
        actor["right_arm"].rotation_euler.y = swing * arm_factor
        for key in ("left_leg", "right_leg", "left_arm", "right_arm"):
            actor[key].keyframe_insert(data_path="rotation_euler", frame=frame)

    for obj in (root, actor["left_leg"], actor["right_leg"], actor["left_arm"], actor["right_arm"]):
        if obj.animation_data and obj.animation_data.action:
            try:
                for fc in obj.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = 'AUTO_CLAMPED'
                        kp.handle_right_type = 'AUTO_CLAMPED'
            except Exception:
                pass


def animate_box_handoff(sender, receiver, box):
    """Clear hand-to-hand transfer: sender releases only after receiver secures the box."""
    for arm_name in ("left_arm", "right_arm"):
        arm = sender[arm_name]
        for frame, angle in ((538, -0.05), (541, -0.70), (546, -0.78), (550, -0.10), (553, 0.0)):
            arm.rotation_euler.y = angle
            arm.keyframe_insert(data_path="rotation_euler", frame=frame)
        arm = receiver[arm_name]
        for frame, angle in ((538, 0.0), (541, -0.20), (546, -0.72), (550, -0.72), (553, 0.0)):
            arm.rotation_euler.y = angle
            arm.keyframe_insert(data_path="rotation_euler", frame=frame)

    for frame, loc in (
        (538, (199.0, -4.0, 1.12)),
        (541, (199.7, -4.0, 1.16)),
        (546, (201.0, -4.0, 1.14)),
        (550, (202.0, -4.0, 1.08)),
        (553, (202.2, -4.0, 1.08)),
        (560, (205.0, -2.0, 1.10)),
        (580, (211.0, 0.0, 1.10)),
    ):
        box.location = loc
        box.keyframe_insert(data_path="location", frame=frame)



def make_falling_branch(name, start_loc, start_frame, end_frame, fall_y=0.9, fall_z=1.4):
    """A thick low-poly branch breaks loose and falls near the woodland route."""
    coll = get_collection("BFP_V20_18_BATTLE_FX")
    branch = cube(name, start_loc, (7.2, 0.24, 0.24), MATS["branch"], coll,
                  rot=(0.0, 0.0, random.uniform(-0.35, 0.35)))
    start_rot = branch.rotation_euler.copy()
    branch.location = start_loc
    branch.keyframe_insert(data_path="location", frame=start_frame)
    branch.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    branch.location = (start_loc[0] + 1.2, start_loc[1] + fall_y, fall_z)
    branch.rotation_euler = (start_rot.x + 0.25, start_rot.y + 0.95, start_rot.z + 0.35)
    branch.keyframe_insert(data_path="location", frame=end_frame)
    branch.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    return branch


def make_small_blast(name, loc, event_frame, radius=2.0):
    """Short flash and expanding low-poly smoke cloud."""
    coll = get_collection("BFP_V20_18_BATTLE_FX")
    flash = ico(name + "_FLASH", loc, (0.08, 0.08, 0.08), MATS["blast"], coll, sub=1)
    for frame, scale in [
        (event_frame - 1, (0.001, 0.001, 0.001)),
        (event_frame + 1, (radius, radius * 0.8, radius * 0.7)),
        (event_frame + 4, (0.12, 0.12, 0.12)),
    ]:
        flash.scale = scale
        flash.keyframe_insert(data_path="scale", frame=frame)

    for i, offset in enumerate(((0, 0, 0), (radius * 0.55, 0.25, 0.45), (-radius * 0.4, -0.3, 0.7))):
        puff = ico(name + "_SMOKE_%02d" % i,
                   (loc[0] + offset[0], loc[1] + offset[1], loc[2] + offset[2]),
                   (0.05, 0.05, 0.05), MATS["smoke"] if i != 2 else MATS["dust"],
                   coll, sub=1)
        for frame, scale, dz in [
            (event_frame, (0.02, 0.02, 0.02), 0.0),
            (event_frame + 8, (radius * 0.9, radius * 0.75, radius * 0.7), 0.4),
            (event_frame + 24, (radius * 1.35, radius * 1.15, radius * 1.25), 1.8),
        ]:
            puff.scale = scale
            puff.location = (loc[0] + offset[0], loc[1] + offset[1], loc[2] + offset[2] + dz)
            puff.keyframe_insert(data_path="scale", frame=frame)
            puff.keyframe_insert(data_path="location", frame=frame)


def make_water_splash(name, loc, event_frame):
    """Simple surface splash cue when a soldier falls into the river."""
    coll = get_collection("BFP_V20_18_BATTLE_FX")
    splash = ico(name, loc, (0.08, 0.08, 0.08), MATS["rock_light"], coll, sub=1)
    for frame, scale in (
        (event_frame - 1, (0.001, 0.001, 0.001)),
        (event_frame + 1, (0.85, 0.55, 0.18)),
        (event_frame + 4, (0.32, 0.24, 0.10)),
        (event_frame + 8, (0.001, 0.001, 0.001)),
    ):
        splash.scale = scale
        splash.keyframe_insert(data_path="scale", frame=frame)
    return splash


def make_non_graphic_limb_debris(name, loc, dims, rot):
    """Muted uniform-colored block silhouettes only; no exposed tissue or gore."""
    coll = get_collection("BFP_V20_16_CHARACTERS")
    return cube(name, loc, dims, MATS["casualty_charred"], coll, rot=rot)


def build_characters_and_props():
    random.seed(SEED + 707)

    # 1) Forest: Chinese soldiers use rock/wood cover, move through the gaps;
    # scattered casualties remain non-graphic and irregular.
    forest_run_a = make_actor("CN_FOREST_RUNNER_A", (-165, -4, 0), yaw=0.0, faction="cn", rifle=True)
    animate_actor(forest_run_a, [
        (108, (-165, -4, 0), 0.10),
        (170, (-158, -2, 0), 0.18),
        (245, (-151, 1, 0), 0.08),
    ], run=True)

    forest_run_b = make_actor("CN_FOREST_RUNNER_B", (-151, 18, 0), yaw=0.0, faction="cn", rifle=True)
    animate_actor(forest_run_b, [
        (118, (-151, 18, 0), 0.0),
        (180, (-145, 17, 0), -0.10),
        (248, (-138, 15, 0), 0.0),
    ], run=True)

    forest_cover_a = make_actor("CN_FOREST_COVER_A", (-139, 18, 0), yaw=0.0,
                                faction="cn", posture="crouch", rifle=True)
    forest_cover_a["left_arm"].rotation_euler.y = -0.9
    forest_cover_a["right_arm"].rotation_euler.y = -0.9

    forest_cover_b = make_actor("CN_FOREST_COVER_B", (-92, -18, 0), yaw=0.0,
                                faction="cn", posture="crouch", rifle=True)

    jp_forest = make_actor("JP_FOREST_ADVANCE_A", (-92, 8, 0), yaw=0.0,
                           faction="jp", rifle=True)
    animate_actor(jp_forest, [
        (180, (-92, 8, 0), 0.0),
        (220, (-88, 7, 0), 0.0),
        (260, (-84, 6, 0), 0.0),
    ], run=True)

    jp_close_a = make_actor("JP_CLOSE_REAR_SHOOTER_A", (-157, -3, 0), yaw=0.0, faction="jp", rifle=True)
    jp_close_b = make_actor("JP_CLOSE_REAR_SHOOTER_B", (-151, 2, 0), yaw=0.0, faction="jp", rifle=True)
    for shooter in (jp_close_a, jp_close_b):
        for arm_key in ("left_arm", "right_arm"):
            shooter[arm_key].rotation_euler.y = -0.68
            shooter[arm_key].keyframe_insert(data_path="rotation_euler", frame=112)
            shooter[arm_key].rotation_euler.y = -0.76
            shooter[arm_key].keyframe_insert(data_path="rotation_euler", frame=120)
            shooter[arm_key].rotation_euler.y = -0.68
            shooter[arm_key].keyframe_insert(data_path="rotation_euler", frame=126)
    animate_rifle_burst(jp_close_a, [114, 119, 123], recover_frame=130, recoil=0.08)
    animate_rifle_burst(jp_close_b, [116, 121, 125], recover_frame=132, recoil=0.08)
    jp_fall = make_actor("JP_CLOSE_HIT_AND_FALL", (-148, -1, 0), yaw=0.0, faction="jp", rifle=True)
    animate_hit_fall_performance(jp_fall, 136, 145, direction=1.0)
    animate_head_turn(jp_close_b, 136, 150, angle_z=-0.42)
    animate_duck_and_recover(jp_close_b, 138, 142, 154, depth=0.13)

    cn_cover_close = make_actor("CN_ROCK_COVER_CLOSE_SHOOTER", (-137, -8, 0),
                                yaw=0.0, faction="cn", posture="crouch", rifle=True)
    cn_cover_second = make_actor("CN_ROCK_COVER_SECOND_SHOOTER", (-130, -12, 0),
                                 yaw=0.0, faction="cn", posture="crouch", rifle=True)
    for actor in (cn_cover_close, cn_cover_second):
        actor["left_arm"].rotation_euler.y = -0.72
        actor["right_arm"].rotation_euler.y = -0.72
    animate_rifle_burst(cn_cover_close, [162, 167, 172], recover_frame=180, recoil=0.07)
    animate_rifle_burst(cn_cover_second, [169, 174], recover_frame=181, recoil=0.07)
    cn_fall = make_actor("CN_ROCK_COVER_HIT_AND_FALL", (-124, -5, 0),
                         yaw=0.0, faction="cn", rifle=True)
    animate_hit_fall_performance(cn_fall, 184, 197, direction=-1.0)
    animate_head_turn(cn_cover_second, 184, 200, angle_z=0.38)
    animate_duck_and_recover(cn_cover_second, 184, 188, 202, depth=0.14)

    # Maintain people in foreground, midground and background during the forest section.
    forest_fg_runner = make_actor("CN_FOREST_FG_RUNNER", (-161, -11, 0), yaw=0.0, faction="cn", rifle=True)
    animate_actor(forest_fg_runner, [
        (110, (-161, -11, 0), 0.0),
        (150, (-156, -10, 0), 0.0),
        (205, (-151, -9, 0), 0.0),
    ], run=True)
    forest_mid_shooter = make_actor("CN_FOREST_MID_SHOOTER", (-141, 4, 0), yaw=0.0, faction="cn", posture="crouch", rifle=True)
    animate_rifle_burst(forest_mid_shooter, [150, 156], recover_frame=164, recoil=0.06)
    forest_bg_jp = make_actor("JP_FOREST_BACKGROUND_ADVANCE", (-121, 18, 0), yaw=0.0, faction="jp", rifle=True)
    animate_actor(forest_bg_jp, [
        (130, (-121, 18, 0), 0.0),
        (190, (-116, 17, 0), 0.0),
        (250, (-110, 16, 0), 0.0),
    ], run=True)
    animate_head_turn(jp_close_a, 118, 136, angle_z=0.18)

    wounded_forest = make_casualty("CN_WOUNDED_FOREST_CRAWL_A", (-115, -2, -0.25),
                                   yaw=0.2, faction="cn", pose="side")
    animate_wounded_body(wounded_forest, 205, 248, dx=0.55, dy=0.18)

    extra_forest_casualties = [
        ((-171, -17, -0.25), 0.2, "side", "cn"),
        ((-163, 12, -0.25), -0.6, "prone", "cn"),
        ((-153, -19, -0.25), 1.1, "supine", "jp"),
        ((-145, 13, -0.25), -1.0, "side", "cn"),
        ((-137, 23, -0.25), 0.5, "prone", "jp"),
        ((-127, 17, -0.25), -0.8, "supine", "cn"),
        ((-119, -19, -0.25), 1.3, "side", "cn"),
        ((-103, 25, -0.25), -0.3, "prone", "jp"),
        ((-96, -17, -0.25), 0.8, "side", "cn"),
        ((-86, 23, -0.25), -1.1, "supine", "cn"),
    ]
    for i, (loc, yaw, pose, faction) in enumerate(extra_forest_casualties):
        make_casualty("FOREST_EXTRA_CASUALTY_%02d" % i, loc, yaw=yaw,
                      faction=faction, pose=pose)

    make_non_graphic_limb_debris("FOREST_UNIFORM_LIMB_DEBRIS_A", (-142, -2, 0.12),
                                 (0.72, 0.18, 0.18), (0.1, 0.2, 0.6))
    make_non_graphic_limb_debris("FOREST_UNIFORM_LIMB_DEBRIS_B", (-112, 7, 0.12),
                                 (0.62, 0.18, 0.18), (-0.1, 0.3, -0.8))

    for i, spec in enumerate([
        ((-160, -24, -0.25), -0.25, "prone"),
        ((-132, 28, -0.25), 0.65, "side"),
        ((-108, -25, -0.25), -0.9, "supine"),
        ((-79, 27, -0.25), 1.4, "prone"),
    ]):
        loc, yaw, pose = spec
        make_casualty("CN_FOREST_CASUALTY_%02d" % i, loc, yaw=yaw, faction="cn", pose=pose)

    # 2) Li Xingou ravine: retreating survivors and scattered fallen soldiers.
    ravine_survivors = [
        ("CN_RAVINE_RUNNER_01", (-45, -7, 0), (-38, -7, 0)),
        ("CN_RAVINE_RUNNER_02", (-41, 7, 0), (-34, 8, 0)),
        ("CN_RAVINE_RUNNER_03", (-32, -12, 0), (-26, -11, 0)),
    ]
    for name, start, end in ravine_survivors:
        actor = make_actor(name, start, yaw=0.0, faction="cn", rifle=True)
        animate_actor(actor, [
            (215, start, 0.0),
            (245, ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, 0), 0.0),
            (275, end, 0.0),
        ], run=True)
        if name == "CN_RAVINE_RUNNER_02":
            animate_head_turn(actor, 242, 268, angle_z=-0.36)

    for i, (loc, yaw, pose, faction) in enumerate([
        ((-49, -4, -0.25), 0.3, "prone", "cn"),
        ((-34, 11, -0.25), -0.8, "side", "cn"),
        ((-20, -8, -0.25), 1.2, "supine", "cn"),
        ((-4, 7, -0.25), -0.4, "prone", "jp"),
        ((-13, 16, -0.25), 2.0, "side", "cn"),
    ]):
        make_casualty(
            "RAVINE_CASUALTY_%02d" % i,
            loc, yaw=yaw, faction=faction, pose=pose,
            charred=(faction == "cn")
        )
    make_casualty(
        "LIXINGOU_FIFTH_CHARRED_CASUALTY",
        (2, -14, -0.25), yaw=-1.1, faction="cn", pose="side", charred=True
    )

    for i, (loc, yaw, faction, pose) in enumerate([
        ((-45, 13, -0.25), 0.5, "cn", "side"),
        ((-37, -14, -0.25), -0.7, "cn", "prone"),
        ((-28, 12, -0.25), 1.2, "jp", "supine"),
        ((-18, -13, -0.25), -0.4, "cn", "side"),
        ((-9, 14, -0.25), 0.8, "cn", "prone"),
        ((-1, -12, -0.25), -1.1, "jp", "side"),
    ]):
        make_casualty("RAVINE_EXTRA_CASUALTY_%02d" % i, loc, yaw=yaw,
                      faction=faction, pose=pose)

    ravine_rear_runner = make_actor("CN_RAVINE_REAR_RUNNER", (-57, 10, 0), yaw=0.0, faction="cn", rifle=True)
    animate_actor(ravine_rear_runner, [
        (278, (-57, 10, 0), 0.0),
        (314, (-49, 9, 0), 0.0),
        (338, (-44, 8, 0), 0.0),
    ], run=True)
    ravine_far_jp = make_actor("JP_RAVINE_FAR_THREAT", (-20, 18, 0), yaw=0.0, faction="jp", rifle=True)

    # 3) Wutonggou: Japanese squad advances in a staggered formation toward the damaged house.
    jp_specs = [
        ((62, 8, 0), (45, 3, 0)),
        ((66, 1, 0), (48, -1, 0)),
        ((59, 14, 0), (42, 6, 0)),
        ((68, -5, 0), (50, -5, 0)),
        ((57, -1, 0), (40, -4, 0)),
        ((64, 20, 0), (48, 12, 0)),
    ]
    for i, (start, end) in enumerate(jp_specs):
        actor = make_actor("JP_WUTONGGOU_ADVANCE_%02d" % i, start, yaw=math.pi,
                           faction="jp", rifle=True)
        animate_actor(actor, [
            (278, start, math.pi),
            (306, ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, 0), math.pi),
            (334, end, math.pi),
        ], run=True)

    jp_house_close_left = make_actor("JP_HOUSE_CLOSE_LEFT", (50, -2, 0), yaw=math.pi, faction="jp", rifle=True)
    jp_house_close_right = make_actor("JP_HOUSE_CLOSE_RIGHT", (53, 2, 0), yaw=math.pi, faction="jp", rifle=True)
    animate_actor(jp_house_close_left, [
        (340, (50, -2, 0), math.pi),
        (360, (44, -2, 0), math.pi),
        (376, (40, -2, 0), math.pi),
    ], run=True)
    animate_actor(jp_house_close_right, [
        (344, (53, 2, 0), math.pi),
        (364, (47, 2, 0), math.pi),
        (378, (43, 2, 0), math.pi),
    ], run=True)
    house_bg_jp = make_actor("JP_HOUSE_BACKGROUND_PINCER", (49, 12, 0), yaw=math.pi, faction="jp", rifle=True)
    animate_actor(house_bg_jp, [
        (352, (49, 12, 0), math.pi),
        (378, (46, 10, 0), math.pi),
        (404, (43, 8, 0), math.pi),
    ], run=True)

    for i in range(3):
        actor = make_actor("JP_HOUSE_BLAST_FALL_%02d" % i,
                           (40 + i * 1.5, -1 + i * 3.0, 0),
                           yaw=math.pi, faction="jp", rifle=True)
        animate_hit_fall_performance(actor, 384 + i * 2, 398 + i * 2, direction=1.0)
    jp_house_close = make_actor("JP_HOUSE_CLOSE_SHOOTER", (36, -1, 0),
                                yaw=0.0, faction="jp", rifle=True)
    jp_house_close["left_arm"].rotation_euler.y = -0.7
    jp_house_close["right_arm"].rotation_euler.y = -0.7
    animate_rifle_burst(jp_house_close, [360, 366, 372], recover_frame=378, recoil=0.08)


    # Chinese defenders occupy low cover away from the camera's breach corridor.
    defender_a = make_actor("CN_WUTONGGOU_COVER_A", (24, -18, 0), yaw=0.0,
                            faction="cn", posture="crouch", rifle=True)
    defender_b = make_actor("CN_WUTONGGOU_COVER_B", (31, -18, 0), yaw=0.0,
                            faction="cn", posture="crouch", rifle=True)
    make_casualty("CN_WUTONGGOU_CASUALTY_A", (16, -11, -0.25), yaw=0.5, faction="cn", pose="side")
    make_casualty("JP_WUTONGGOU_CASUALTY_A", (52, 18, -0.25), yaw=-0.6, faction="jp", pose="prone")

    # 4) Huangcaoguan river: bodies on the riverbed and moving soldiers in shallow water.
    water_bodies = [
        ((92, 7, -3.45), 0.2, "prone", "cn"),
        ((108, -8, -3.50), -0.8, "side", "cn"),
        ((124, 6, -3.45), 1.1, "supine", "jp"),
        ((143, -8, -3.45), -0.4, "prone", "cn"),
        ((158, 7, -3.50), 0.7, "side", "cn"),
        ((176, -5, -3.45), -1.2, "supine", "jp"),
        ((184, 9, -3.45), 0.3, "prone", "cn"),
    ]
    for i, (loc, yaw, pose, faction) in enumerate(water_bodies):
        make_casualty("RIVERBED_CASUALTY_%02d" % i, loc, yaw=yaw,
                      faction=faction, pose=pose, submerged=True)

    water_runners = [
        ((96, 4, -0.72), (108, 4, -0.72)),
        ((113, -5, -0.72), (126, -5, -0.72)),
        ((133, 9, -0.72), (145, 9, -0.72)),
        ((153, -10, -0.72), (166, -10, -0.72)),
    ]
    for i, (start, end) in enumerate(water_runners):
        actor = make_actor("CN_SHALLOW_WATER_RUNNER_%02d" % i, start, yaw=0.0,
                           faction="cn", rifle=(i % 2 == 0))
        animate_wading_actor(actor, [
            (360, start, 0.0),
            (410, ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, start[2]), 0.0),
            (455, end, 0.0),
        ])

    for i, (loc, yaw, pose, faction) in enumerate([
        ((101, -10, -3.48), 0.4, "side", "jp"),
        ((116, 10, -3.50), -0.9, "prone", "cn"),
        ((132, -10, -3.48), 1.4, "supine", "cn"),
        ((148, 9, -3.50), -0.2, "side", "jp"),
        ((164, -9, -3.48), 0.9, "prone", "cn"),
        ((178, 10, -3.50), -1.2, "supine", "cn"),
    ]):
        body = make_casualty("RIVER_EXTRA_BODY_%02d" % i, loc, yaw=yaw,
                             faction=faction, pose=pose, submerged=True)
        if i in (1, 4):
            animate_wounded_body(body, 438 + i * 3, 492 + i * 2, dx=0.24, dy=0.16)

    river_support = make_actor("RIVER_SUPPORTING_SOLDIER", (116, 4, -0.72),
                               yaw=0.0, faction="cn", posture="crouch", rifle=False)
    river_injured = make_actor("RIVER_INJURED_SOLDIER", (118, 5, -0.85),
                               yaw=0.0, faction="cn", posture="crouch", rifle=False)
    river_support["right_arm"].rotation_euler.y = -1.0
    river_support["left_arm"].rotation_euler.y = -0.55
    river_injured["left_arm"].rotation_euler.y = -0.9
    animate_actor(river_support, [
        (440, (116, 4, -0.72), 0.0),
        (470, (118, 4.5, -0.72), 0.0),
        (500, (120, 5, -0.72), 0.0),
    ], run=False)
    animate_actor(river_injured, [
        (440, (118, 5, -0.85), 0.0),
        (470, (119, 5.5, -0.85), 0.0),
        (500, (121, 6, -0.85), 0.0),
    ], run=False)
    animate_head_turn(river_support, 440, 500, angle_z=0.20)
    animate_head_turn(river_injured, 440, 500, angle_z=-0.24)
    for frame, support_right, support_left, injured_left in (
        (440, -0.65, -0.40, -0.65),
        (452, -1.00, -0.68, -0.90),
        (470, -0.92, -0.60, -0.82),
        (488, -0.78, -0.52, -0.70),
        (500, -0.65, -0.40, -0.65),
    ):
        river_support["right_arm"].rotation_euler.y = support_right
        river_support["right_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)
        river_support["left_arm"].rotation_euler.y = support_left
        river_support["left_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)
        river_injured["left_arm"].rotation_euler.y = injured_left
        river_injured["left_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)

    for i, (start, end) in enumerate([
        ((104, -8, -0.72), (112, -8, -0.72)),
        ((126, 12, -0.72), (137, 12, -0.72)),
        ((145, -12, -0.72), (156, -12, -0.72)),
        ((168, 6, -0.72), (179, 6, -0.72)),
    ]):
        actor = make_actor("RIVER_EXTRA_RUNNER_%02d" % i, start, yaw=0.0,
                           faction="cn", rifle=False)
        animate_wading_actor(actor, [
            (430, start, 0.0),
            (465, ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, start[2]), 0.0),
            (500, end, 0.0),
        ])

    # Keep foreground, midground and background human activity during the river section.
    river_fg_cross_1 = make_actor("CN_RIVER_FG_CROSS_1", (88, 1, -0.72), yaw=0.0, faction="cn", rifle=False)
    river_fg_cross_2 = make_actor("CN_RIVER_FG_CROSS_2", (99, -4, -0.72), yaw=0.0, faction="cn", rifle=False)
    river_mid_cross = make_actor("CN_RIVER_MID_CROSS", (124, 8, -0.72), yaw=0.0, faction="cn", rifle=True)
    river_bg_cross = make_actor("CN_RIVER_BG_CROSS", (160, -8, -0.72), yaw=0.0, faction="cn", rifle=False)
    for actor, path in [
        (river_fg_cross_1, [(420, (88, 1, -0.72), 0.0), (458, (96, 1, -0.72), 0.0), (500, (103, 1, -0.72), 0.0)]),
        (river_fg_cross_2, [(432, (99, -4, -0.72), 0.0), (470, (108, -4, -0.72), 0.0), (508, (117, -4, -0.72), 0.0)]),
        (river_mid_cross, [(430, (124, 8, -0.72), 0.0), (472, (133, 8, -0.72), 0.0), (514, (142, 8, -0.72), 0.0)]),
        (river_bg_cross, [(440, (160, -8, -0.72), 0.0), (486, (168, -8, -0.72), 0.0), (528, (176, -8, -0.72), 0.0)]),
    ]:
        animate_wading_actor(actor, path)

    # Surface-floating and falling bodies for clearer readable river action.
    float_body_a = make_casualty("RIVER_SURFACE_FLOAT_A", (110, 1, 0.05), yaw=0.4, faction="cn", pose="supine")
    float_body_b = make_casualty("RIVER_SURFACE_FLOAT_B", (145, -3, 0.02), yaw=-0.9, faction="jp", pose="side")
    animate_wounded_body(float_body_a, 438, 500, dx=0.35, dy=0.02)
    animate_wounded_body(float_body_b, 456, 520, dx=0.28, dy=-0.04)
    river_fall = make_actor("CN_RIVER_CROSSING_HIT_FALL", (130, 2, -0.72), yaw=0.0, faction="cn", rifle=False)
    animate_hit_fall_performance(river_fall, 488, 502, direction=-1.0)

    # One soldier is hit during the underwater passage and falls into the water.
    hit_actor = make_actor("CN_RIVER_HIT_AND_FALL", (143, -1.5, -0.72), yaw=0.0,
                           faction="cn", rifle=True)
    animate_hit_fall_performance(hit_actor, 500, 514, direction=-1.0)
    river_react = make_actor("CN_RIVER_CROSSER_DUCK_REACTION", (126, -3, -0.72),
                             yaw=0.0, faction="cn", rifle=False)
    animate_head_turn(river_react, 486, 506, angle_z=-0.34)
    animate_duck_and_recover(river_react, 486, 494, 508, depth=0.12)

    # 5) Riverbank handoff: the receiver takes the box and runs forward.
    handoff_a = make_actor("CN_BOX_HANDOFF_SENDER", (198, -4, 0), yaw=0.0,
                           faction="cn", rifle=False)
    handoff_b = make_actor("CN_BOX_HANDOFF_RECEIVER", (202, -4, 0), yaw=math.pi,
                           faction="cn", rifle=False)
    box = cube("RIVERBANK_HANDOFF_BOX", (199.0, -4, 1.12), (0.95, 0.62, 0.62),
               MATS["box"], get_collection("BFP_V20_17_PROPS"))
    animate_box_handoff(handoff_a, handoff_b, box)

    animate_actor(handoff_b, [
        (553, (202, -4, 0), math.pi),
        (564, (206, -2, 0), 0.1),
        (580, (211, 0, 0), 0.1),
    ], run=True)
    handoff_follow = make_actor("CN_HANDOFF_FOLLOW_RUNNER", (210, 4, 0), yaw=0.0, faction="cn", rifle=True)
    animate_actor(handoff_follow, [
        (540, (210, 4, 0), 0.0),
        (564, (220, 3, 0), 0.0),
        (592, (230, 2, 0), 0.0),
    ], run=True)
    handoff_bg_group = make_actor("CN_HANDOFF_BACKGROUND_RUNNER", (228, -10, 0), yaw=0.0, faction="cn", rifle=True)

    # 6) Old Meng: strong silhouette, explosive charges around the torso, hand shields sunlight.
    old_meng = make_actor("OLD_MENG", (250, 0, 0), yaw=0.0,
                          faction="old_meng", rifle=False, grenades=8)
    old_meng["root"].scale = (1.15, 1.15, 1.15)
    # He shades his eyes as the camera arrives, then lowers the arm into a firm front hold.
    old_meng["right_arm"].rotation_euler.y = 0.0
    old_meng["right_arm"].keyframe_insert(data_path="rotation_euler", frame=588)
    old_meng["right_arm"].rotation_euler.y = -1.0
    old_meng["right_arm"].keyframe_insert(data_path="rotation_euler", frame=602)
    old_meng["right_arm"].rotation_euler.y = -1.0
    old_meng["right_arm"].keyframe_insert(data_path="rotation_euler", frame=638)
    old_meng["right_arm"].rotation_euler.y = -0.12
    old_meng["right_arm"].keyframe_insert(data_path="rotation_euler", frame=650)
    old_meng["right_arm"].rotation_euler.y = -0.12
    old_meng["right_arm"].keyframe_insert(data_path="rotation_euler", frame=676)
    old_meng["left_arm"].rotation_euler.y = 0.16
    old_meng["left_arm"].keyframe_insert(data_path="rotation_euler", frame=588)
    old_meng["left_arm"].rotation_euler.y = 0.16
    old_meng["left_arm"].keyframe_insert(data_path="rotation_euler", frame=676)
    animate_head_turn(old_meng, 614, 662, angle_z=0.12)

    # Maintain foreground / midground / background around Old Meng.
    old_meng_fg_left = make_actor("CN_OLD_MENG_FG_LEFT", (246, -6, 0), yaw=0.0, faction="cn", rifle=True)
    old_meng_fg_right = make_actor("CN_OLD_MENG_FG_RIGHT", (246, 6, 0), yaw=0.0, faction="cn", rifle=True)
    old_meng_bg_center = make_actor("CN_OLD_MENG_BG_CENTER", (261, 0, 0), yaw=0.0, faction="cn", rifle=True)
    animate_actor(old_meng_bg_center, [
        (600, (261, 0, 0), 0.0),
        (660, (272, 0, 0), 0.0),
        (720, (284, 0, 0), 0.0),
    ], run=True)

    # Guard company soldiers pass around him and continue toward the valley.
    guard_specs = [
        ((236, -12, 0), (270, -14, 0)),
        ((242, 12, 0), (276, 14, 0)),
        ((250, -15, 0), (282, -16, 0)),
        ((255, 15, 0), (289, 16, 0)),
    ]
    for i, (start, end) in enumerate(guard_specs):
        actor = make_actor("CN_GUARD_COMPANY_%02d" % i, start, yaw=0.0, faction="cn", rifle=True)
        animate_actor(actor, [
            (550, start, 0.0),
            (620, ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5, 0), 0.0),
            (700, end, 0.0),
        ], run=True)

    # 7) Main charge: staggered groups run toward +X; camera retreats through the lanes.
    charge_positions = [
        (260, -11), (266, -6), (270, 7), (276, 12),
        (282, -10), (287, -5), (292, 6), (298, 11),
        (304, -12), (309, -7), (313, 7), (318, 12),
        (268, 2), (280, 3), (294, -2), (307, 2),
        (320, -5), (326, 6), (314, 15), (300, -16),
    ]
    for i, (x, y) in enumerate(charge_positions):
        actor = make_actor("CN_MAIN_CHARGE_%02d" % i, (x, y, 0), yaw=0.0,
                           faction="cn", rifle=(i % 3 != 0))
        end_x = x + random.uniform(28, 38)
        end_y = y + random.uniform(-1.2, 1.2)
        animate_actor(actor, [
            (690, (x, y, 0), 0.0),
            (770, (x + (end_x - x) * 0.52, y + (end_y - y) * 0.52, 0), 0.0),
            (850, (end_x, end_y, 0), 0.0),
        ], run=True)

    extra_charge_positions = [
        (263, -18), (271, 18), (279, -19), (286, 19),
        (295, -18), (303, 18), (312, -17), (321, 18),
        (274, 0), (289, 0), (305, 0), (318, -2)
    ]
    for i, (x, y) in enumerate(extra_charge_positions):
        actor = make_actor("CN_MAIN_CHARGE_EXTRA_%02d" % i, (x, y, 0),
                           yaw=0.0, faction="cn", rifle=(i % 2 == 0))
        end_x = x + random.uniform(20, 27)
        end_y = y + random.uniform(-0.8, 0.8)
        animate_actor(actor, [
            (700, (x, y, 0), 0.0),
            (790, (x + (end_x - x) * 0.5, y + (end_y - y) * 0.5, 0), 0.0),
            (880, (end_x, end_y, 0), 0.0),
        ], run=True)

    # Additional non-graphic fallen soldiers sit off the charge lanes and at the valley margins.
    for i, (loc, yaw, faction, pose) in enumerate([
        ((236, -19, -0.25), 0.4, "cn", "side"),
        ((248, 20, -0.25), -0.7, "cn", "prone"),
        ((286, 21, -0.25), 1.1, "jp", "supine"),
        ((315, -20, -0.25), -1.3, "cn", "side"),
    ]):
        make_casualty("WEST_PASS_CASUALTY_%02d" % i, loc, yaw=yaw, faction=faction, pose=pose)

    # A small number of runners continue beyond the camera's final pull-back.
    for i, (x, y) in enumerate(((333, -10), (338, 11), (346, -4))):
        actor = make_actor("CN_VALLEY_EXIT_RUNNER_%02d" % i, (x, y, 0), yaw=0.0,
                           faction="cn", rifle=True)
        animate_actor(actor, [
            (760, (x, y, 0), 0.0),
            (850, (x + 18, y + random.uniform(-1.0, 1.0), 0), 0.0),
        ], run=True)

    make_aircraft()



def build_storyboard_details():
    """Missing storyboard-critical blocking: forest rescue, house doorway pair, river crowd and frame gates."""
    action_coll = get_collection("BFP_V20_19_STORYBOARD_ACTIONS")
    chars = get_collection("BFP_V20_16_CHARACTERS")
    props = get_collection("BFP_V20_17_PROPS")
    random.seed(SEED + 1212)

    # FOREST: soldier pinned beneath a fallen tree; comrade arrives, braces and lifts.
    pinned = make_casualty("CN_FOREST_PINNED_UNDER_TREE", (-108, 12, -0.18),
                           yaw=0.18, faction="cn", pose="side")
    rescuer = make_actor("CN_FOREST_RESCUER", (-114, 9, 0), yaw=0.0,
                         faction="cn", posture="crouch", rifle=False)
    animate_actor(rescuer, [
        (174, (-118, 8, 0), 0.0),
        (188, (-113, 9, 0), 0.0),
        (198, (-111, 10, 0), 0.0),
        (220, (-109, 10, 0), 0.0),
    ], run=False)
    for frame, angle in [(174, -0.15), (188, -0.55), (198, -1.0), (208, -1.12), (220, -0.8)]:
        rescuer["left_arm"].rotation_euler.y = angle
        rescuer["right_arm"].rotation_euler.y = angle * 0.92
        rescuer["left_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)
        rescuer["right_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)
    trunk = beam_between("FOREST_RESCUE_FALLEN_TREE_TRUNK", (-115, 12, 0.82), (-99, 12, 0.82),
                         0.68, MATS["trunk"], action_coll)
    for frame, loc, rot in [
        (174, (-107, 12, 0.82), (0.0, math.pi / 2.0, 0.0)),
        (190, (-107, 12, 0.84), (0.0, math.pi / 2.0, 0.0)),
        (202, (-107, 12, 1.10), (0.0, math.pi / 2.0 - 0.06, 0.0)),
        (214, (-107, 12, 2.05), (0.0, math.pi / 2.0 - 0.12, 0.0)),
        (226, (-107, 12, 2.05), (0.0, math.pi / 2.0 - 0.12, 0.0)),
    ]:
        trunk.location = loc
        trunk.rotation_euler = rot
        trunk.keyframe_insert(data_path="location", frame=frame)
        trunk.keyframe_insert(data_path="rotation_euler", frame=frame)
    animate_wounded_body(pinned, 214, 234, dx=0.65, dy=-0.15)

    # A natural tree arch is a physical frame the camera threads after the rescue beat.
    beam_between("FOREST_ARCH_LEFT_TRUNK", (-91, -8, 2.8), (-91, -8, 0.0), 0.62, MATS["trunk"], action_coll)
    beam_between("FOREST_ARCH_RIGHT_TRUNK", (-91, 8, 2.8), (-91, 8, 0.0), 0.62, MATS["trunk"], action_coll)
    beam_between("FOREST_ARCH_CROSS_TRUNK", (-91, -8, 5.5), (-91, 8, 5.5), 0.58, MATS["trunk"], action_coll)
    beam_between("FOREST_ARCH_BRANCH_DIAGONAL", (-91, 5, 5.2), (-96, 10, 3.9), 0.24, MATS["branch"], action_coll)

    # WUTONGGOU: woman already at the doorway carrying a wounded man; old wooden-shaft explosive.
    woman = make_actor("WUTONGGOU_WOMAN_CARRYING_WOUNDED_MAN", (35.0, -7.0, 0.0),
                       yaw=0.0, faction="cn", rifle=False)
    animate_actor(woman, [(340, (34.2, -7.0, 0.0), 0.0),
                          (354, (35.0, -7.0, 0.0), 0.0),
                          (376, (35.0, -7.0, 0.0), 0.0)], run=False)

    wounded = make_actor("WUTONGGOU_WOUNDED_MAN_ON_BACK", (35.0, -7.0, 0.0),
                         yaw=0.0, faction="cn", rifle=False)
    wounded["root"].parent = woman["root"]
    wounded["root"].location = (-0.22, 0.0, 1.28)
    wounded["root"].rotation_euler = (0.0, math.radians(82.0), math.pi)

    shaft = cylinder("WUTONGGOU_OLD_WOODEN_SHAFT_GRENADE", (35.78, -7.18, 1.35),
                     0.075, 1.05, MATS["trunk"], props, vertices=10,
                     rot=(0.18, 0.18, 0.0))
    cap = cylinder("WUTONGGOU_WOODEN_GRENADE_METAL_CAP", (35.78, -7.18, 1.88),
                   0.095, 0.16, MATS["weapon"], props, vertices=10)
    bpy.ops.mesh.primitive_torus_add(major_segments=16, minor_segments=8,
                                     location=(35.90, -7.18, 1.90),
                                     major_radius=0.14, minor_radius=0.025)
    pin_ring = bpy.context.object
    pin_ring.name = "WUTONGGOU_WOODEN_GRENADE_PULL_RING"
    move_obj(pin_ring, props)
    for frame, loc, rot in [
        (350, (35.90, -7.18, 1.90), (0.0, 0.0, 0.0)),
        (366, (35.90, -7.18, 1.90), (0.0, 0.0, 0.0)),
        (372, (36.16, -7.18, 1.88), (0.0, 0.0, 0.55)),
        (376, (36.36, -7.18, 1.84), (0.0, 0.0, 0.85)),
    ]:
        pin_ring.location = loc
        pin_ring.rotation_euler = rot
        pin_ring.keyframe_insert(data_path="location", frame=frame)
        pin_ring.keyframe_insert(data_path="rotation_euler", frame=frame)
    for frame, angle in [(350, -0.18), (362, -0.55), (370, -1.08), (376, -0.42)]:
        woman["right_arm"].rotation_euler.y = angle
        woman["right_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)

    # Additional Japanese perimeter positions create a genuine encirclement, not a single line.
    for i, (loc, yaw) in enumerate([
        ((43, -18, 0), math.pi), ((47, -14, 0), math.pi), ((52, -10, 0), math.pi),
        ((56, -3, 0), math.pi), ((55, 7, 0), math.pi), ((49, 14, 0), math.pi),
        ((42, 11, 0), math.pi), ((45, 3, 0), math.pi),
    ]):
        jp = make_actor("JP_WUTONGGOU_PERIMETER_%02d" % i, loc, yaw=yaw,
                        faction="jp", rifle=True)
        for frame, arm_angle in [(350, -0.60), (364, -0.74), (376, -0.80)]:
            jp["left_arm"].rotation_euler.y = arm_angle
            jp["right_arm"].rotation_euler.y = arm_angle
            jp["left_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)
            jp["right_arm"].keyframe_insert(data_path="rotation_euler", frame=frame)

    # A few house fragments are kicked outward by the blast and settle while the camera passes through.
    for i, spec in enumerate([
        ((37, -12, 2.2), (31, -18, 4.2)), ((40, -2, 2.8), (48, 4, 5.0)),
        ((35, -5, 3.8), (27, -2, 6.2)), ((43, -8, 2.0), (52, -12, 3.5)),
        ((39, -10, 4.5), (44, -18, 7.0)),
    ]):
        a, b = spec
        debris = ico("WUTONGGOU_BLAST_FLYING_DEBRIS_%02d" % i, a,
                     (0.65, 0.42, 0.28), MATS["roof"], action_coll, sub=1)
        debris.keyframe_insert(data_path="location", frame=376)
        debris.location = b
        debris.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        debris.keyframe_insert(data_path="location", frame=388)
        debris.keyframe_insert(data_path="rotation_euler", frame=388)
        debris.location = (b[0] + 1.5, b[1] + 1.0, 0.25)
        debris.keyframe_insert(data_path="location", frame=408)

    # RIVER: expand the crossing from a handful of figures to a populated, irregular field.
    for i in range(60):
        x = random.uniform(92, 184)
        y = random.uniform(-31, 31)
        start = (x, y, -0.62 + random.uniform(-0.10, 0.06))
        end = (x + random.uniform(5.0, 13.0),
               y + random.uniform(-5.0, 5.0), start[2])
        actor = make_actor("CN_RIVER_CROWD_WADER_%02d" % i, start,
                           yaw=random.uniform(-0.16, 0.16), faction="cn",
                           rifle=(i % 5 == 0))
        animate_wading_actor(actor, [
            (418 + random.randint(0, 16), start, 0.0),
            (468 + random.randint(-5, 8), ((start[0] + end[0]) * 0.5,
                                         (start[1] + end[1]) * 0.5, start[2]), 0.0),
            (522 + random.randint(-8, 10), end, 0.0),
        ])

    # Floating bodies lie flat at the surface, distributed across the full river width.
    float_specs = [
        (94, -28, "supine", "cn"), (101, 19, "side", "jp"),
        (111, -12, "prone", "cn"), (119, 29, "supine", "cn"),
        (128, -31, "side", "jp"), (137, 14, "supine", "cn"),
        (146, -20, "prone", "cn"), (153, 30, "side", "jp"),
        (164, -8, "supine", "cn"), (172, 22, "prone", "cn"),
        (181, -27, "side", "jp"), (188, 9, "supine", "cn"),
    ]
    for i, (x, y, pose, faction) in enumerate(float_specs):
        body = make_casualty("RIVER_SURFACE_FLOAT_V12_%02d" % i,
                             (x, y, 0.04), yaw=random.uniform(-1.2, 1.2),
                             faction=faction, pose=pose)
        animate_wounded_body(body, 420 + i * 4, 520 + i * 2,
                             dx=random.uniform(0.12, 0.42), dy=random.uniform(-0.18, 0.18))

    # Additional river debris floats slowly with the current.
    for i, (x, y) in enumerate([(103, 25), (132, -26), (159, 4), (181, -14)]):
        log_obj = beam_between("RIVER_FLOATING_TIMBER_%02d" % i,
                               (x, y, 0.16), (x + 2.4, y + 0.5, 0.16),
                               0.16, MATS["trunk"], action_coll)
        log_obj.keyframe_insert(data_path="location", frame=420 + i * 5)
        log_obj.location.x += 1.2
        log_obj.location.y += 0.8
        log_obj.keyframe_insert(data_path="location", frame=520 + i * 4)

    # Natural rock arch at the final valley entrance: the camera flies through its open center.
    pass_coll = get_collection("BFP_V20_06_WEST_PASS")
    beam_between("WEST_VALLEY_ROCK_ARCH_CROWN", (330, -42, 55), (330, 42, 55),
                 5.5, MATS["rock"], pass_coll)
    beam_between("WEST_VALLEY_ROCK_ARCH_LEFT_SUPPORT", (330, -42, 55), (330, -42, 5),
                 5.0, MATS["rock"], pass_coll)
    beam_between("WEST_VALLEY_ROCK_ARCH_RIGHT_SUPPORT", (330, 42, 55), (330, 42, 5),
                 5.0, MATS["rock"], pass_coll)

    log("Storyboard details added: rescue, doorway pair, wooden-shaft grenade, encirclement, broad river crowd, surface casualties and natural frame gates.")


def add_terrain_reference_board():
    """Pack the supplied terrain image into the .blend as a non-rendering reference board."""
    ref_coll = get_collection("BFP_V20_20_TERRAIN_REFERENCE")
    base_dir = get_script_directory()
    candidates = [
        os.path.join(base_dir, "terrain_reference.png"),
        os.path.join(base_dir, "image(20261031-062739).png"),
        os.path.join(os.getcwd(), "terrain_reference.png"),
    ]
    img_path = next((p for p in candidates if os.path.exists(p)), None)
    if not img_path:
        STATUS["TERRAIN_REFERENCE_IMAGE"] = "SKIP - terrain_reference.png not found beside script"
        return
    img = bpy.data.images.load(img_path, check_existing=True)
    try:
        img.pack()
    except Exception:
        pass
    mat_ref = bpy.data.materials.new("BFP_V20_TERRAIN_REFERENCE_IMAGE_MATERIAL")
    mat_ref.use_nodes = True
    nodes = mat_ref.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat_ref.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    plane_mesh = bpy.data.meshes.new("BFP_V20_TERRAIN_REFERENCE_PLANE_MESH")
    plane_mesh.from_pydata([(-80, -45, 0), (80, -45, 0), (80, 45, 0), (-80, 45, 0)], [], [(0, 1, 2, 3)])
    plane_mesh.materials.append(mat_ref)
    plane = bpy.data.objects.new("TERRAIN_REFERENCE_IMAGE_BOARD_NON_RENDER", plane_mesh)
    ref_coll.objects.link(plane)
    plane.location = (950, 0, 20)
    plane.hide_render = True
    STATUS["TERRAIN_REFERENCE_IMAGE"] = "PACKED - " + os.path.basename(img_path)

def build_battlefield_fx():
    fx = get_collection("BFP_V20_18_BATTLE_FX")

    # Animated blast flash: a timing/volume proxy, not a finished explosion simulation.
    flash = ico("WUTONGGOU_BLAST_FLASH_PROXY", (38, -7, 4.0),
                (0.1, 0.1, 0.1), MATS["blast"], fx, sub=1)
    for frame, scale in [
        (376, (0.001, 0.001, 0.001)),
        (378, (2.8, 2.8, 2.8)),
        (380, (5.0, 4.0, 3.4)),
        (384, (1.0, 1.0, 1.0)),
        (389, (0.001, 0.001, 0.001)),
    ]:
        flash.scale = scale
        flash.keyframe_insert(data_path="scale", frame=frame)

    # Expand existing smoke placeholders in time with the blast.
    smoke_coll = get_collection("BFP_V20_12_SMOKE_PLACEHOLDERS")
    for obj in list(smoke_coll.objects):
        base = obj.scale.copy()
        for frame, factor in [
            (375, 0.001),
            (378, 0.18),
            (386, 0.72),
            (398, 1.0),
            (410, 1.28),
        ]:
            obj.scale = (base.x * factor, base.y * factor, base.z * factor)
            obj.keyframe_insert(data_path="scale", frame=frame)

    make_small_blast("AIR_BOMB_MAIN_IMPACT", (-181, -8, 0.8), 90, radius=4.8)
    make_small_blast("AIR_BOMB_SECONDARY_IMPACT_A", (-191, -29, 0.8), 98, radius=3.2)
    make_small_blast("AIR_BOMB_SECONDARY_IMPACT_B", (-169, 26, 0.8), 104, radius=3.0)
    make_small_blast("AIR_BOMB_SECONDARY_IMPACT_C", (-151, 38, 0.8), 110, radius=2.8)
    make_small_blast("FOREST_BLAST_NEAR_JP_LINE", (-166, -8, 1.8), 116, radius=1.7)
    make_small_blast("FOREST_BLAST_ROCK_COVER", (-133, -7, 1.8), 176, radius=2.1)
    make_small_blast("FOREST_BLAST_REAR_SLOPE", (-105, 11, 2.2), 226, radius=1.8)
    make_small_blast("RAVINE_BLAST_FAR_WALL", (-34, 10, 2.0), 302, radius=1.6)
    make_small_blast("WUTONGGOU_HOUSE_BLAST_EVENT", (38, -7, 3.0), 378, radius=3.6)
    make_small_blast("VILLAGE_NEAR_GROUND_IMPACT", (28, -1, 1.2), 364, radius=1.9)
    make_small_blast("RIVERBANK_POST_EXIT_BLAST", (197, 6, 1.0), 536, radius=1.5)
    make_water_splash("RIVER_CROSSER_SPLASH_NEAR", (130, 2, 0.02), 490)
    make_water_splash("RIVER_CROSSER_SPLASH_FAR", (143, -1.5, 0.02), 502)

    make_falling_branch("FALLING_BRANCH_A", (-168, -14, 5.0), 118, 132, fall_y=1.4, fall_z=1.2)
    make_falling_branch("FALLING_BRANCH_B", (-145, 7, 5.4), 154, 170, fall_y=-1.2, fall_z=1.1)
    make_falling_branch("FALLING_BRANCH_C", (-126, -3, 4.8), 180, 198, fall_y=1.5, fall_z=1.0)
    make_falling_branch("FALLING_BRANCH_D", (-103, 15, 5.2), 220, 238, fall_y=-1.3, fall_z=1.0)
    make_falling_branch("FALLING_BRANCH_E", (-82, -10, 4.7), 246, 262, fall_y=1.2, fall_z=1.0)

    # Bullet streaks cross the frame at different depths; they are brief, simple cues.
    make_bullet_tracer("TRACER_FOREST_JP_A", (-156, -2, 1.5), (-140, -7, 1.0), 118, 124)
    make_bullet_tracer("TRACER_FOREST_CN_A", (-137, -8, 1.0), (-150, -3, 1.2), 162, 168)
    make_bullet_tracer("TRACER_FOREST_CN_B", (-130, -12, 1.0), (-120, -6, 1.2), 171, 177)
    make_bullet_tracer("TRACER_VILLAGE_A", (49, 5, 2.0), (29, -5, 1.7), 360, 367)
    make_bullet_tracer("TRACER_VILLAGE_B", (17, 7, 1.4), (47, -5, 1.9), 372, 380)
    make_bullet_tracer("TRACER_RIVER_A", (103, 13, -1.8), (116, -7, -2.0), 472, 479)
    make_bullet_tracer("TRACER_RIVER_B", (148, -12, -1.6), (162, 7, -1.8), 498, 505)
    make_bullet_tracer("TRACER_WEST_PASS_A", (265, -17, 1.4), (289, 13, 1.8), 706, 713)
    make_bullet_tracer("TRACER_WEST_PASS_B", (307, 15, 1.6), (326, -12, 2.0), 754, 761)

    # Simple water impact puffs: low-poly spheres expand and fade in scale.
    for i, loc in enumerate(((100, 2, -1.6), (119, -2, -1.5), (139, 5, -1.4), (158, -4, -1.5), (176, 4, -1.4))):
        splash = ico("WATER_BULLET_IMPACT_%02d" % i, loc, (0.08, 0.08, 0.08),
                     MATS["rock_light"], fx, sub=1)
        frame = 438 + i * 16
        for f, scale in [
            (frame, (0.02, 0.02, 0.02)),
            (frame + 2, (0.85, 0.45, 0.35)),
            (frame + 7, (0.15, 0.15, 0.15)),
        ]:
            splash.scale = scale
            splash.keyframe_insert(data_path="scale", frame=f)


# ============================================================
# CAMERA WAYPOINTS
# 30 seconds / 900 frames. Main direction is +X.
# Performance beats receive short camera holds; transition passages remain fast.
# Small Y offsets create purposeful weaving; camera roll is never applied.
# ============================================================

CAMERA_KEYS = [
    # HIGH AIR / PIGEON / FOUR-BOMBER MEETING
    (1,   (-285, -34, 150), (-240, -20, 118), "HIGH AERIAL ESTABLISH / TERRAIN SCALE", -4),
    (12,  (-265, -26, 140), (-232, -16, 118), "DESCEND BEHIND PIGEON", -10),
    (22,  (-245, -18, 126), (-221, -12, 114), "PIGEON LEFT FOREGROUND / REAR POV", -18),
    (32,  (-226, -12, 118), (-196, -4, 110), "FOUR AIRCRAFT APPROACH", -8),
    (42,  (-207, -8, 112), (-174, 2, 108), "AIRCRAFT FORMATION CLOSES", 12),
    (52,  (-190, -2, 105), (-158, 8, 100), "PASS BETWEEN AIRCRAFT / BOMBS RELEASE", 22),
    (60,  (-182, 8, 96), (-172, 0, 78), "UNDERWING CLOSE PASS / BOMB FREEFALL", 28),
    (70,  (-181, 14, 75), (-178, 3, 40), "CAMERA PITCHES DOWN / PLANES LEAVE FRAME", 36),
    (80,  (-183, 8, 38), (-180, -4, 15), "STEEP DIVE TOWARD IMPACT ZONE", 22),
    (90,  (-180, -4, 10), (-174, -8, 1), "MAIN BOMB IMPACT / ENTER SMOKE", 0),
    (98,  (-176, -8, 2), (-170, -6, 1), "LOW ENTRY INTO FOREST", -5),

    # FOREST: LEFT HOOK -> RIGHT CUT -> ARCH THREAD -> LOW DODGE
    (108, (-166, -8, 1.60), (-160, -3, 1.05), "JAPANESE CLOSE SHOOTER", -10),
    (116, (-160, -18, 1.45), (-153, -24, 1.00), "HARD LEFT AROUND TREE TRUNK", -28),
    (124, (-151, -28, 1.40), (-145, -20, 1.00), "CUT BACK RIGHT THROUGH TREE GAP", -38),
    (132, (-143, -18, 1.25), (-136, -8, 0.95), "PASS MUZZLE / FIRE LINE", -22),
    (140, (-137, 0, 1.20), (-131, 10, 0.90), "SLIDE TOWARD CHINESE COVER", 22),
    (148, (-132, 18, 1.20), (-126, 24, 0.90), "RIGHT BANK / RETURN FIRE", 38),
    (156, (-126, 26, 1.15), (-120, 28, 0.90), "CUT THROUGH ROCK-COVER LANE", 32),
    (164, (-120, 18, 1.20), (-115, 8, 0.90), "SWEEP LEFT PAST FIRING POSITION", 18),
    (172, (-116, 0, 1.20), (-110, -10, 0.90), "LOW S-CURVE INTO TREE DENSITY", -26),
    (180, (-111, -18, 1.10), (-106, -25, 0.90), "PASS WOUNDED SOLDIER / ROCK EDGE", -36),
    (188, (-106, -26, 1.05), (-102, -12, 0.90), "ROLL INTO RESCUE BEAT", -45),
    (196, (-102, -8, 1.25), (-108, 12, 1.10), "LOOK ACROSS TO TREE RESCUE", 12),
    (204, (-98, 8, 1.35), (-93, 4, 1.00), "THREAD UNDER FOREST TREE ARCH", 30),
    (212, (-94, 2, 1.35), (-90, -1, 1.00), "BANK THROUGH ARCH EXIT", 22),
    (220, (-90, -4, 1.45), (-85, -10, 1.00), "DODGE LOW BRANCH / TURN OUT", -24),
    (232, (-81, 5, 1.40), (-75, 12, 0.90), "FOREST EXIT / RAVINE REVEAL", 0),

    # LI XINGOU: DESCEND INTO ROCK CORRIDOR / S-TURN / TURN TOWARD HOUSE
    (244, (-72, 10, 1.20), (-65, 18, 0.60), "DROP INTO RAVINE", 26),
    (254, (-60, 24, 1.10), (-53, 16, 0.60), "PASS BETWEEN ROCK WALLS", 42),
    (264, (-50, 12, 0.95), (-44, 0, 0.50), "SWEEP LEFT AROUND BOULDER", 24),
    (274, (-42, -10, 0.90), (-35, -18, 0.50), "REVERSE TURN ALONG GULLY FLOOR", -34),
    (286, (-31, -22, 0.90), (-23, -18, 0.50), "LOW PASS / SCATTERED CASUALTIES", -40),
    (298, (-21, -12, 1.10), (-14, -2, 0.50), "ROTATE RIGHT THROUGH ROCK GAP", -18),
    (310, (-12, 12, 1.30), (-4, 18, 0.70), "CLIMB SLIGHTLY / LEAVE GULLY", 24),
    (322, (0, 20, 1.40), (12, 12, 1.00), "LONG DIAGONAL TURN TO VILLAGE", 28),
    (332, (17, 14, 1.50), (29, 5, 1.00), "SWEEP BEHIND JAPANESE LINE", 34),

    # WUTONGGOU: FOLLOW JAPANESE FROM BEHIND / HOUSE DOORWAY FRAME / BLAST DODGE
    (340, (40, 14, 1.60), (50, 2, 1.20), "BEHIND JAPANESE PERIMETER", 22),
    (350, (55, 4, 1.45), (45, -4, 1.10), "FOLLOW APPROACH / REVEAL DOORWAY", -12),
    (360, (49, -4, 1.40), (39, -7, 1.20), "SLIDE TO REAR-OBLIQUE HOUSE AXIS", 8),
    (370, (43, -8, 1.45), (36, -7, 1.40), "WOMAN AND WOUNDED MAN AT DOOR", 18),
    (378, (40, -14, 2.00), (38, -7, 3.00), "WOODEN-SHAFT GRENADE / HOUSE BLAST", 38),
    (388, (42, -22, 3.20), (50, -14, 4.50), "DODGE BLAST / PASS THROUGH DEBRIS FRAME", 48),
    (398, (53, -22, 2.00), (64, -13, 0.80), "EXIT SMOKE WITH BANKED TURN", 26),
    (410, (68, -11, 1.30), (80, -4, 0.20), "RIVER VALLEY OPENS AHEAD", 0),

    # BROAD RIVER: DIAGONAL ENTRY / BRAKE / RECOIL / SIDE DODGE / WEAVE THROUGH PEOPLE
    (420, (78, -10, 0.20), (90, -15, -1.50), "DIVE TOWARD BROAD RIVER", -22),
    (430, (92, -18, -2.00), (100, -25, -1.00), "UNDERWATER ENTRY BETWEEN WADERS", -32),
    (440, (106, -28, -2.10), (115, -30, -0.90), "SWEEP UNDER CROWD / FLOATING BODY", -38),
    (450, (120, -22, -2.20), (129, -10, -0.90), "ROLL THROUGH UNDERWATER GAP", 26),
    (458, (126, -8, -2.20), (133, 5, -1.00), "SUDDEN BRAKE / WATER BULLET IMPACT", 40),
    (466, (124, 12, -2.10), (131, 22, -1.00), "BACKWARD RECOIL / HARD SIDE DODGE", 48),
    (476, (136, 24, -1.80), (145, 26, -0.60), "CUT BETWEEN FLOATING CASUALTIES", 26),
    (488, (151, 18, -1.20), (160, 8, -0.10), "FORWARD ACCELERATION / RISE", -18),
    (500, (167, 2, -0.20), (176, -8, 0.70), "BREAK WATER SURFACE", -22),
    (512, (184, -10, 0.80), (194, -7, 1.20), "OUT OF RIVER / BANK TOWARD HANDOFF", 0),

    # HANDOFF / OLD MENG: low approach, one 180-degree orbit, front hold
    (524, (196, -12, 0.35), (201, -4, 1.10), "BOX HANDOFF ENTERS FRAME", -10),
    (536, (203, -5, 0.30), (203, -4, 1.10), "PASS BETWEEN SENDER AND RECEIVER", 0),
    (548, (213, 6, 0.35), (218, 0, 1.00), "FOLLOW RECEIVER / LOW GROUND SWEEP", 12),
    (564, (228, 12, 0.40), (239, 0, 1.30), "TURN INTO OLD MENG OPENING", 16),
    (582, (240, 0, 0.30), (250, 0, 2.00), "OLD MENG APPEARS AHEAD", 0),
    (594, (246.5, 0.0, 0.24), (250, 0, 2.12), "ORBIT START / REAR LOW ANGLE", 0),
    (608, (247.5, 2.5, 0.24), (250, 0, 2.14), "180 ORBIT / LEFT REAR QUARTER", 4),
    (622, (250.0, 3.5, 0.25), (250, 0, 2.16), "ORBIT SIDE PROFILE", 6),
    (636, (252.5, 2.5, 0.25), (250, 0, 2.18), "ORBIT FRONT THREE-QUARTER", 4),
    (650, (253.5, 0.0, 0.26), (250, 0, 2.20), "FRONT LOW HERO / FULL FACE", 0),
    (664, (253.5, 0.0, 0.28), (250, 0, 2.20), "HERO HOLD / BREATH AND LOOK", 0),

    # PULL BACK / THROUGH HUMAN FRAME / VALLEY ARCH / HIGH AERIAL REVEAL
    (680, (262, -1, 0.90), (254, 0, 1.80), "DIRECT PULL BACK FROM OLD MENG", -4),
    (700, (278, -12, 1.80), (270, -1, 1.20), "WEAVE THROUGH FIRST CHARGE LANE", -24),
    (720, (296, -24, 3.20), (286, -2, 1.20), "BANK LEFT THROUGH CROWD GAP", -34),
    (742, (315, -18, 6.00), (304, -1, 1.50), "PASS UNDER NATURAL VALLEY FRAME", 28),
    (762, (338, 8, 12.00), (326, 0, 1.50), "CLEAR ROCK ARCH / CLIMB", -18),
    (790, (360, 22, 24.00), (340, 0, 4.00), "SWEEP RIGHT ABOVE VALLEY", -30),
    (830, (400, 0, 55.00), (300, 0, 0.00), "HIGH AERIAL LIFT", -8),
    (870, (450, 0, 100.00), (220, 0, 0.00), "WIDE REVEAL OF COMPLETE BATTLEFIELD", 0),
    (900, (510, 0, 145.00), (140, 0, 0.00), "FINAL HIGH AERIAL / TERRAIN SCALE", 0),
]

CAMERA_FOCAL_KEYS = [
    (1, 24), (12, 26), (22, 30), (32, 34), (42, 38), (52, 40), (60, 42), (70, 36), (80, 28), (90, 24), (98, 26),
    (108, 38), (116, 42), (124, 42), (132, 38), (140, 40), (148, 42), (156, 40), (164, 38), (172, 36),
    (180, 34), (188, 34), (196, 36), (204, 38), (212, 38), (220, 34), (232, 30),
    (244, 30), (254, 34), (264, 38), (274, 36), (286, 36), (298, 34), (310, 30), (322, 30), (332, 32),
    (340, 34), (350, 38), (360, 42), (370, 46), (378, 40), (388, 32), (398, 30), (410, 28),
    (420, 30), (430, 38), (440, 42), (450, 44), (458, 44), (466, 40), (476, 42), (488, 36), (500, 30), (512, 28),
    (524, 34), (536, 44), (548, 38), (564, 28), (582, 30), (594, 48), (608, 58), (622, 62), (636, 65),
    (650, 68), (664, 65), (680, 40), (700, 32), (720, 28), (742, 26), (762, 24), (790, 24), (830, 24), (870, 24), (900, 24),
]


def build_camera():
    camera_coll = get_collection("BFP_V20_09_CAMERA")
    cam_data = bpy.data.cameras.new("BFP_V20_ACTIVE_CAMERA_DATA")
    cam = bpy.data.objects.new("BFP_V20_ACTIVE_CAMERA", cam_data)
    camera_coll.objects.link(cam)
    cam.parent = None
    cam.rotation_mode = 'QUATERNION'
    cam_data.lens = 24
    cam_data.clip_start = 0.05
    cam_data.clip_end = 2600
    cam_data.display_size = 5.0
    cam.show_in_front = True
    cam.show_name = True
    cam["CAMERA_BANKING_ENABLED"] = True
    cam["CAMERA_CHOREOGRAPHY_VERSION"] = "V1.2"

    focus = empty(
        "BFP_V20_CAMERA_LOOK_TARGET",
        (0, 0, 0),
        camera_coll,
        display='SPHERE',
        size=0.8
    )

    previous_camera_q = None
    for frame, position, target, note, bank_deg in CAMERA_KEYS:
        cam.location = position
        cam.keyframe_insert(data_path="location", frame=frame)

        direction = Vector(target) - Vector(position)
        if direction.length < 0.001:
            direction = Vector((1, 0, 0))

        # Explicit bank is part of the camera choreography: it peaks at turns and frame passages,
        # then returns toward level at readable story beats.
        base_q = direction.to_track_quat('-Z', 'Y')
        local_bank = Quaternion((0.0, 0.0, 1.0), math.radians(bank_deg))
        camera_q = base_q @ local_bank
        if previous_camera_q is not None and camera_q.dot(previous_camera_q) < 0.0:
            camera_q = Quaternion((-camera_q.w, -camera_q.x, -camera_q.y, -camera_q.z))
        cam.rotation_quaternion = camera_q
        cam.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        previous_camera_q = camera_q.copy()

        focus.location = target
        focus.keyframe_insert(data_path="location", frame=frame)

    for frame, lens_mm in CAMERA_FOCAL_KEYS:
        cam_data.lens = lens_mm
        cam_data.keyframe_insert(data_path="lens", frame=frame)

    try:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_object = focus
        cam_data.dof.aperture_fstop = 5.6
        cam_data.dof.aperture_blades = 6
    except Exception:
        pass

    # Smooth camera movement with clamped handles.
    # Path stays continuous; no deliberate stop on each hit reaction.
    for obj in (cam, focus, cam_data):
        if obj.animation_data and obj.animation_data.action:
            try:
                for fc in obj.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = 'AUTO_CLAMPED'
                        kp.handle_right_type = 'AUTO_CLAMPED'
            except Exception:
                pass

    bpy.context.scene.camera = cam
    bpy.context.view_layer.update()
    STATUS["CAMERA_BANKING"] = "PASS - explicit bank keys: %d" % sum(1 for k in CAMERA_KEYS if abs(k[4]) >= 18)
    STATUS["CAMERA_CHOREOGRAPHY"] = "PASS - %d non-linear waypoints across 30s" % len(CAMERA_KEYS)
    return cam, focus


# ============================================================
# CAMERA PATH DEBUG CURVE
# ============================================================

def build_camera_path_debug():
    coll = get_collection("BFP_V20_10_PATH_DEBUG")
    curve = bpy.data.curves.new("BFP_V20_CAMERA_PATH_CURVE_DATA", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 2
    curve.bevel_depth = 0.16
    curve.bevel_resolution = 2

    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(CAMERA_KEYS) - 1)

    for i, item in enumerate(CAMERA_KEYS):
        x, y, z = item[1]
        bp = spline.bezier_points[i]
        bp.co = (x, y, z)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    path_obj = bpy.data.objects.new("BFP_V20_CAMERA_PATH_VISIBLE", curve)
    coll.objects.link(path_obj)
    curve.materials.append(MATS["path"])
    path_obj.hide_render = True
    path_obj.show_in_front = True
    path_obj.display_type = 'WIRE'

    for idx, item in enumerate(CAMERA_KEYS):
        frame, position, target, note, bank_deg = item
        if abs(bank_deg) >= 18:
            marker = empty("CAMERA_BANK_MARKER_%02d_F%03d" % (idx, frame), position, coll,
                           display='ARROWS', size=1.4)
            marker["FRAME"] = frame
            marker["BANK_DEGREES"] = bank_deg
            marker["CHOREOGRAPHY_NOTE"] = note


# ============================================================
# LIGHTS / SCENE / VIEWPORT
# ============================================================

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def configure_lighting():
    coll = get_collection("BFP_V20_11_LIGHTS")

    bpy.ops.object.light_add(type='SUN', location=(180, -120, 110))
    sun = bpy.context.object
    sun.name = "BFP_V20_DAWN_SUN"
    sun.data.energy = 1.8
    point_at(sun, (100, 0, 0))
    move_obj(sun, coll)

    bpy.ops.object.light_add(type='AREA', location=(250, -30, 35))
    fill = bpy.context.object
    fill.name = "BFP_V20_WEST_PASS_FILL"
    fill.data.energy = 2600
    fill.data.shape = 'DISK'
    fill.data.size = 45
    point_at(fill, (275, 0, 5))
    move_obj(fill, coll)

    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("BFP_V20_WORLD")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.20, 0.24, 0.28, 1)
        bg.inputs[1].default_value = 0.65


def force_camera_view():
    scene = bpy.context.scene
    cam = bpy.data.objects.get("BFP_V20_ACTIVE_CAMERA")
    if cam is None:
        raise RuntimeError("BFP_V20_ACTIVE_CAMERA not found")
    scene.camera = cam
    bpy.context.view_layer.update()

    # Set all existing 3D View areas to camera perspective.
    # Use the view_camera operator with an explicit area/region override.
    changed = 0
    wm = bpy.context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            try:
                space.region_3d.view_perspective = 'CAMERA'
                space.region_3d.view_camera_zoom = 20
            except Exception:
                pass

            window_region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if window_region:
                try:
                    with bpy.context.temp_override(window=window, area=area, region=window_region):
                        bpy.ops.view3d.view_camera()
                    changed += 1
                except Exception as exc:
                    log("view_camera operator warning: " + repr(exc))

    log("Camera viewport areas switched: %d" % changed)


def configure_scene():
    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100

    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        pass
    try:
        scene.view_settings.view_transform = 'AgX'
    except Exception:
        pass

    for marker in list(scene.timeline_markers):
        scene.timeline_markers.remove(marker)

    marker_list = [
        (1, "01 高空大地貌建立"), (22, "02 鸽子左前景后方跟随"),
        (32, "03 四机迎面接近"), (52, "04 穿越编队 / 航空炸弹释放"),
        (70, "05 机腹近景后俯冲"), (90, "06 主炸弹落地 / 穿烟入林"),
        (108, "07 森林日军近景射击"), (140, "08 左右折返进入中方掩体"),
        (188, "09 森林救援与倒木动作"), (204, "10 穿越树木框架"),
        (244, "11 李行沟下切"), (274, "12 沟底反向转弯"),
        (322, "13 转向梧桐沟"), (350, "14 日军背后跟拍逼近破屋"),
        (370, "15 门口背人 / 木杆光荣弹拉环"), (378, "16 破屋爆炸"),
        (388, "17 倾斜穿越爆炸碎片框架"), (420, "18 斜向入河"),
        (458, "19 水下急停"), (466, "20 后退惯性 / 侧向闪避"),
        (500, "21 出水"), (536, "22 箱子交接"),
        (582, "23 低机位接近老孟"), (650, "24 老孟正面英雄仰拍"),
        (680, "25 直接后拉穿过冲锋队伍"), (742, "26 穿越山谷天然岩石框架"),
        (830, "27 高空升起"), (900, "28 完整战场高空全景"),
    ]
    for frame, name in marker_list:
        scene.timeline_markers.new(name, frame=frame)

    performance_markers = [
        (22, "表演峰值｜鸽子近景滑翔"), (52, "动作峰值｜四机穿越与炸弹释放"),
        (90, "动作峰值｜航空炸弹落地"), (118, "表演峰值｜日军近距离射击"),
        (148, "表演峰值｜中方掩体反击"), (188, "表演峰值｜倒木下救援"),
        (204, "空间动作｜穿越森林树木框架"), (254, "空间动作｜岩壁窄口转弯"),
        (370, "表演峰值｜门口背人拉木杆光荣弹"), (378, "动作峰值｜房屋爆炸冲击"),
        (466, "动作峰值｜水下后退与侧闪"), (488, "动作峰值｜穿越浮尸和渡河人群"),
        (536, "表演峰值｜箱子交接"), (650, "表演峰值｜老孟低角度英雄呈现"),
        (742, "空间动作｜穿越山谷岩石框架"), (900, "高空全景｜完整战场"),
    ]
    for frame, name in performance_markers:
        scene.timeline_markers.new(name, frame=frame)

    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()


def write_build_report():
    text_name = "BFP_V20_BUILD_REPORT"
    txt = bpy.data.texts.get(text_name)
    if txt is None:
        txt = bpy.data.texts.new(text_name)
    else:
        txt.clear()

    lines = [
        "Battlefield One-Take Previs V1.2",
        "Blender: " + bpy.app.version_string,
        "Scope: 30-second battlefield previs with continuous human presence, close-up staged action, layered foreground/midground/background blocking and editable camera",
        "Actors: near/mid/far human presence in every major beat; explicit firing, hit recoil, fall, duck/recover, water wading, assisted crossing, hand-to-hand box transfer and Old Meng hero gesture.",
        "Props: four approaching Japanese bombers in a loose two-per-side formation, four staged non-powered aviation bombs, pigeon, rifles, wooden-shaft grenade, handoff box and Old Meng charge markers.",
        "Camera: 3D non-linear choreography with left/right S-curves, hard turns, vertical dives, underwater recoil, one Old Meng 180-degree orbit, deliberate banking/roll and multiple physical frame passages.",
        "Camera is not locked: actor positions, event timing, camera path, aim and lens remain editable after playback.",
        "Forest: dense irregular woodland, close S-curve route, tree-frame passage, battle casualties, pinned soldier and animated rescue/lift beneath a fallen trunk.",
        "Forest path: lateral bends around obstacles plus vertical undulation.",
        "Tactical layout: neutral cover slots, advance lanes and fire-direction anchors.",
        "Water: broad 72m crossing, irregular wading crowd across the full river width, flat surface-floating casualties, submerged bodies, bullet impacts, hit/fall beats and assisted crossing.",
        "Ground-level foreground: fine grass and low stones near the lens.",
        "Wutonggou: Japanese perimeter encirclement -> woman carrying wounded man at doorway -> old wooden-shaft explosive ring pull -> house blast -> debris-frame passage -> river approach.",
        "Underwater: sudden stop, backward recoil, lateral dodge, forward acceleration and exit.",
        "Ground-level wide-angle section: near-lens grass tufts and low foreground stones.",
        "Road after water: wide and open; deceleration before Old Meng.",
        "Old Meng: low-angle full-to-medium-to-close push, low-angle arc from rear toward front, arm-shading gesture, then front heroic close-up and hold.",
        "Final: direct pull-back through charging crowd, banked pass beneath natural rock arch, rising valley reveal and expanded high aerial view.",
        "Camera banking: explicitly keyed at turns, dives, dodges and frame passages; level is restored at hero beats.",
        "Camera focus: story-event targets; focal lengths animate from 24mm aerial wide to a 68mm Old Meng low-angle close-up.",
        "Movement rhythm: fast passages bridge the staged performance peaks; camera holds are added at hit reactions, blast, water fall and box transfer.",
        "Multiple segmented white-block people, layered battlefield blocking and simplified props; no facial detail, clothing texture or rig.",
        "Blast flash, smoke expansion, falling branches, bullet tracers, blood-water tint and water impact puffs are simplified timing cues, not physical simulations.",
        "Timeline: 1-900 @ 30 FPS; all actors, props, aircraft, bombs and environment events share one global timebase.",
        "",
        "Performance peak map:",
        "Frame 1-110: four bombers approach; aviation bombs remain attached, release in staggered phases, descend through early/mid/terminal stages and impact at separate points.",
        "Frame 118-145: Japanese close shooter fires; nearby soldier is hit and falls; adjacent soldier reacts. Frame 174-234: pinned soldier rescue and tree lift continue on the same timeline.",
        "Frame 162-202: Chinese cover position returns fire; one soldier is hit; the second shooter ducks and looks toward him.",
        "Frame 242-268: one retreating soldier glances back while continuing to withdraw.",
        "Frame 340-408: Japanese perimeter advances; doorway pair remains visible; woman pulls the ring of a wooden-shaft explosive; house blast throws debris and soldiers outward.",
        "Frame 418-522: broad river crowd wades across varied lanes; multiple flat surface bodies drift; one pair assists an injured soldier; hit/fall and bullet splash cues remain active.",
        "Frame 538-553: sender extends the box, receiver secures it, sender releases, receiver moves away carrying it.",
        "Frame 588-676: Old Meng raises an arm to shade his eyes, lowers it as the camera reaches the front, then holds the low-angle hero frame.",
        "",
        "Stage status:"
    ]
    for key, value in STATUS.items():
        lines.append("%s : %s" % (key, value))
    lines.extend(["", "Camera path samples (banked choreography):"])
    cam = bpy.data.objects.get("BFP_V20_ACTIVE_CAMERA")
    if cam:
        for frame in (1, 22, 32, 52, 70, 90, 108, 124, 148, 172, 188, 204, 220, 244, 254, 274, 298, 322, 350, 370, 378, 388, 410, 430, 458, 466, 488, 512, 536, 582, 608, 622, 650, 664, 700, 742, 790, 830, 870, 900):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            p = cam.matrix_world.translation
            lines.append("Frame %d : %.2f, %.2f, %.2f" % (frame, p.x, p.y, p.z))
    lines.extend(["", "Execution log:"])
    lines.extend(REPORT)
    txt.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def legacy_v12_main_unused():
    log("START " + VERSION)
    log("Blender version " + bpy.app.version_string)

    clear_generated_collections()
    hide_legacy_versions()
    create_materials()

    run_stage("LANDSCAPE_OPEN_SKY", build_landscape)
    run_stage("IRREGULAR_DENSE_WOODLAND_AND_ROCK_PASSAGES", build_forest)
    run_stage("TACTICAL_COVER_AND_ADVANCE_LAYOUT", build_tactical_layout)
    run_stage("LIXINGOU_RAVINE", build_ravine)
    run_stage("WUTONGGOU_BREACHED_HOUSE_AND_APPROACH_MARKERS", build_village)
    run_stage("STATIC_HOUSE_BLAST_SMOKE_PLACEHOLDERS", build_house_blast_smoke)
    run_stage("CURVED_RIVER_AND_UNDERWATER_OBSTACLES", build_river)
    run_stage("WIDE_ROAD_AND_FUTURE_CROWD_LANES", build_wide_road_and_crowd_markers)
    run_stage("LOW_FINE_GRASS_FOR_GROUND_LEVEL_WIDE_ANGLE", build_ground_grass)
    run_stage("LOW_CAMERA_FOREGROUND_GROUND_ROCKS", build_ground_rocks)
    run_stage("HUGE_WEST_VALLEY_FRAME", build_west_pass)
    run_stage("WHITE_BLOCK_CHARACTERS_AND_PROPS", build_characters_and_props)
    run_stage("STORYBOARD_CRITICAL_ACTIONS_AND_FRAME_GATES", build_storyboard_details)
    run_stage("PACKED_TERRAIN_REFERENCE_BOARD", add_terrain_reference_board)
    run_stage("ANIMATED_BATTLEFIELD_INTERACTIONS", build_battlefield_fx)
    run_stage("ACTOR_INFORMED_CAMERA_ANIMATION", build_camera)
    run_stage("CAMERA_PATH_DEBUG", build_camera_path_debug)
    run_stage("LIGHTING", configure_lighting)
    run_stage("SCENE_CONFIGURATION", configure_scene)
    run_stage("FORCE_CAMERA_VIEW", force_camera_view)

    cam = bpy.data.objects.get("BFP_V20_ACTIVE_CAMERA")
    if cam:
        samples = []
        for frame in (1, 22, 32, 52, 70, 90, 108, 124, 148, 172, 188, 204, 220, 244, 254, 274, 298, 322, 350, 370, 378, 388, 410, 430, 458, 466, 488, 512, 536, 582, 608, 622, 650, 664, 700, 742, 790, 830, 870, 900):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            p = cam.matrix_world.translation
            samples.append((round(p.x, 2), round(p.y, 2), round(p.z, 2)))
        STATUS["CAMERA_MOVEMENT_CHECK"] = "PASS" if len(set(samples)) > 1 else "FAIL"
        log("Camera position samples: " + repr(samples))
    else:
        STATUS["CAMERA_MOVEMENT_CHECK"] = "FAIL - camera missing"

    bpy.context.scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()
    write_build_report()
    log("FINISHED. Open BFP_V20_BUILD_REPORT if anything failed.")
    try:
        output_dir = get_script_directory()
        if not output_dir:
            output_dir = os.path.expanduser("~/Desktop")
        os.makedirs(output_dir, exist_ok=True)
        blend_path = os.path.join(output_dir, "Battlefield_OneTake_Previs_V1_2.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        STATUS["BLEND_SAVE"] = "PASS - " + blend_path
        log("Saved Blender scene: " + blend_path)
        write_build_report()
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    except Exception as exc:
        STATUS["BLEND_SAVE"] = "FAIL: " + repr(exc)
        log("BLEND SAVE FAILED: " + repr(exc))
    log("V1.2 emphasizes a non-linear banked camera choreography, terrain-scale expansion, four-aircraft approach, pigeon glide, staged aviation bombs, forest rescue, doorway blast, broad river crowd, surface casualties and storyboard-aligned frame passages. Inspect BFP_V20_BUILD_REPORT.")


# ============================================================
# V2 implementation. Legacy construction helpers above are retained locally;
# entrypoint below supersedes V1.2 main(), camera and timing.
# ============================================================
import json, csv, sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
CFG = {
    'crowd_clearance_height_m':1.5, 'fps':30, 'camera_radius':0.22, 'safety_margin':0.12,
    'width':640, 'height':360, 'float_bodies':40, 'bank_runners':20,
    'seed':20261101, 'render_engine':'BLENDER_WORKBENCH',
    # old timeline boundaries / new seconds: editable pacing, no 30s cap
    'time_map':[(1,0),(98,30),(232,59),(332,79),(410,103),
                (512,133),(564,146),(664,167),(900,190)],
}
OUT = Path(get_script_directory())

def time_frame(f):
    m=CFG['time_map']
    for (a,ta),(b,tb) in zip(m,m[1:]):
        if f<=b: return 1+(ta+(f-a)/(b-a)*(tb-ta))*CFG['fps']
    return 1+m[-1][1]*CFG['fps']+(f-m[-1][0])

def curves(obj):
    a=getattr(getattr(obj,'animation_data',None),'action',None)
    if not a: return []
    try: return list(a.fcurves)
    except AttributeError:
        result=[]
        for layer in a.layers:
            for strip in layer.strips:
                for bag in strip.channelbags: result.extend(bag.fcurves)
        return result

def retime():
    actions=set()
    for obj in list(bpy.data.objects)+list(bpy.data.materials)+list(bpy.data.cameras):
        for fc in curves(obj):
            if fc.as_pointer() in actions: continue
            actions.add(fc.as_pointer())
            for k in fc.keyframe_points:
                old=k.co.x; delta=time_frame(old)-old
                k.co.x+=delta; k.handle_left.x+=delta; k.handle_right.x+=delta
            fc.update()
    for mk in bpy.context.scene.timeline_markers: mk.frame=round(time_frame(mk.frame))

def root_offset(root, delta):
    root.location+=Vector(delta)
    for fc in curves(root):
        if fc.data_path=='location':
            for k in fc.keyframe_points:
                d=delta[fc.array_index]; k.co.y+=d; k.handle_left.y+=d; k.handle_right.y+=d

# The rescue belongs in Li Xingou, separate from the forest firing beat.
def extra_events():
    for name in ['CN_FOREST_PINNED_UNDER_TREE_ROOT','CN_FOREST_RESCUER_ROOT',
                 'FOREST_RESCUE_FALLEN_TREE_TRUNK']:
        ob=bpy.data.objects.get(name)
        if ob:
            root_offset(ob,(73,-12,0))
            for fc in curves(ob):
                for k in fc.keyframe_points:
                    k.co.x+=100; k.handle_left.x+=100; k.handle_right.x+=100
    # Waders' feet and camera share a real 1.8m-deep bed, not two separate levels.
    for ob in bpy.data.objects:
        if ob.type=='MESH' and ('BLOOD_TINT' in ob.name or 'UNIFORM_LIMB' in ob.name):
            ob.hide_render=True; ob.hide_viewport=True
        if ob.type=='EMPTY' and not ob.parent and 'ROOT' in ob.name:
            if ('RIVER' in ob.name or 'SHALLOW_WATER' in ob.name) and 'BODY' not in ob.name and 'FLOAT' not in ob.name and 'CASUALTY' not in ob.name and 'HANDOFF' not in ob.name:
                if -1.5<ob.location.z<0: root_offset(ob,(0,0,-0.25))
    random.seed(CFG['seed'])
    for i in range(CFG['float_bodies']-14):
        x,y=random.uniform(89,186),random.uniform(-29,29)
        r=make_casualty('V2_FLOAT_%02d'%i,(x,y,0.12),yaw=random.uniform(-math.pi,math.pi),pose=['prone','supine','side'][i%3])
        for f in (1,450,900):
            r.location=(x+(f-1)*.002,y+(f-1)*.001,0.12+.04*math.sin(f*.03+i));r.keyframe_insert(data_path='location',frame=f)
    for i in range(6):
        actor=make_actor('V2_WATER_FALL_%02d'%i,(100+i*13,random.uniform(-12,12),-0.98))
        animate_hit_fall_performance(actor,445+i*9,460+i*9,(-1)**i)
        make_water_splash('V2_FALL_SPLASH_%02d'%i,(100+i*13,actor['root'].location.y,.38),450+i*9)
    for i in range(CFG['bank_runners']):
        x,y=random.uniform(193,228),random.choice([-1,1])*random.uniform(5,22)
        actor=make_actor('V2_BANK_RUN_%02d'%i,(x,y,0),rifle=i%3==0)
        animate_actor(actor,[(1,(x-55,y,-1.5),0),(510,(x,y,0),0),(900,(x+75,y,0),0)])
    # Extend locomotion across Master Timeline (not tied to the observation window).
    for ob in list(bpy.data.objects):
        if ob.type=='EMPTY' and ob.name.endswith('_ROOT') and any(x in ob.name for x in ['MAIN_CHARGE','GUARD_COMPANY','VALLEY_EXIT_RUNNER','FOREST_RUNNER','RAVINE_RUNNER']):
            for fc in curves(ob):
                if fc.data_path=='location' and len(fc.keyframe_points)>1:
                    ks=fc.keyframe_points; a,b=ks[0],ks[-1]; v=(b.co.y-a.co.y)/(b.co.x-a.co.x)
                    fc.keyframe_points.insert(1,a.co.y+(1-a.co.x)*v)
                    fc.keyframe_points.insert(900,b.co.y+(900-b.co.x)*v)
    # Independent body breathing for Meng.
    torso=bpy.data.objects['OLD_MENG_TORSO']
    for f in range(1,901,15):
        torso.scale=(.52,.36,.76*(1+.015*math.sin(f*.1)));torso.keyframe_insert(data_path='scale',frame=f)
    # Doorway grenade components follow the carrier's transform without jumping.
    for n in ['WUTONGGOU_OLD_WOODEN_SHAFT_GRENADE','WUTONGGOU_WOODEN_GRENADE_METAL_CAP']:
        ob=bpy.data.objects[n]; parent=bpy.data.objects['WUTONGGOU_WOUNDED_MAN_ON_BACK_ROOT']
        bpy.context.view_layer.update(); world=ob.matrix_world.copy();ob.parent=parent;ob.matrix_world=world
    # Receiver emerges from river before reaching handoff; carried box bound to receiver after grip.
    r=bpy.data.objects['CN_BOX_HANDOFF_RECEIVER_ROOT']
    for f,p,yaw in [(500,(193,-4,-1.5),0),(524,(200,-4,-.4),math.pi),(538,(202,-4,0),math.pi),
                    (553,(202,-4,0),math.pi),(570,(208,-13,0),-.9),(600,(225,-30,0),-.9),(900,(300,-55,0),-.9)]:
        r.location=p;r.rotation_euler.z=yaw;r.keyframe_insert(data_path='location',frame=f);r.keyframe_insert(data_path='rotation_euler',frame=f)
    box=bpy.data.objects['RIVERBANK_HANDOFF_BOX']
    box.animation_data_clear()
    for f,p in [(1,(198.7,-4,1.1)),(538,(198.7,-4,1.1)),(546,(201.1,-4,1.1)),(553,(201.4,-4,1.1))]:
        box.location=p;box.keyframe_insert(data_path='location',frame=f)
    con=box.constraints.new('CHILD_OF');con.target=r
    bpy.context.scene.frame_set(553);bpy.context.view_layer.update();con.inverse_matrix=r.matrix_world.inverted()
    for f,v in [(1,0),(552,0),(553,1)]:con.influence=v;con.keyframe_insert(data_path='influence',frame=f)
    for fc in curves(box):
        if 'influence' in fc.data_path:
            for k in fc.keyframe_points:k.interpolation='CONSTANT'

# Purposeful observation points; all entries refer to the legacy event clock,
# then camera and actors are retimed together to a 190s master clock.
V2_KEYS=[
(1,(-285,-34,165),(-240,-20,118),'Sky',0),
(12,(-246,-20,124),(-225,-16,115),'Pigeon',0),
(22,(-232,-13,118),(-222,-16,115),'Pigeon glide',0),
(32,(-210,-18,116),(-150,-21,113),'Aircraft approach',0),
(42,(-181,-27,111),(-148,-22,113),'Bomber close',-4),
(52,(-163,-26,107),(-158,-22,111),'Under wing release',-5),
(60,(-167,-19,100),(-166,-22,108),'Belly and bombs',0),
(70,(-175,-14,73),(-181,-8,30),'Descent',4),
(80,(-185,-12,34),(-181,-8,2),'Bomb descent',3),
(90,(-184,-14,8),(-181,-8,1),'Impact',0),
(98,(-174,-10,2.2),(-158,-3,1),'Forest entry',0),
(108,(-163,-7,1.7),(-157,-3,1.1),'JP firing',0),
(124,(-156,-6,1.6),(-151,2,1),'JP reaction',-3),
(145,(-146,-4,1.5),(-148,-1,.8),'Hit and fall',0),
(156,(-141,-12,1.5),(-137,-8,1),'CN cover',3),
(176,(-132,-16,1.4),(-130,-12,1),'Return fire',0),
(197,(-122,-9,1.4),(-124,-5,.6),'CN casualty',-3),
(212,(-104,-2,1.5),(-92,7,1),'Branch dodge',4),
(232,(-81,5,1.7),(-57,10,1),'Ravine reveal',0),
(254,(-54,4,1.5),(-45,-4,.3),'Losses',-3),
(274,(-43,-5,1.5),(-35,0,.7),'Pinned soldier',0),
(288,(-40,-6,1.4),(-38,-2,1),'Rescuer bends',0),
(302,(-34,-6,1.5),(-36,-1,1),'Tree lift',0),
(314,(-30,-3,1.5),(-34,0,1),'Rescue continues',3),
(332,(20,2,2.2),(48,-2,1),'Village approach',0),
(350,(53,-5,1.6),(44,-2,1),'JP rear approach',0),
(360,(43,-10,1.6),(35,-7,1.5),'Doorway pair',0),
(370,(39,-10,1.65),(35.5,-7,1.6),'Ring pull readable medium',0),
(378,(43,-9,2),(36,-7,2),'House blast',5),
(388,(49,-9,2.8),(40,-7,3),'Blast reaction',8),
(398,(60,-6,2.5),(72,-4,.5),'Smoke exit',3),
(410,(70,-9,2.2),(101,0,.8),'River opens',0),
(420,(82,-8,.1),(94,-4,.1),'Water entry',-4),
(430,(97,-7,-.4),(108,-4,-.3),'Waders legs',-5),
(440,(112,-6,-.4),(120,4,-.3),'Assisted crossing',0),
(450,(124,-6,-.4),(121,6,-.6),'Underwater bodies',3),
(458,(130,-4,-.4),(140,-1,-.3),'Brake',0),
(462,(129.5,-4,-.4),(140,-1,-.3),'Inertial recoil',0),
(466,(129,-7,-.4),(143,-1,-.4),'Side dodge',6),
(476,(140,-8,-.35),(145,-3,-.2),'Float clearance',3),
(488,(155,-6,-.3),(165,0,.2),'Rise',0),
(500,(176,-8,.7),(194,-4,1),'Surface',0),
(512,(189,-10,1),(200,-4,1),'Bank emergence',0),
(524,(196,-11,1.25),(200,-4,1),'Transfer approach',0),
(538,(198,-9,1.3),(200,-4,1),'Sender reaches',0),
(550,(200,-9,1.3),(201,-4,1),'Receiver secures',0),
(558,(203,-8,1.2),(209,-12,1),'Run screen right',0),
(564,(225,3,.7),(250,0,1.3),'Meng approach',0),
(582,(240,0,.65),(250,0,1.2),'Meng back',0),
(594,(246,0,.6),(250,0,1.1),'Orbit start',0),
(608,(247.17,2.83,.6),(250,0,1.1),'Rear quarter',2),
(622,(250,4,.6),(250,0,1.1),'Side',3),
(636,(252.83,2.83,.6),(250,0,1.1),'Front quarter',2),
(650,(254,0,.6),(250,0,1.1),'Hero front',0),
(664,(255,0,.7),(250,0,1.15),'Pull back begins',0),
(680,(263,0,1.4),(250,0,1.2),'Charge',0),
(700,(280,0,2.8),(250,0,1.2),'Charge layers',-3),
(720,(302,0,5),(250,0,1.2),'Valley frame',0),
(742,(322,0,10),(250,0,1.4),'Pass entrance',3),
(762,(345,0,18),(260,0,2),'Inside valley',0),
(790,(370,5,35),(280,0,2),'Lift',0),
(830,(412,3,65),(260,0,2),'Wide',0),
(870,(460,0,105),(210,0,0),'Battlefield',0),
(900,(510,0,150),(140,0,0),'Final',0)]

def white_materials():
    for k,m in MATS.items():
        if k in ['path','marker']:continue
        gray={'ground':.52,'leaf':.62,'leaf_light':.7,'trunk':.45,'cn_soldier':.82,'jp_soldier':.58,'old_meng':.9,'weapon':.25,'grenade':.3,'water':.45,'smoke':.72,'dust':.66}.get(k,.68)
        color=(gray,gray,gray,1)
        if k=='water':color=(.35,.48,.53,.24)
        if k in ['smoke','dust']:color=(gray,gray,gray,.28)
        m.diffuse_color=color
        bs=m.node_tree.nodes.get('Principled BSDF')
        if bs:bs.inputs['Base Color'].default_value=color;bs.inputs['Alpha'].default_value=color[3]


def setup_camera_v2():
    global CAMERA_KEYS, CAMERA_FOCAL_KEYS
    CAMERA_KEYS=V2_KEYS
    CAMERA_FOCAL_KEYS=[(k[0],24 if k[0]<98 else 32 if k[0]<594 else 28 if k[0]<680 else 24) for k in V2_KEYS]
    build_camera();bpy.context.scene.camera.data.dof.use_dof=False
    bpy.context.scene.camera.data.clip_start=.06
    bpy.context.scene.camera.data.clip_end=2500


def configure_v2():
    s=bpy.context.scene;s.frame_start=1;s.frame_end=round(time_frame(900));s.render.fps=30
    s.render.resolution_x=CFG['width'];s.render.resolution_y=CFG['height'];s.render.resolution_percentage=100
    s.render.engine=CFG['render_engine']
    sh=s.display.shading;sh.light='STUDIO';sh.studiolight_rotate_z=.4;sh.color_type='MATERIAL'
    sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=True
    sh.background_type='WORLD';s.world.color=(.13,.13,.13);s.display.render_aa='FXAA'
    s.view_settings.view_transform='Standard'
    for c in bpy.data.collections:
        if any(x in c.name for x in ['MARKER','PATH_DEBUG','TACTICAL']):c.hide_render=True
    for ob in bpy.data.objects:
        if 'CAMERA_PATH' in ob.name or 'DIRECTION_MARKER' in ob.name:ob.hide_render=True
    s['requirement_baseline']='User V1.0; implementation V2.0; original V1.2 preserved'
    s['target_blender']='5.2.x (not validated)';s['validated_blender']=bpy.app.version_string
    s['camera_safety_radius_m']=CFG['camera_radius'];s['camera_margin_m']=CFG['safety_margin']
    s['master_timeline_seconds']=CFG['time_map'][-1][1]
    for f,n in [(98,'02 Forest'),(232,'03 Li Xingou'),(332,'04 House'),(410,'05 River'),(512,'06A Handoff'),(564,'06B Meng'),(664,'07 Valley')]:
        s.timeline_markers.new(n,frame=round(time_frame(f)))
    s.frame_set(1)


# Shared immutable mesh data: crowd parts reuse one unit primitive per material.
import bmesh
_MESH_CACHE={}
def unit_mesh(kind,material,sub=1,vertices=7):
    key=(kind,material.name if material else None,sub,vertices)
    cached=_MESH_CACHE.get(key)
    if cached and cached.name in bpy.data.meshes:return cached
    bm=bmesh.new()
    if kind=='cube':bmesh.ops.create_cube(bm,size=1)
    elif kind=='ico':bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=1)
    else:bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=vertices,radius1=1,radius2=1,depth=1)
    mesh=bpy.data.meshes.new('V2_SHARED_'+kind);bm.to_mesh(mesh);bm.free()
    if material:mesh.materials.append(material)
    _MESH_CACHE[key]=mesh;return mesh

def cube(name,loc,dims,material,coll,rot=(0,0,0)):
    ob=bpy.data.objects.new(name,unit_mesh('cube',material));coll.objects.link(ob)
    ob.location=loc;ob.scale=dims;ob.rotation_euler=rot;return ob

def ico(name,loc,scale,material,coll,sub=1,rot=(0,0,0)):
    ob=bpy.data.objects.new(name,unit_mesh('ico',material,sub=sub));coll.objects.link(ob)
    ob.location=loc;ob.scale=scale;ob.rotation_euler=rot;return ob

def cylinder(name,loc,radius,depth,material,coll,vertices=7,rot=(0,0,0)):
    ob=bpy.data.objects.new(name,unit_mesh('cylinder',material,vertices=vertices));coll.objects.link(ob)
    ob.location=loc;ob.scale=(radius,radius,depth);ob.rotation_euler=rot;return ob

_base_make_actor=make_actor
def make_actor(name,loc,yaw=0.,faction='cn',posture='stand',rifle=False,grenades=0,material_override=None):
    actor=_base_make_actor(name,loc,yaw,faction,posture,rifle,grenades,material_override)
    c=get_collection('BFP_V20_16_CHARACTERS');head=actor['head'];root=actor['root']
    hz=head.location.z
    if faction=='jp':
        child_ico(name+'_HELMET',root,(0,0,hz+.10),(.27,.27,.19),MATS['jp_soldier'],c)
    elif faction!='old_meng':
        child_cube(name+'_CAP',root,(0,0,hz+.19),(.38,.42,.10),MATS['cn_soldier'],c)
    if faction=='old_meng':
        child_cube(name+'_BELT',root,(0,0,.95),(.56,.40,.09),MATS['weapon'],c)
        child_ico(name+'_NOSE',head,(.90,0,0),(.22,.18,.22),MATS['old_meng'],c)
        for side in [-1,1]:child_ico(name+'_EYE_'+str(side),head,(.83,side*.44,.25),(.09,.08,.08),MATS['weapon'],c)
    return actor

_old_extra_events=extra_events
def extra_events():
    _old_extra_events()
    pinned=bpy.data.objects['CN_FOREST_PINNED_UNDER_TREE_ROOT']
    pinned.rotation_euler.z=math.pi/2;root_offset(pinned,(0,-.65,0))
    for i in range(3):
        ob=bpy.data.objects['JP_HOUSE_BLAST_FALL_%02d_ROOT'%i]
        p=Vector((40+i*1.5,-1+i*3,0))
        for f,d in [(382+i*2,(0,0,0)),(393+i*2,(2,1,2.5)),(409+i*2,(5,2,-.1))]:
            ob.location=p+Vector(d);ob.keyframe_insert(data_path='location',frame=f)
    c=get_collection('BFP_V20_18_BATTLE_FX')
    for ob in list(bpy.data.objects):
        if ob.type=='EMPTY' and ob.name.endswith('_ROOT') and ('COVER' in ob.name or 'MID_SHOOTER' in ob.name) and ob.name.startswith('CN_'):
            ob.rotation_euler.z=math.pi
        if ob.type=='EMPTY' and ob.name.endswith('_ROOT') and any(x in ob.name for x in ['SHOOTER','COVER_A','COVER_B']):
            flash=child_ico(ob.name+'_MUZZLE',ob,(1.25,-.22,1.1),(.001,)*3,MATS['blast'],c)
            for f in range(1,901,18):
                for df,sc in [(0,.001),(1,.18),(2,.001)]:
                    flash.scale=(sc*2,sc,sc);flash.keyframe_insert(data_path='scale',frame=f+df)
    for i in range(8):
        release=48+i*3
        plane=bpy.data.objects['JAPANESE_BOMBER_LEFT_NEAR_ROOT' if i%2==0 else 'JAPANESE_BOMBER_RIGHT_NEAR_ROOT']
        bpy.context.scene.frame_set(release);bpy.context.view_layer.update();p=plane.matrix_world.translation.copy();p.z-=1.1
        make_aircraft_bomb('V2_AIR_BOMB_%02d'%i,release,p,release+40,(p.x-22,p.y,1.1),start_loc=p)
        make_small_blast('V2_AIR_IMPACT_%02d'%i,(p.x-22,p.y,1),release+40,radius=2.5)
    bpy.context.scene.frame_set(1)

def main_v2():
    for key in ['v2_ground_patched','v2_walkers_grounded','v2_final_assets','v2_air_dodge','v2_crowd_clearance']:
        bpy.context.scene[key]=False
    clear_generated_collections();hide_legacy_versions();create_materials()
    stages=[build_landscape,build_forest,build_tactical_layout,build_ravine,build_village,build_house_blast_smoke,build_river,
            build_wide_road_and_crowd_markers,build_ground_grass,build_ground_rocks,build_west_pass,
            build_characters_and_props,build_storyboard_details,build_battlefield_fx,configure_lighting]
    # Fail fast: never save a partially constructed scene as a successful build.
    for fun in stages:
        print('V2 BUILD',fun.__name__,flush=True);fun()
    extra_events();setup_camera_v2();retime();white_materials();configure_v2()
    # pack supplied references, without requiring external paths when opening blend
    ref=OUT.parent/'reference_original'/'Battlefield_OneTake_Previs_V1_2_Package'
    for p in ref.glob('*.png'):
        im=bpy.data.images.load(str(p),check_existing=True);im.pack()
    config_text=bpy.data.texts.get('V2_CONFIG') or bpy.data.texts.new('V2_CONFIG')
    config_text.clear();config_text.write(json.dumps(CFG,indent=2))
    script=bpy.data.texts.get('battlefield_v2.py') or bpy.data.texts.new('battlefield_v2.py')
    script.clear();script.write(Path(__file__).read_text())
    path=OUT/'battlefield_v2.blend'
    if path.exists():
        import shutil,datetime
        history=OUT/'history';history.mkdir(exist_ok=True)
        shutil.copy2(path,history/('battlefield_v2_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend'))
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print('V2_BUILD_SUCCESS',path,flush=True)

if __name__=='__main__':
    main_v2()
    import runpy
    runpy.run_path(str(OUT/'validate_scene.py'),run_name='__main__')
