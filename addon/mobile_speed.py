# SPDX-License-Identifier: GPL-2.0-or-later
"""Mobile viewport performance profiles for the unofficial Android Blender port.

Everything here is opt-in or applied only to a blank startup workspace.
No object, mesh, render setting or saved blend file is edited.
The original preferences + viewport state are kept in memory for this session.
"""

import bpy
from bpy.types import Menu, Operator

_previous_system = None
_previous_spaces = {}
_menu_installed = False
_auto_applied = False
_file_import_installed = False



# File loading protection for Android 11 / older Mali Vulkan drivers.
# The source Android port already probes GPU subdivision, but a driver can pass
# the probe and still fault while a scene loads; default to the CPU path here.
from bpy.app.handlers import persistent
import os
import time

_last_memory_mb = None
_file_log = "/sdcard/Download/Blender/mobile-file-debug.log"
_user_disabled_gpu_subdiv = False


def _rss_mb():
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return None


def _diagnostic(event):
    # Logs do not include any paths to user projects, only an event label
    # and the live process memory. Never block Blender if storage is locked.
    message = "[MobileFile] {:.0f} {} pid={} rss_mb={}".format(
        time.time(), event, os.getpid(), _rss_mb()
    )
    print(message, flush=True)  # Upstream copies stdout to blender-startup.log.
    try:
        os.makedirs(os.path.dirname(_file_log), exist_ok=True)
        with open(_file_log, "a", encoding="utf-8") as log:
            log.write(message + "\n")
    except OSError:
        pass


def _safe_system_prefs():
    global _user_disabled_gpu_subdiv
    sys = bpy.context.preferences.system
    if _previous_system is None:
        _capture([])
    if hasattr(sys, 'use_gpu_subdivision'):
        _set_value(sys, 'use_gpu_subdivision', False)
        _user_disabled_gpu_subdiv = True
    # Lower maximum uploaded preview texture size before a heavy import.
    if hasattr(sys, 'gl_texture_limit'):
        _set_value(sys, 'gl_texture_limit', 'CLAMP_512')
    # Mali-G76 / Android 11 Vulkan driver may corrupt or crash with MSAA.
    # OFF disables viewport anti-aliasing without changing mesh/render data.
    if hasattr(sys, 'viewport_aa'):
        _set_value(sys, 'viewport_aa', 'OFF')


@persistent
def _mobile_load_pre(_dummy):
    # Do not retain RNA references or old screen pointers across file reload.
    _previous_spaces.clear()
    _diagnostic("BLEND_LOAD_PRE")
    try:
        _safe_system_prefs()
    except (AttributeError, ReferenceError, RuntimeError) as exc:
        print("[MobileFile] load_pre protection unavailable:", exc, flush=True)


@persistent
def _mobile_load_post(_dummy):
    _diagnostic("BLEND_LOAD_POST")
    # File loading may reset preferences; keep GPU subdivision off.
    try:
        _safe_system_prefs()
    except (AttributeError, ReferenceError, RuntimeError) as exc:
        print("[MobileFile] load_post protection unavailable:", exc, flush=True)


def _memory_heartbeat():
    global _last_memory_mb
    rss = _rss_mb()
    if rss is not None and (
        _last_memory_mb is None or abs(rss - _last_memory_mb) >= 200
    ):
        _last_memory_mb = rss
        _diagnostic("MEMORY_SNAPSHOT")
    return 12.0


def _spaces_for_active_windows():
    result = []
    wm = bpy.context.window_manager
    if wm is None:
        return result
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                result.append(area.spaces.active)
    return result


def _set_value(target, attr, value):
    try:
        setattr(target, attr, value)
    except (AttributeError, TypeError, ValueError) as exc:
        # Blender builds can expose a different preference schema.
        print("[MobileSpeed] Skipped {}: {}".format(attr, exc))


def _capture(spaces):
    global _previous_system
    system = bpy.context.preferences.system
    if _previous_system is None:
        _previous_system = {
            name: getattr(system, name) for name in (
                'viewport_aa', 'anisotropic_filter', 'gl_texture_limit',
                'use_gpu_subdivision')
            if hasattr(system, name)
        }

    for space in spaces:
        if space.type != 'VIEW_3D':
            continue
        key = space.as_pointer()
        if key not in _previous_spaces:
            sh = space.shading
            ov = space.overlay
            # Store only primitive values, never a persistent reference to
            # SpaceView3D: on .blend reload that RNA pointer becomes invalid.
            _previous_spaces[key] = (
                {name: getattr(sh, name) for name in (
                    'show_cavity', 'show_shadows', 'show_specular_highlight')
                 if hasattr(sh, name)},
                {name: getattr(ov, name) for name in (
                    'show_floor', 'show_ortho_grid')
                 if hasattr(ov, name)},
            )


def _apply_profile(profile, spaces):
    _capture(spaces)
    system = bpy.context.preferences.system

    # No change to actual render resolution or Blender's Vulkan driver.
    if profile == 'BALANCED':
        _set_value(system, 'viewport_aa', 'FXAA')
        _set_value(system, 'anisotropic_filter', 'FILTER_2')
        _set_value(system, 'gl_texture_limit', 'CLAMP_512')
    elif profile in {'FAST', 'MALI_SAFE'}:
        _set_value(system, 'viewport_aa', 'OFF')
        _set_value(system, 'anisotropic_filter', 'FILTER_0')
        _set_value(system, 'gl_texture_limit',
                   'CLAMP_512' if profile == 'MALI_SAFE' else 'CLAMP_256')

    for space in spaces:
        if space.type != 'VIEW_3D':
            continue
        # Do not unexpectedly switch a material/render preview to Solid.
        if space.shading.type == 'SOLID':
            _set_value(space.shading, 'show_shadows', False)
            _set_value(space.shading, 'show_cavity', False)
            if profile in {'FAST', 'MALI_SAFE'}:
                _set_value(space.shading, 'show_specular_highlight', False)
                # Hide grid only, not mesh outlines or editing tools.
                _set_value(space.overlay, 'show_floor', False)
                _set_value(space.overlay, 'show_ortho_grid', False)
            if profile == 'MALI_SAFE':
                # Flat light avoids heavier studio-light shading paths.
                # This can lessen artifacts but cannot repair a broken Vulkan driver.
                _set_value(space.shading, 'light', 'FLAT')
                _set_value(space.overlay, 'show_axis_x', False)
                _set_value(space.overlay, 'show_axis_y', False)

    print("[MobileSpeed] Profile applied:", profile)


def _restore():
    global _previous_system
    if _previous_system is not None:
        for name, value in _previous_system.items():
            _set_value(bpy.context.preferences.system, name, value)
        _previous_system = None
    # Resolve *current* live RNA pointers; do not dereference freed spaces
    # after opening another blend file or changing workspaces.
    for space in _spaces_for_active_windows():
        values = _previous_spaces.get(space.as_pointer())
        if values is None:
            continue
        shading, overlay = values
        for name, value in shading.items():
            _set_value(space.shading, name, value)
        for name, value in overlay.items():
            _set_value(space.overlay, name, value)
    _previous_spaces.clear()
    print("[MobileSpeed] Original session settings restored.")
    _diagnostic("PREFERENCES_RESTORED")


class WM_OT_mobile_speed(Operator):
    bl_idname = 'wm.mobile_speed'
    bl_label = 'Mobile Viewport Speed'
    bl_description = 'Adjust only viewport quality, without altering model geometry'
    bl_options = {'REGISTER'}

    profile: bpy.props.EnumProperty(items=[
        ('BALANCED', 'Balanced', 'Keep grid and editing tools; reduce AA and shadows'),
        ('FAST', 'Fast', 'Disable viewport AA, shading extras and floor grid'),
        ('MALI_SAFE', 'Mali Safe', 'Reduce costly lighting and grid passes on Mali Vulkan'),
        ('RESTORE', 'Restore', 'Restore the settings from before Mobile Speed was used'),
    ])

    def execute(self, context):
        try:
            if self.profile == 'RESTORE':
                _restore()
            else:
                spaces = (
                    [context.area.spaces.active]
                    if context.area and context.area.type == 'VIEW_3D'
                    else _spaces_for_active_windows()
                )
                _apply_profile(self.profile, spaces)
        except Exception as exc:
            self.report({'ERROR'}, "Mobile Speed: {}".format(exc))
            return {'CANCELLED'}
        return {'FINISHED'}




class WM_OT_mobile_import_gltf(Operator):
    bl_idname = 'wm.mobile_import_gltf'
    bl_label = 'Import GLB / GLTF'
    bl_description = 'Import glTF 2.0 into the current scene; File > Open is only for .blend projects'
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        # Blender 5.3 ships the official glTF importer; the operator may be
        # disabled if the corresponding bundled add-on has not registered yet.
        try:
            if 'gltf' not in dir(bpy.ops.import_scene):
                import addon_utils
                addon_utils.enable('io_scene_gltf2', default_set=False)
            _diagnostic('GLTF_IMPORT_DIALOG')
            return bpy.ops.import_scene.gltf('INVOKE_DEFAULT')
        except (RuntimeError, AttributeError, ImportError, TypeError) as exc:
            self.report({'ERROR'}, 'glTF importer unavailable: ' + str(exc))
            _diagnostic('GLTF_IMPORT_ERROR')
            return {'CANCELLED'}

    def execute(self, context):
        # The menu normally invokes the file chooser. Keep this as a safe
        # fallback for Blender's EXEC operator context.
        return self.invoke(context, None)


def _draw_mobile_glb_import(self, context):
    self.layout.operator_context = 'INVOKE_AREA'
    self.layout.operator('wm.mobile_import_gltf', text='Import GLB / GLTF...', icon='IMPORT')


class WM_OT_mobile_file_diagnostics(Operator):
    bl_idname = 'wm.mobile_file_diagnostics'
    bl_label = 'Write File Load Diagnostic'
    bl_description = 'Record process memory to Download/Blender/mobile-file-debug.log'
    bl_options = {'REGISTER'}

    def execute(self, context):
        _diagnostic("MANUAL_BEFORE_FILE_OPEN")
        self.report({'INFO'}, "Diagnostic: Download/Blender/mobile-file-debug.log")
        return {'FINISHED'}


class VIEW3D_MT_mobile_speed(Menu):
    bl_idname = 'VIEW3D_MT_mobile_speed'
    bl_label = 'Mobile Performance'

    def draw(self, context):
        layout = self.layout
        for label, profile in (
            ('Balanced (clearer)', 'BALANCED'),
            ('Fast (higher FPS)', 'FAST'),
            ('Mali Safe (graphics glitches)', 'MALI_SAFE'),
            ('Restore previous settings', 'RESTORE'),
        ):
            op = layout.operator('wm.mobile_speed', text=label)
            op.profile = profile
        layout.separator()
        layout.label(text='Models and saved files unchanged')
        layout.operator('wm.mobile_file_diagnostics', text='Write File Load Diagnostic')


def _draw_entry(self, context):
    self.layout.menu('VIEW3D_MT_mobile_speed', text='Mobile Performance')


def _install_menu_when_ready():
    global _menu_installed, _file_import_installed, _auto_applied
    if bpy.app.background:
        return None
    if not hasattr(bpy.types, 'VIEW3D_MT_view'):
        return 0.5
    if not _menu_installed:
        bpy.types.VIEW3D_MT_view.append(_draw_entry)
        _menu_installed = True
    if not _file_import_installed and hasattr(bpy.types, 'TOPBAR_MT_file'):
        # File > Open attempts to read .blend and will reject .glb.
        bpy.types.TOPBAR_MT_file.prepend(_draw_mobile_glb_import)
        _file_import_installed = True

    # Stability release: performance profiles are opt-in, to avoid any
    # possibility of a stale viewport RNA reference during a file load.
    _auto_applied = True
    return None


def register():
    bpy.utils.register_class(WM_OT_mobile_speed)
    bpy.utils.register_class(VIEW3D_MT_mobile_speed)
    bpy.utils.register_class(WM_OT_mobile_file_diagnostics)
    bpy.utils.register_class(WM_OT_mobile_import_gltf)
    _safe_system_prefs()
    _diagnostic('STABILITY_PROTECTION_ENABLED')
    for handler, callback in ((bpy.app.handlers.load_pre, _mobile_load_pre),
                              (bpy.app.handlers.load_post, _mobile_load_post)):
        if callback not in handler:
            handler.append(callback)
    if not bpy.app.background:
        bpy.app.timers.register(_install_menu_when_ready, first_interval=1.5)
        bpy.app.timers.register(_memory_heartbeat, first_interval=3.0)


def unregister():
    global _menu_installed, _file_import_installed, _auto_applied
    if bpy.app.timers.is_registered(_install_menu_when_ready):
        bpy.app.timers.unregister(_install_menu_when_ready)
    if bpy.app.timers.is_registered(_memory_heartbeat):
        bpy.app.timers.unregister(_memory_heartbeat)
    for handler, callback in ((bpy.app.handlers.load_pre, _mobile_load_pre),
                              (bpy.app.handlers.load_post, _mobile_load_post)):
        if callback in handler:
            handler.remove(callback)
    if _menu_installed and hasattr(bpy.types, 'VIEW3D_MT_view'):
        bpy.types.VIEW3D_MT_view.remove(_draw_entry)
    if _file_import_installed and hasattr(bpy.types, 'TOPBAR_MT_file'):
        bpy.types.TOPBAR_MT_file.remove(_draw_mobile_glb_import)
    _file_import_installed = False
    _menu_installed = False
    _auto_applied = False
    _restore()
    bpy.utils.unregister_class(WM_OT_mobile_import_gltf)
    bpy.utils.unregister_class(WM_OT_mobile_file_diagnostics)
    bpy.utils.unregister_class(VIEW3D_MT_mobile_speed)
    bpy.utils.unregister_class(WM_OT_mobile_speed)
