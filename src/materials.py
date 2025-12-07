import bpy
from .helpers import hex2rgb


class Material:
    """Make and modify materials"""
    def __init__(self, name: str):
        self.name = name
        self.xpos = 0
        self.ypos = 0

        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nodes = self.mat.node_tree.nodes
        # material output node
        self.output = self.nodes['Material Output']

    def link(self, from_node, from_slot_name, to_node, to_slot_name):
        output_socket = from_node.outputs[from_slot_name]
        input_socket = to_node.inputs[to_slot_name]
        self.mat.node_tree.links.new(output_socket, input_socket)

    def makeNode(self, type, name):
        node = self.nodes.new(type)
        node.name = name
        self.xpos += 200
        node.location = (self.xpos, self.ypos)
        return node


def _clear_all_but_output(mat_obj: bpy.types.Material):
    """Remove all nodes except the Material Output node."""
    nodes = mat_obj.node_tree.nodes
    for node in list(nodes):
        if node.type != 'OUTPUT_MATERIAL':
            nodes.remove(node)


def make_key_material(color: str):
    """Make a plastic keycap material (Principled BSDF), return the name."""
    if color not in bpy.data.materials:
        m = Material(color)

        # Clear whatever Blender created by default except the output
        _clear_all_but_output(m.mat)

        principled = m.makeNode('ShaderNodeBsdfPrincipled', 'Key Principled')

        # Base colour from the KLE hex (hex2rgb should return (r,g,b,a))
        principled.inputs['Base Color'].default_value = hex2rgb(color)

        # Tunable look – adjust to taste
        principled.inputs['Roughness'].default_value = 0.35

        m.link(principled, 'BSDF', m.output, 'Surface')

    return color


def make_led_material(color: str, strength: float):
    """Make a glowing material for LEDs / backlit legends, return the name."""
    material_name = f'led: {color}'
    if material_name not in bpy.data.materials:
        m = Material(material_name)

        _clear_all_but_output(m.mat)

        emission = m.makeNode('ShaderNodeEmission', 'Emission')
        emission.inputs["Color"].default_value = hex2rgb(color)
        emission.inputs["Strength"].default_value = strength * 5.0

        m.link(emission, 'Emission', m.output, 'Surface')

    return material_name
