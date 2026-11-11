# SPDX-License-Identifier: GPL-2.0-or-later
"""Minimal Android 11 Blender GPU configuration, without Edit Mode hooks."""
import bpy
from bpy.types import Menu, Operator
from bpy.app.handlers import persistent

ENABLED = True
PREVIOUS_SYSTEM = {}
PREVIOUS_VIEW = {}


def set_value(obj, name, value):
    try:
        if hasattr(obj, name) and getattr(obj, name) != value:
            setattr(obj, name, value)
    except (AttributeError, TypeError, ReferenceError, RuntimeError, ValueError):
        pass


def viewports():
    wm = bpy.context.window_manager
    if wm is None:
        return []
    return [area.spaces.active for win in wm.windows
            for area in win.screen.areas if area.type == 'VIEW_3D']


def configure_autosave():
    p = bpy.context.preferences.filepaths
    set_value(p, 'use_auto_save_temporary_files', True)
    set_value(p, 'auto_save_time', 3)
    if getattr(p, 'save_version', 2) < 2:
        set_value(p, 'save_version', 2)


def apply_low_gpu():
    # Critical regression safeguard: NEVER update Blender display or
    # scene properties while Edit, Pose or Weight Paint is active.
    if not ENABLED or bpy.app.background or bpy.context.mode != 'OBJECT':
        return False
    system = bpy.context.preferences.system
    for name, val in (('viewport_aa', 'OFF'),
                      ('anisotropic_filter', 'FILTER_0'),
                      ('gl_texture_limit', 'CLAMP_128'),
                      ('use_gpu_subdivision', False)):
        if hasattr(system, name):
            PREVIOUS_SYSTEM.setdefault(name, getattr(system, name))
            set_value(system, name, val)
    for space in viewports():
        try:
            key = space.as_pointer()
            if key in PREVIOUS_VIEW:
                continue
            sh, ov = space.shading, space.overlay
            shades = (('type', 'SOLID'), ('light', 'FLAT'),
                      ('color_type', 'MATERIAL'), ('show_shadows', False),
                      ('show_cavity', False), ('show_specular_highlight', False))
            extras = (('show_floor', False), ('show_ortho_grid', False),
                      ('show_axis_x', False), ('show_axis_y', False),
                      ('show_relationship_lines', False),
                      ('show_motion_paths', False))
            PREVIOUS_VIEW[key] = (
                {k: getattr(sh, k) for k, _ in shades if hasattr(sh, k)},
                {k: getattr(ov, k) for k, _ in extras if hasattr(ov, k)},
            )
            for k, v in shades:
                set_value(sh, k, v)
            for k, v in extras:
                set_value(ov, k, v)
        except (AttributeError, RuntimeError, ReferenceError):
            pass
    # No scene.render changes, no armature display swaps, no modifier changes.
    return True


def restore_view():
    if bpy.context.mode != 'OBJECT':
        return False
    for space in viewports():
        old = PREVIOUS_VIEW.get(space.as_pointer())
        if old:
            for key, val in old[0].items():
                set_value(space.shading, key, val)
            for key, val in old[1].items():
                set_value(space.overlay, key, val)
    PREVIOUS_VIEW.clear()
    for key, val in PREVIOUS_SYSTEM.items():
        set_value(bpy.context.preferences.system, key, val)
    PREVIOUS_SYSTEM.clear()
    return True


@persistent
def on_load_pre(_unused):
    PREVIOUS_VIEW.clear()
    PREVIOUS_SYSTEM.clear()


@persistent
def on_load_post(_unused):
    configure_autosave()
    apply_low_gpu()


class WM_OT_safe_gpu(Operator):
    bl_idname = 'wm.safe_gpu'
    bl_label = 'Safe GPU Performance'
    bl_options = {'REGISTER'}
    enabled: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        global ENABLED
        if context.mode != 'OBJECT':
            self.report({'WARNING'}, 'Switch to Object Mode before changing GPU settings')
            return {'CANCELLED'}
        if self.enabled:
            ENABLED = True
            apply_low_gpu()
        else:
            restore_view()
            ENABLED = False
        return {'FINISHED'}


class VIEW3D_MT_safe_gpu(Menu):
    bl_label = 'Safe GPU / Rig'
    def draw(self, context):
        op = self.layout.operator('wm.safe_gpu', text='Safe GPU ON (Object Mode)')
        op.enabled = True
        op = self.layout.operator('wm.safe_gpu', text='Restore View (Object Mode)')
        op.enabled = False
        self.layout.label(text='No Edit Mode timers or bone changes')
        self.layout.label(text='3-minute native Auto Save')


def menu_view(self, context):
    self.layout.menu('VIEW3D_MT_safe_gpu', text='Safe GPU / Rig')


def menu_file(self, context):
    self.layout.separator()
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator('wm.recover_auto_save', text='Recover Auto Save...')


def initialize_once():
    if hasattr(bpy.types, 'VIEW3D_MT_view'):
        bpy.types.VIEW3D_MT_view.append(menu_view)
    if hasattr(bpy.types, 'TOPBAR_MT_file'):
        bpy.types.TOPBAR_MT_file.append(menu_file)
    apply_low_gpu()
    return None


def register():
    bpy.utils.register_class(WM_OT_safe_gpu)
    bpy.utils.register_class(VIEW3D_MT_safe_gpu)
    bpy.app.handlers.load_pre.append(on_load_pre)
    bpy.app.handlers.load_post.append(on_load_post)
    configure_autosave()
    if not bpy.app.background:
        bpy.app.timers.register(initialize_once, first_interval=1.0)


def unregister():
    if bpy.app.timers.is_registered(initialize_once):
        bpy.app.timers.unregister(initialize_once)
    if bpy.context.mode == 'OBJECT':
        restore_view()
    for funcs, cb in ((bpy.app.handlers.load_pre, on_load_pre),
                      (bpy.app.handlers.load_post, on_load_post)):
        if cb in funcs:
            funcs.remove(cb)
    for parent_name, cb in (('VIEW3D_MT_view', menu_view),
                            ('TOPBAR_MT_file', menu_file)):
        parent = getattr(bpy.types, parent_name, None)
        if parent:
            try:
                parent.remove(cb)
            except (ValueError, RuntimeError):
                pass
    bpy.utils.unregister_class(VIEW3D_MT_safe_gpu)
    bpy.utils.unregister_class(WM_OT_safe_gpu)
