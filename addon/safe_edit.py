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
    for space in all_viewports():
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




# Explicit one-shot Texture Paint preflight. Never changes Blender data or
# viewport settings from within a paint/edit/pose mode.
def all_viewports():
    spaces = []
    seen = set()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            try:
                space = area.spaces.active
                key = space.as_pointer()
                if key in seen:
                    continue
                seen.add(key)
                spaces.append(space)
            except (AttributeError, RuntimeError, ReferenceError):
                pass
    return spaces


def paint_capture(space):
    key = space.as_pointer()
    if key in PREVIOUS_VIEW:
        return
    sh, ov = space.shading, space.overlay
    shade_fields = ('type', 'light', 'color_type', 'show_shadows',
                    'show_cavity', 'show_specular_highlight')
    overlay_fields = ('show_floor', 'show_ortho_grid', 'show_axis_x',
                      'show_axis_y', 'show_relationship_lines',
                      'show_motion_paths')
    PREVIOUS_VIEW[key] = (
        {name: getattr(sh, name) for name in shade_fields if hasattr(sh, name)},
        {name: getattr(ov, name) for name in overlay_fields if hasattr(ov, name)},
    )


def apply_paint_profile(context, textured=False):
    """Prepare already-existing Blender workspaces, only in Object Mode.

    No automatic mode switching, image decode, UV editing, material editing,
    repeating timer or dependency-graph handler.
    """
    if not ENABLED or context.mode != 'OBJECT':
        return 0
    apply_low_gpu()
    count = 0
    for space in all_viewports():
        try:
            paint_capture(space)
            for name, val in (('type', 'SOLID'), ('light', 'FLAT'),
                              ('color_type', 'TEXTURE' if textured else 'MATERIAL'),
                              ('show_shadows', False), ('show_cavity', False),
                              ('show_specular_highlight', False)):
                set_value(space.shading, name, val)
            for name in ('show_floor', 'show_ortho_grid',
                         'show_axis_x', 'show_axis_y',
                         'show_relationship_lines', 'show_motion_paths'):
                set_value(space.overlay, name, False)
            count += 1
        except (AttributeError, RuntimeError, ReferenceError, ValueError):
            pass
    return count


def paint_image_summary():
    """Only metadata: avoid decoding images or copying pixel buffers."""
    count = 0
    largest = 0
    try:
        for image in bpy.data.images:
            count += 1
            if count > 256:
                break
            dimensions = image.size
            largest = max(largest, int(dimensions[0]), int(dimensions[1]))
    except (AttributeError, RuntimeError, ReferenceError, ValueError, TypeError):
        pass
    return count, largest


def paint_diagnostic(event, mode):
    """Best-effort marker. Never include filenames, paths, scene or mesh names."""
    import time
    import os
    try:
        rss_kib = -1
        try:
            with open('/proc/self/status', 'r', encoding='utf-8') as proc:
                for line in proc:
                    if line.startswith('VmRSS:'):
                        rss_kib = int(line.split()[1])
                        break
        except (OSError, ValueError, IndexError):
            pass
        count, largest = paint_image_summary()
        safe_event = event if event in {
            'PAINT_PREPARE_BEGIN', 'PAINT_PREPARE_OK',
            'PAINT_PREPARE_FAILED', 'SAFE_TEXTURE_PREVIEW',
            'MANUAL_DIAGNOSTIC'} else 'UNKNOWN'
        safe_mode = mode if mode in {
            'OBJECT', 'PAINT_TEXTURE', 'PAINT_WEIGHT', 'EDIT_MESH',
            'EDIT_ARMATURE', 'POSE', 'SCULPT'} else 'OTHER'
        marker = ('%.0f event=%s mode=%s rss_kib=%d images=%d max_edge=%d' %
                  (time.time(), safe_event, safe_mode, rss_kib, count, largest))
        print('[PaintGuard] ' + marker, flush=True)
        try:
            directory = '/sdcard/Download/Blender'
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, 'paint-guard.log'),
                      'a', encoding='utf-8') as logfile:
                logfile.write(marker + '\n')
        except (OSError, PermissionError):
            pass
    except Exception:
        # Do not let diagnostics crash Blender when storage/RNA is unavailable.
        pass


class WM_OT_prepare_texture_paint(Operator):
    bl_idname = 'wm.prepare_texture_paint'
    bl_label = 'Prepare Texture Paint (Safe)'
    bl_description = 'Prepare low-cost Solid viewport before entering Texture Paint'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        paint_diagnostic('PAINT_PREPARE_BEGIN', context.mode)
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            paint_diagnostic('PAINT_PREPARE_FAILED', context.mode)
            self.report({'WARNING'}, 'Select a mesh in Object Mode first')
            return {'CANCELLED'}
        count = apply_paint_profile(context, textured=False)
        if not count:
            paint_diagnostic('PAINT_PREPARE_FAILED', context.mode)
            self.report({'WARNING'}, 'No available 3D view to prepare')
            return {'CANCELLED'}
        paint_diagnostic('PAINT_PREPARE_OK', context.mode)
        try:
            has_uv = len(obj.data.uv_layers) > 0
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            has_uv = False
        _, largest = paint_image_summary()
        if not has_uv:
            self.report({'WARNING'}, 'Safe view ready; mesh has no UV map')
        elif largest >= 2048:
            self.report({'WARNING'}, 'Safe view ready; large images may exhaust memory')
        else:
            self.report({'INFO'}, 'Safe view ready. Enter Texture Paint manually')
        return {'FINISHED'}


class WM_OT_safe_texture_preview(Operator):
    bl_idname = 'wm.safe_texture_preview'
    bl_label = 'Safe Texture Preview (No EEVEE)'
    bl_description = 'Solid textured preview; opt-in GPU texture upload'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        if apply_paint_profile(context, textured=True) == 0:
            self.report({'WARNING'}, 'No 3D viewport or Safe GPU is off')
            return {'CANCELLED'}
        paint_diagnostic('SAFE_TEXTURE_PREVIEW', context.mode)
        self.report({'INFO'}, 'Solid texture preview prepared; no EEVEE')
        return {'FINISHED'}


class WM_OT_paint_diagnostics(Operator):
    bl_idname = 'wm.paint_diagnostics'
    bl_label = 'Write Paint Diagnostics'
    bl_description = 'Record safe event and memory metadata, not project content'
    bl_options = {'REGISTER'}

    def execute(self, context):
        paint_diagnostic('MANUAL_DIAGNOSTIC', context.mode)
        self.report({'INFO'}, 'Diagnostic: Download/Blender/paint-guard.log')
        return {'FINISHED'}

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
        self.layout.separator()
        self.layout.operator('wm.prepare_texture_paint', text='Prepare Texture Paint (Object Mode)')
        self.layout.operator('wm.safe_texture_preview', text='Safe Texture Preview (No EEVEE)')
        self.layout.operator('wm.paint_diagnostics', text='Write Paint Diagnostics')
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
    bpy.utils.register_class(WM_OT_prepare_texture_paint)
    bpy.utils.register_class(WM_OT_safe_texture_preview)
    bpy.utils.register_class(WM_OT_paint_diagnostics)
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
    bpy.utils.unregister_class(WM_OT_paint_diagnostics)
    bpy.utils.unregister_class(WM_OT_safe_texture_preview)
    bpy.utils.unregister_class(WM_OT_prepare_texture_paint)
    bpy.utils.unregister_class(VIEW3D_MT_safe_gpu)
    bpy.utils.unregister_class(WM_OT_safe_gpu)
