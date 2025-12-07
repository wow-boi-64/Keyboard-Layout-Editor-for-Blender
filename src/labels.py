from bpy import context, ops, data
import re
import os
from math import pi
from .helpers import *
from .key import Profile, Label, Key
from .char_ranges import CJK_RANGES, DEJAVU_RANGES
from typing import Tuple, List


LABEL_ALIGNMENT = {
    Profile.DCS: [0.25, 0.05, 0.25, 0.25],
    Profile.DSA: [0.25, 0.15, 0.25, 0.2],
    Profile.SA:  [0.25, 0.2,  0.25, 0.2],
    Profile.DSS: None,
}

CAP_THICKNESS = 0.001
ICON_FAMILIES = {
    "kb": "kbd-webfont",
    "fa": "font-awesome"
}

SYMBOLA = data.fonts.load(os.path.join(os.path.dirname(
    __file__), "fonts", "symbola.ttf"))
ENGRAVERS_GOTHIC = data.fonts.load(os.path.join(os.path.dirname(
    __file__), "fonts", "engravers_gothic.ttf"))
HELVETICA = data.fonts.load(os.path.join(os.path.dirname(
    __file__), "fonts", "helvetica.ttf"))
DEJAVU = data.fonts.load(os.path.join(os.path.dirname(
    __file__), "fonts", "deja_vu.ttf"))
NOTO = data.fonts.load(os.path.join(os.path.dirname(
    __file__), "fonts", "noto_cjk.ttc"))

ALIGN_TEXT = [
    ["LEFT",   "TOP"],
    ["CENTER", "TOP"],
    ["RIGHT",  "TOP"],
    ["LEFT",   "CENTER"],
    ["CENTER", "CENTER"],
    ["RIGHT",  "CENTER"],
    ["LEFT",   "BOTTOM"],
    ["CENTER", "BOTTOM"],
    ["RIGHT",  "BOTTOM"]
]


def add_curve(
    key: Key,
    curve,
    text_length: int,
    label_material_name: str,
    label_size: int,
    key_object,
    box: Tuple[float],
    offset: float,
):
    """Helper to add curve/text as a key label"""
    from bpy import context, ops, data

    # Orient and place above the key
    curve.rotation_euler[2] = pi
    curve.data.extrude = 0.01
    curve.location[2] = key_object.location[2] + key_object.dimensions[2]

    # Link to scene / collection
    add_object(curve)
    if hasattr(context, "view_layer"):
        context.view_layer.update()
    else:
        context.scene.update()

    unselect_all()
    select_object(curve)
    set_active_object(curve)

    # Convert to mesh so shrinkwrap works reliably
    ops.object.convert(target='MESH')
    curve.active_material = data.materials[label_material_name]

    # NO REMESH: remesh was collapsing some labels into dots

    unselect_all()
    set_active_object(curve)

    # Shrinkwrap label gently onto key surface
    ops.object.modifier_add(type='SHRINKWRAP')
    context.object.modifiers["Shrinkwrap"].offset = offset
    context.object.modifiers["Shrinkwrap"].wrap_method = 'PROJECT'
    context.object.modifiers["Shrinkwrap"].use_project_z = True
    context.object.modifiers["Shrinkwrap"].use_positive_direction = True
    context.object.modifiers["Shrinkwrap"].use_negative_direction = True
    context.object.modifiers["Shrinkwrap"].target = key_object
    apply_modifier("Shrinkwrap")

    # Slight lift to avoid z-fighting
    curve.location[2] += CAP_THICKNESS

    # Try to set full crease on edges (Blender 4+ safe)
    obj = context.object
    if obj and obj.type == 'MESH':
        me = obj.data

        prev_mode = context.mode
        if prev_mode != 'OBJECT':
            ops.object.mode_set(mode='OBJECT')

        try:
            if "crease_edge" not in me.attributes:
                me.attributes.new(name="crease_edge", type="FLOAT", domain="EDGE")
            attr = me.attributes["crease_edge"]
        except:
            attr = None

        for i, edge in enumerate(me.edges):
            if hasattr(edge, "crease"):
                try:
                    edge.crease = 1.0
                except:
                    pass
            elif attr:
                try:
                    attr.data[i].value = 1.0
                except:
                    pass

        if prev_mode != 'OBJECT':
            ops.object.mode_set(mode=prev_mode)

    # Join into key object so no stray labels remain
    unselect_all()
    select_object(curve)
    set_active_object(key_object)
    ops.object.join()


def add_icon(
    icon_family: str,
    icon_name: str,
    size: float,
    label_position: int,
    box: Tuple[float],
):
    """Add an icon label to a key"""
    select_all()
    ops.import_curve.svg(
        filepath=os.path.join(
            os.path.dirname(__file__),
            "fonts",
            ICON_FAMILIES[icon_family],
            icon_name + ".svg",
        )
    )
    new_label = [c for c in context.scene.objects if not c.select_get()][0]

    unselect_all()
    set_active_object(new_label)
    new_label.dimensions = [
        size,
        size * (new_label.dimensions[1] / new_label.dimensions[0]),
        0,
    ]
    ops.object.origin_set(type='ORIGIN_GEOMETRY')

    align_x = ALIGN_TEXT[label_position][0]
    align_y = ALIGN_TEXT[label_position][1]

    x_offset = 0

    if align_x == 'LEFT':
        x_offset = new_label.dimensions[0] / 2
    elif align_x == 'CENTER':
        x_offset = box[2] / 2
    elif align_x == 'RIGHT':
        x_offset = box[2] - new_label.dimensions[0] / 2

    if align_y == 'TOP':
        y_offset = new_label.dimensions[1] / 2
    elif align_y == 'CENTER':
        y_offset = box[3] / 2
    elif align_y == 'BOTTOM':
        y_offset = box[3] - new_label.dimensions[1] / 2

    new_label.location = [box[0] - x_offset, box[1] + y_offset, 2]

    return new_label


def add_text(
    text: str,
    size: float,
    font,
    label_position: int,
    box: Tuple[float],
):
    """Add a text label to the scene"""
    new_label_data = data.curves.new(type="FONT", name="keylabel")
    new_label = data.objects.new("label", new_label_data)
    new_label.data.body = text

    new_label.data.font = font
    new_label.data.size = size

    vertical_correction = -0.1 if text in [",", ";", ".", "[", "]"] else 0

    new_label.data.text_boxes[0].width = box[2]
    new_label.data.text_boxes[0].height = box[3] + vertical_correction * size

    new_label.data.text_boxes[0].y = -size
    new_label.data.align_x = ALIGN_TEXT[label_position][0]
    new_label.data.align_y = ALIGN_TEXT[label_position][1]

    new_label.location = [box[0], box[1], 2]

    return new_label


def add(
    key: Key,
    fonts: List,
    label_position: int,
    material_name: str,
    key_obj,
):
    """Add the given label to the scene"""
    key_label = key.labels[label_position]

    font = ENGRAVERS_GOTHIC if key.profile is Profile.DSA or key.profile is Profile.SA else HELVETICA
    offset = 0.0005
    label_align = LABEL_ALIGNMENT[key.profile]

    # Some legends arrive with size 0 / None (e.g. some F-row/Fn/End).
    # Use a sensible default instead of letting them vanish.
    raw_size = key_label.size
    if raw_size is None or raw_size <= 0:
        raw_size = 3  # typical KLE default

    label_size = raw_size / 15.0

    box_top = key.y + label_align[1]
    box_left = -1 * key.x - label_align[0]
    box_height = key.height - (label_align[1] + label_align[3])
    box_width = key.width - (label_align[0] + label_align[2])
    box = (box_left, box_top, box_width, box_height)
    label_length = len(key_label.text)

    curve = None
    match = re.fullmatch(
        r"<i class=['\"](fa|kb) (fa|kb)-([a-zA-Z0-9\-]+)['\"]><\/i>",
        key_label.text,
    )

    if match is not None:
        # icon label
        label_size *= 0.5
        curve = add_icon(match[1], match[3], label_size, label_position, box)
        label_length = 1
    else:
        # text label
        max_char = max(ord(c) for c in key_label.text)
        if max_char < 0xFF or fonts[label_position] is not None:
            font = fonts[label_position] if fonts[label_position] is not None else font
        elif in_charset(max_char, CJK_RANGES):
            font = NOTO
            offset = 0.0001
            label_size = raw_size / 7.5
        elif in_charset(max_char, DEJAVU_RANGES):
            font = DEJAVU
            offset = 0.0001
            label_size = raw_size / 11.5
        else:
            font = SYMBOLA

        curve = add_text(key_label.text, label_size, font, label_position, box)

    # use the corrected raw_size for downstream logic
    add_curve(key, curve, label_length, material_name, raw_size, key_obj, box, offset)
