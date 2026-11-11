# SPDX-License-Identifier: GPL-2.0-or-later
"""Minimal Android 11 survival mode: bones, weights, saving, nothing else."""
import bpy
from bpy.types import Menu, Operator
from bpy.app.handlers import persistent

ON = True
AUTO_BOUNDS = True
PREV_SCENES = {}
PREV_SPACES = {}
PREV_SYSTEM = {}
PREV_MESH = {}
PREV_BONES = {}
LAST_MODE = None

def set_safe(obj, name, value):
    try:
        if hasattr(obj, name) and getattr(obj, name) != value:
            setattr(obj, name, value)
    except (RuntimeError, AttributeError, TypeError, ValueError, ReferenceError) as exc:
        print("[Survival] property skipped", name, str(exc)[:90])

def spaces():
    wm = bpy.context.window_manager
    if wm is None:
        return []
    return [area.spaces.active for window in wm.windows
            for area in window.screen.areas if area.type == 'VIEW_3D']

def autosave():
    try:
        p = bpy.context.preferences.filepaths
        set_safe(p, 'use_auto_save_temporary_files', True)
        set_safe(p, 'auto_save_time', 3)
        if getattr(p, 'save_version', 2) < 2:
            set_safe(p, 'save_version', 2)
    except (RuntimeError, AttributeError) as exc:
        print("[Survival] native autosave unavailable:", exc)

def gpu():
    if not ON:
        return
    sys = bpy.context.preferences.system
    for key, val in (('viewport_aa', 'OFF'), ('anisotropic_filter', 'FILTER_0'),
                     ('gl_texture_limit', 'CLAMP_128'), ('use_gpu_subdivision', False)):
        if hasattr(sys, key):
            PREV_SYSTEM.setdefault(key, getattr(sys, key))
            set_safe(sys, key, val)
    for scene in bpy.data.scenes:
        render = scene.render
        state = PREV_SCENES.setdefault(scene.name_full, {})
        for key, val in (('use_simplify', True), ('simplify_subdivision', 0),
                         ('simplify_volumes', 0.0)):
            if hasattr(render, key):
                state.setdefault(key, getattr(render, key))
                set_safe(render, key, val)
    for space in spaces():
        try:
            key = space.as_pointer()
            if key in PREV_SPACES:
                continue
            sh, ov = space.shading, space.overlay
            shade = ('type', 'color_type', 'light', 'show_shadows',
                     'show_cavity', 'show_specular_highlight')
            overlay = ('show_floor', 'show_ortho_grid', 'show_axis_x', 'show_axis_y',
                       'show_relationship_lines', 'show_motion_paths',
                       'show_wpaint_contours')
            PREV_SPACES[key] = (
                {x: getattr(sh, x) for x in shade if hasattr(sh, x)},
                {x: getattr(ov, x) for x in overlay if hasattr(ov, x)})
            for x, y in (('type', 'SOLID'), ('color_type', 'MATERIAL'),
                         ('light', 'FLAT'), ('show_shadows', False),
                         ('show_cavity', False), ('show_specular_highlight', False)):
                set_safe(sh, x, y)
            for x in overlay:
                set_safe(ov, x, False)
            # Weight colors, selected outlines and bone overlays stay enabled.
        except (RuntimeError, ReferenceError, AttributeError):
            pass

def restore_mesh():
    for name, display in list(PREV_MESH.items()):
        obj = bpy.data.objects.get(name)
        if obj is not None and obj.type == 'MESH':
            set_safe(obj, 'display_type', display)
    PREV_MESH.clear()

def mode_tick():
    global LAST_MODE
    if not ON:
        return None
    try:
        gpu()
        obj = bpy.context.active_object
        mode = bpy.context.mode
        arm = obj if obj and obj.type == 'ARMATURE' else None
        state = (mode, arm.name_full if arm else '', AUTO_BOUNDS)
        if state == LAST_MODE:
            return 1.1
        LAST_MODE = state
        restore_mesh()
        if arm and mode in {'EDIT_ARMATURE', 'POSE'}:
            data = arm.data
            if data.name_full not in PREV_BONES:
                PREV_BONES[data.name_full] = (data.display_type, data.show_names)
            set_safe(data, 'display_type', 'STICK')
            set_safe(data, 'show_names', False)
        if mode == 'EDIT_ARMATURE' and arm and AUTO_BOUNDS:
            for linked in bpy.context.view_layer.objects:
                if linked.type != 'MESH':
                    continue
                bound = linked.parent == arm
                if not bound:
                    bound = any(mod.type == 'ARMATURE' and mod.object == arm
                                for mod in linked.modifiers)
                if bound:
                    PREV_MESH[linked.name_full] = linked.display_type
                    set_safe(linked, 'display_type', 'BOUNDS')
        # On PAINT_WEIGHT all previously boxed meshes were restored above.
        print("[Survival] mode", mode, "boxed", len(PREV_MESH), flush=True)
    except (RuntimeError, AttributeError, ReferenceError, TypeError) as exc:
        print("[Survival] mode skipped", str(exc)[:110], flush=True)
    return 1.1

def restore():
    global LAST_MODE
    restore_mesh()
    for name, pair in list(PREV_BONES.items()):
        arm = bpy.data.armatures.get(name)
        if arm:
            set_safe(arm, 'display_type', pair[0])
            set_safe(arm, 'show_names', pair[1])
    PREV_BONES.clear()
    for name, values in list(PREV_SCENES.items()):
        scene = bpy.data.scenes.get(name)
        if scene:
            for key, value in values.items():
                set_safe(scene.render, key, value)
    PREV_SCENES.clear()
    for space in spaces():
        old = PREV_SPACES.get(space.as_pointer())
        if old:
            for key, val in old[0].items():
                set_safe(space.shading, key, val)
            for key, val in old[1].items():
                set_safe(space.overlay, key, val)
    PREV_SPACES.clear()
    for key, val in PREV_SYSTEM.items():
        set_safe(bpy.context.preferences.system, key, val)
    PREV_SYSTEM.clear()
    LAST_MODE = None

@persistent
def load_pre(_):
    global LAST_MODE
    # Old Blender RNA objects become invalid after loading a new .blend.
    PREV_MESH.clear()
    PREV_BONES.clear()
    PREV_SCENES.clear()
    PREV_SPACES.clear()
    PREV_SYSTEM.clear()
    LAST_MODE = None

@persistent
def load_post(_):
    autosave()
    if ON:
        gpu()
        mode_tick()

class WM_OT_ultra_survival(Operator):
    bl_idname = "wm.ultra_survival"
    bl_label = "Ultra GPU / Rig Recovery"
    bl_options = {'REGISTER'}
    enabled: bpy.props.BoolProperty(default=True)
    def execute(self, context):
        global ON
        if self.enabled:
            ON = True
            gpu()
            mode_tick()
        else:
            restore()
            ON = False
        return {'FINISHED'}

class WM_OT_survival_bounds(Operator):
    bl_idname = "wm.survival_bounds"
    bl_label = "Bone Edit Auto Bounds"
    bl_options = {'REGISTER'}
    enabled: bpy.props.BoolProperty(default=True)
    def execute(self, context):
        global AUTO_BOUNDS, LAST_MODE
        AUTO_BOUNDS = self.enabled
        LAST_MODE = None
        mode_tick()
        return {'FINISHED'}

class VIEW3D_MT_ultra_survival(Menu):
    bl_label = "Ultra GPU / Rig Rescue"
    def draw(self, context):
        layout = self.layout
        o = layout.operator("wm.ultra_survival", text="Ultra GPU ON")
        o.enabled = True
        o = layout.operator("wm.ultra_survival", text="Ultra GPU OFF / Restore")
        o.enabled = False
        layout.separator()
        o = layout.operator("wm.survival_bounds", text="Bone Edit: show mesh as box")
        o.enabled = True
        o = layout.operator("wm.survival_bounds", text="Bone Edit: show full model")
        o.enabled = False
        layout.label(text="Weight Paint restores full mesh")
        layout.label(text="Native recovery every 3 minutes")

def view_menu(self, context):
    self.layout.menu("VIEW3D_MT_ultra_survival", text="Ultra GPU / Rig Rescue")

def file_menu(self, context):
    self.layout.separator()
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator("wm.recover_auto_save", text="Recover Auto Save...")

def install_menu():
    if not hasattr(bpy.types, 'VIEW3D_MT_view'):
        return 0.5
    bpy.types.VIEW3D_MT_view.append(view_menu)
    if hasattr(bpy.types, 'TOPBAR_MT_file'):
        bpy.types.TOPBAR_MT_file.append(file_menu)
    gpu()
    return None

def register():
    for cls in (WM_OT_ultra_survival, WM_OT_survival_bounds, VIEW3D_MT_ultra_survival):
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_pre.append(load_pre)
    bpy.app.handlers.load_post.append(load_post)
    autosave()
    if not bpy.app.background:
        bpy.app.timers.register(install_menu, first_interval=1.0)
        bpy.app.timers.register(mode_tick, first_interval=1.3)

def unregister():
    restore()
    for cb in (install_menu, mode_tick):
        if bpy.app.timers.is_registered(cb):
            bpy.app.timers.unregister(cb)
    for handlers, cb in ((bpy.app.handlers.load_pre, load_pre),
                         (bpy.app.handlers.load_post, load_post)):
        if cb in handlers:
            handlers.remove(cb)
    for cls, f in (('VIEW3D_MT_view', view_menu),
                   ('TOPBAR_MT_file', file_menu)):
        parent = getattr(bpy.types, cls, None)
        if parent:
            try:
                parent.remove(f)
            except (ValueError, RuntimeError):
                pass
    for cls in (VIEW3D_MT_ultra_survival, WM_OT_survival_bounds, WM_OT_ultra_survival):
        bpy.utils.unregister_class(cls)
