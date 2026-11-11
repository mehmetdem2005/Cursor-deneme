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
                'viewport_aa', 'anisotropic_filter', 'gl_texture_limit')
            if hasattr(system, name)
        }

    for space in spaces:
        if space.type != 'VIEW_3D':
            continue
        key = space.as_pointer()
        if key not in _previous_spaces:
            sh = space.shading
            ov = space.overlay
            _previous_spaces[key] = (
                space,
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
        _set_value(system, 'gl_texture_limit', 'CLAMP_1024')
    elif profile == 'FAST':
        _set_value(system, 'viewport_aa', 'OFF')
        _set_value(system, 'anisotropic_filter', 'FILTER_0')
        _set_value(system, 'gl_texture_limit', 'CLAMP_512')

    for space in spaces:
        if space.type != 'VIEW_3D':
            continue
        # Do not unexpectedly switch a material/render preview to Solid.
        if space.shading.type == 'SOLID':
            _set_value(space.shading, 'show_shadows', False)
            _set_value(space.shading, 'show_cavity', False)
            if profile == 'FAST':
                _set_value(space.shading, 'show_specular_highlight', False)
                # Hide the background grid, not the outlines or editing tools.
                _set_value(space.overlay, 'show_floor', False)
                _set_value(space.overlay, 'show_ortho_grid', False)

    print("[MobileSpeed] Profile applied:", profile)


def _restore():
    global _previous_system
    if _previous_system is not None:
        for name, value in _previous_system.items():
            _set_value(bpy.context.preferences.system, name, value)
        _previous_system = None
    for key, (space, shading, overlay) in list(_previous_spaces.items()):
        try:
            for name, value in shading.items():
                _set_value(space.shading, name, value)
            for name, value in overlay.items():
                _set_value(space.overlay, name, value)
        except ReferenceError:
            print("[MobileSpeed] An earlier viewport was closed.")
    _previous_spaces.clear()
    print("[MobileSpeed] Original session settings restored.")


class WM_OT_mobile_speed(Operator):
    bl_idname = 'wm.mobile_speed'
    bl_label = 'Mobile Viewport Speed'
    bl_description = 'Adjust only viewport quality, without altering model geometry'
    bl_options = {'REGISTER', 'UNDO'}

    profile: bpy.props.EnumProperty(items=[
        ('BALANCED', 'Balanced', 'Keep grid and editing tools; reduce AA and shadows'),
        ('FAST', 'Fast', 'Disable viewport AA, shading extras and floor grid'),
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


class VIEW3D_MT_mobile_speed(Menu):
    bl_idname = 'VIEW3D_MT_mobile_speed'
    bl_label = 'Mobile Performance'

    def draw(self, context):
        layout = self.layout
        for label, profile in (
            ('Balanced (clearer)', 'BALANCED'),
            ('Fast (higher FPS)', 'FAST'),
            ('Restore previous settings', 'RESTORE'),
        ):
            op = layout.operator('wm.mobile_speed', text=label)
            op.profile = profile
        layout.separator()
        layout.label(text='Models and saved files unchanged')


def _draw_entry(self, context):
    self.layout.menu('VIEW3D_MT_mobile_speed', text='Mobile Performance')


def _install_menu_when_ready():
    global _menu_installed, _auto_applied
    if bpy.app.background:
        return None
    if not hasattr(bpy.types, 'VIEW3D_MT_view'):
        return 0.5
    if not _menu_installed:
        bpy.types.VIEW3D_MT_view.append(_draw_entry)
        _menu_installed = True

    # Do not modify loaded user projects, even if the user opened one immediately.
    if not _auto_applied:
        _auto_applied = True
        if not bpy.data.filepath:
            spaces = _spaces_for_active_windows()
            if spaces:
                try:
                    _apply_profile('BALANCED', spaces)
                except Exception as exc:
                    print("[MobileSpeed] Default profile skipped:", exc)
    return None


def register():
    bpy.utils.register_class(WM_OT_mobile_speed)
    bpy.utils.register_class(VIEW3D_MT_mobile_speed)
    if not bpy.app.background:
        bpy.app.timers.register(_install_menu_when_ready, first_interval=1.5)


def unregister():
    global _menu_installed, _auto_applied
    if bpy.app.timers.is_registered(_install_menu_when_ready):
        bpy.app.timers.unregister(_install_menu_when_ready)
    if _menu_installed and hasattr(bpy.types, 'VIEW3D_MT_view'):
        bpy.types.VIEW3D_MT_view.remove(_draw_entry)
    _menu_installed = False
    _auto_applied = False
    _restore()
    bpy.utils.unregister_class(VIEW3D_MT_mobile_speed)
    bpy.utils.unregister_class(WM_OT_mobile_speed)
