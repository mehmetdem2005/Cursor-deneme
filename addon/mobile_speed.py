# SPDX-License-Identifier: GPL-2.0-or-later
"""Mobile viewport performance profiles for the unofficial Android Blender port.

Everything here is opt-in or applied only to a blank startup workspace.
No object, mesh, render setting or saved blend file is edited.
The original preferences + viewport state are kept in memory for this session.
"""

import bpy
from bpy.types import Menu, Operator
from bpy_extras.io_utils import ImportHelper

_previous_system = None
_previous_spaces = {}
_menu_installed = False
_auto_applied = False
_file_import_installed = False
_rig_enabled = False
_rig_saved_viewports = {}



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
    _rig_stop()
    _depth_stop()
    _bone_safe_stop()
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
                    'show_cavity', 'show_shadows', 'show_specular_highlight',
                    'light', 'type', 'color_type')
                 if hasattr(sh, name)},
                {name: getattr(ov, name) for name in (
                    'show_floor', 'show_ortho_grid',
                    'show_axis_x', 'show_axis_y')
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




def _mobile_scan_glb(filepath):
    """Bounded GLB/glTF metadata read: never reads mesh BIN/image content."""
    import json
    import os
    import struct

    suffix = os.path.splitext(filepath)[1].lower()
    if suffix not in {'.glb', '.gltf'} or not os.path.isfile(filepath):
        raise ValueError('Choose an existing GLB or glTF file')
    size = os.path.getsize(filepath)
    if size < 12 or size > 512 * 1024 * 1024:
        raise ValueError('Truncated file or file over 512 MiB')
    if suffix == '.glb':
        with open(filepath, 'rb') as src:
            hdr = src.read(12)
            if len(hdr) != 12:
                raise ValueError('Missing GLB header')
            magic, version, declared = struct.unpack('<4sII', hdr)
            if magic != b'glTF' or version != 2 or declared != size:
                raise ValueError('Incorrect GLB header, version or length')
            ch = src.read(8)
            if len(ch) != 8:
                raise ValueError('Missing GLB JSON chunk')
            n, tag = struct.unpack('<I4s', ch)
            if tag != b'JSON' or n == 0 or n > 16 * 1024 * 1024 or 20 + n > size:
                raise ValueError('Invalid or oversized GLB JSON chunk')
            raw = src.read(n)
            if len(raw) != n:
                raise ValueError('Incomplete GLB JSON')
            pos = 20 + n
            while pos < size:
                src.seek(pos)
                header = src.read(8)
                if len(header) != 8:
                    raise ValueError('Incomplete GLB chunk header')
                length, _tag = struct.unpack('<I4s', header)
                pos += 8 + length
                if pos > size:
                    raise ValueError('GLB chunk extends beyond file')
    else:
        if size > 16 * 1024 * 1024:
            raise ValueError('Oversized glTF JSON')
        with open(filepath, 'rb') as src:
            raw = src.read()

    def reject_constant(token):
        raise ValueError('Invalid numeric token ' + token)

    doc = json.loads(raw.decode('utf-8').strip('\x00 \r\n\t '),
                     parse_constant=reject_constant)
    if not isinstance(doc, dict) or not isinstance(doc.get('asset'), dict):
        raise ValueError('GLB has no glTF asset metadata')
    if doc['asset'].get('version') != '2.0':
        raise ValueError('Only glTF 2.0 is supported')

    def arr(key):
        value = doc.get(key, [])
        if not isinstance(value, list):
            raise ValueError('Invalid glTF array ' + key)
        return value

    meshes = arr('meshes')
    accessors = arr('accessors')
    buffers = arr('buffers')
    images = arr('images')
    views = arr('bufferViews')
    if len(accessors) > 200000 or len(meshes) > 100000:
        raise ValueError('Excessive GLB metadata')
    vertices = 0
    primitives = 0
    draco = False
    for mesh in meshes:
        if not isinstance(mesh, dict):
            raise ValueError('Invalid mesh structure')
        for part in mesh.get('primitives', []):
            primitives += 1
            attrs = part.get('attributes', {})
            if isinstance(attrs, dict) and isinstance(attrs.get('POSITION'), int):
                idx = attrs['POSITION']
                if idx < 0 or idx >= len(accessors):
                    raise ValueError('Invalid vertex accessor index')
                count = accessors[idx].get('count', 0)
                if not isinstance(count, int) or count < 0:
                    raise ValueError('Invalid vertex count')
                vertices += count
            draco |= 'KHR_draco_mesh_compression' in part.get('extensions', {})
    required = set(doc.get('extensionsRequired', []))
    used = set(doc.get('extensionsUsed', []))
    meshopt = any(
        'EXT_meshopt_compression' in v.get('extensions', {}) or
        'KHR_meshopt_compression' in v.get('extensions', {})
        for v in views if isinstance(v, dict))
    buffer_bytes = sum(max(0, int(b.get('byteLength', 0))) for b in buffers)
    basis = 'KHR_texture_basisu' in used or 'KHR_texture_basisu' in required
    basis |= any(
        im.get('mimeType') == 'image/ktx2' or
        str(im.get('uri', '')).lower().endswith('.ktx2')
        for im in images if isinstance(im, dict))
    return {
        'size': size, 'vertices': vertices, 'primitives': primitives,
        'images': len(images), 'buffer_bytes': buffer_bytes,
        'draco': draco or 'KHR_draco_mesh_compression' in required,
        'meshopt': meshopt or bool(required & {
            'EXT_meshopt_compression', 'KHR_meshopt_compression'}),
        'basis': basis,
        'heavy': size > 60 * 1024 * 1024 or vertices > 1000000 or
                 buffer_bytes > 256 * 1024 * 1024,
    }


class WM_OT_mobile_import_gltf(Operator, ImportHelper):
    bl_idname = 'wm.mobile_import_gltf'
    bl_label = 'Scan and Import GLB / GLTF'
    bl_description = 'Check file structure, compression and estimated complexity before Blender import'
    bl_options = {'REGISTER'}
    filename_ext = '.glb'
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default='*.glb;*.gltf', options={'HIDDEN'})
    allow_heavy: bpy.props.BoolProperty(
        name='Allow heavy GLB',
        description='Permit high-resource import that may crash Android',
        default=False)

    def draw(self, context):
        self.layout.prop(self, 'allow_heavy')

    def invoke(self, context, event):
        _diagnostic('GLB_FILE_SELECTION')
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        try:
            metadata = _mobile_scan_glb(self.filepath)
        except (ValueError, OSError, TypeError) as exc:
            self.report({'ERROR'}, 'GLB preflight: ' + str(exc)[:150])
            _diagnostic('GLB_INVALID')
            return {'CANCELLED'}

        print('[MobileGLB] preflight: bytes={} vertices={} parts={} images={} buffer={}'.format(
            metadata['size'], metadata['vertices'], metadata['primitives'],
            metadata['images'], metadata['buffer_bytes']), flush=True)
        try:
            import addon_utils
            addon_utils.enable('io_scene_gltf2', default_set=False)
            import io_scene_gltf2
            for feature, checker in (
                ('draco', 'is_draco_available'),
                ('meshopt', 'is_meshopt_available')):
                if metadata[feature] and not (
                    hasattr(io_scene_gltf2, checker) and getattr(io_scene_gltf2, checker)()):
                    self.report({'ERROR'}, feature + ' compressed meshes unsupported in this Lite APK')
                    _diagnostic('GLB_COMPRESSION_UNAVAILABLE')
                    return {'CANCELLED'}
        except (ImportError, RuntimeError, AttributeError) as exc:
            self.report({'ERROR'}, 'glTF add-on unavailable: ' + str(exc)[:130])
            _diagnostic('GLB_ADDON_MISSING')
            return {'CANCELLED'}

        if metadata['heavy'] and not self.allow_heavy:
            self.report({'ERROR'}, 'Heavy GLB: choose Allow heavy GLB to attempt import')
            _diagnostic('GLB_HEAVY_REJECTED')
            return {'CANCELLED'}
        if metadata['basis']:
            self.report({'WARNING'}, 'KTX2/BasisU textures may not be supported in this port')

        # Avoid costly EEVEE Vulkan compilation while new scene resources load.
        if _rig_enabled:
            _rig_stop()
        for space in _spaces_for_active_windows():
            _set_value(space.shading, 'type', 'SOLID')
            _set_value(space.shading, 'light', 'FLAT')
            _set_value(space.shading, 'show_shadows', False)
            _set_value(space.shading, 'show_cavity', False)

        _diagnostic('GLB_IMPORT_BEGIN')
        try:
            result = bpy.ops.import_scene.gltf(
                'EXEC_DEFAULT', filepath=self.filepath, import_unused_materials=False)
        except (Exception,) as exc:
            self.report({'ERROR'}, 'glTF import error: ' + str(exc)[:130])
            _diagnostic('GLB_IMPORT_ERROR')
            return {'CANCELLED'}
        _diagnostic('GLB_IMPORT_RETURN')
        return result


def _draw_mobile_glb_import(self, context):
    self.layout.operator_context = 'INVOKE_AREA'
    self.layout.operator('wm.mobile_import_gltf', text='Import GLB / GLTF...', icon='IMPORT')



# GPU-safe material inspection and rig/weight-paint tools.
# Only viewport display fields change; weights, bones and objects are untouched.
_RIG_SH = ('type', 'color_type', 'light', 'show_shadows',
           'show_cavity', 'show_specular_highlight')
_RIG_OV = ('show_floor', 'show_ortho_grid', 'show_relationship_lines',
           'show_motion_paths', 'show_wpaint_contours')


def _rig_restore():
    for space in _spaces_for_active_windows():
        state = _rig_saved_viewports.get(space.as_pointer())
        if state is None:
            continue
        a, b = state
        for name, value in a.items():
            _set_value(space.shading, name, value)
        for name, value in b.items():
            _set_value(space.overlay, name, value)
    _rig_saved_viewports.clear()


def _rig_apply():
    if bpy.context.mode not in {'POSE', 'PAINT_WEIGHT'}:
        _rig_restore()
        return
    for space in _spaces_for_active_windows():
        key = space.as_pointer()
        if key in _rig_saved_viewports:
            continue  # Never reconfigure every brush stroke/frame.
        sh, ov = space.shading, space.overlay
        _rig_saved_viewports[key] = (
            {n: getattr(sh, n) for n in _RIG_SH if hasattr(sh, n)},
            {n: getattr(ov, n) for n in _RIG_OV if hasattr(ov, n)},
        )
        for name, value in (
            ('type', 'SOLID'), ('color_type', 'MATERIAL'), ('light', 'FLAT'),
            ('show_shadows', False), ('show_cavity', False),
            ('show_specular_highlight', False),
        ):
            _set_value(sh, name, value)
        for name in _RIG_OV:
            _set_value(ov, name, False)
        # Keep weight ramp, armature bones, paint brushes and object outlines.


def _rig_tick():
    if not _rig_enabled:
        return None
    try:
        _rig_apply()
    except (RuntimeError, ReferenceError, AttributeError) as exc:
        print("[MobileRig] update skipped:", exc)
    return 0.40


def _rig_stop():
    global _rig_enabled
    _rig_enabled = False
    _rig_restore()


@persistent
def _rig_save_pre(_unused):
    if _rig_enabled:
        _rig_restore()


@persistent
def _rig_save_post(_unused):
    if _rig_enabled:
        _rig_apply()


class WM_OT_mobile_safe_texture(Operator):
    bl_idname = 'wm.mobile_safe_texture'
    bl_label = 'Safe Texture (Solid, no EEVEE)'
    bl_description = 'Display active UV image textures without unsafe EEVEE Material Preview'
    bl_options = {'REGISTER'}

    def execute(self, context):
        if _rig_enabled:
            _rig_stop()
        spaces = ([context.area.spaces.active]
                  if context.area and context.area.type == 'VIEW_3D'
                  else _spaces_for_active_windows())
        _capture(spaces)
        for space in spaces:
            for attr, val in (
                ('type', 'SOLID'), ('color_type', 'TEXTURE'),
                ('light', 'STUDIO'), ('show_shadows', False),
                ('show_cavity', False), ('show_specular_highlight', False),
            ):
                _set_value(space.shading, attr, val)
        self.report({'INFO'}, 'Safe texture view enabled. Material Preview may still crash.')
        return {'FINISHED'}


class WM_OT_mobile_rig_lite(Operator):
    bl_idname = 'wm.mobile_rig_lite'
    bl_label = 'Rig / Weight Paint Lite'
    bl_description = 'Use simple shading and minimal overlays for Pose/Weight Paint; preserve bones and weights'
    bl_options = {'REGISTER'}

    enabled: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        global _rig_enabled
        if not self.enabled:
            _rig_stop()
            self.report({'INFO'}, 'Rig Lite disabled and viewport restored')
            return {'FINISHED'}
        _rig_enabled = True
        try:
            _rig_apply()
            if not bpy.app.timers.is_registered(_rig_tick):
                bpy.app.timers.register(_rig_tick, first_interval=0.40)
        except Exception as exc:
            _rig_stop()
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Rig Lite enabled for Pose/Weight Paint')
        return {'FINISHED'}



# Read-only diagnostics for older Mali depth precision / coincident polygons.
_depth_safe_enabled = False
_depth_original = {}


def _depth_restore():
    for space in _spaces_for_active_windows():
        original = _depth_original.get(space.as_pointer())
        if original is not None:
            _set_value(space, 'clip_start', original[0])
            _set_value(space, 'clip_end', original[1])
    _depth_original.clear()


def _depth_apply():
    if not _depth_safe_enabled:
        return
    for space in _spaces_for_active_windows():
        key = space.as_pointer()
        if key not in _depth_original:
            _depth_original[key] = (space.clip_start, space.clip_end)
        # Opt-in depth-precision test. Nearby or distant objects may clip.
        _set_value(space, 'clip_start', 0.1)
        _set_value(space, 'clip_end', 100.0)


def _depth_stop():
    global _depth_safe_enabled
    _depth_safe_enabled = False
    _depth_restore()


@persistent
def _depth_save_pre(_unused):
    if _depth_safe_enabled:
        _depth_restore()


@persistent
def _depth_save_post(_unused):
    if _depth_safe_enabled:
        _depth_apply()


class WM_OT_mobile_depth_test(Operator):
    bl_idname = 'wm.mobile_depth_test'
    bl_label = 'Depth Precision Test'
    bl_description = 'Test stronger depth precision in 3D views; does not modify meshes'
    bl_options = {'REGISTER'}
    enable: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        global _depth_safe_enabled
        if self.enable:
            _depth_safe_enabled = True
            _depth_apply()
            _diagnostic('DEPTH_PRECISION_ON')
            self.report({'INFO'}, 'Depth test ON. View clip start 0.1, end 100.')
        else:
            _depth_stop()
            _diagnostic('DEPTH_PRECISION_OFF')
            self.report({'INFO'}, 'Original clipping restored.')
        return {'FINISHED'}


def _sample_overlapping_faces(mesh, max_faces=2500):
    """Bounded check of identical polygon vertices; no mutations."""
    count = len(mesh.polygons)
    if count == 0:
        return 0, 0, 0
    stride = max(1, (count + max_faces - 1) // max_faces)
    seen = set()
    found = 0
    checked = 0
    for idx in range(0, count, stride):
        poly = mesh.polygons[idx]
        if len(poly.vertices) < 3:
            continue
        signature = tuple(sorted(
            tuple(round(float(c), 5) for c in mesh.vertices[v].co)
            for v in poly.vertices))
        checked += 1
        if signature in seen:
            found += 1
        else:
            seen.add(signature)
        if checked >= max_faces:
            break
    return found, checked, count


class WM_OT_mobile_overlap_check(Operator):
    bl_idname = 'wm.mobile_overlap_check'
    bl_label = 'Check Coincident Faces'
    bl_description = 'Read-only sample of up to 2500 selected mesh polygons'
    bl_options = {'REGISTER'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, 'Select a mesh object first.')
            return {'CANCELLED'}
        try:
            found, checked, total = _sample_overlapping_faces(obj.data)
        except (RuntimeError, ReferenceError, IndexError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        _diagnostic('OVERLAP_FACES_{}_SAMPLED_{}_TOTAL_{}'.format(found, checked, total))
        self.report({'WARNING'} if found else {'INFO'},
                    '{} coincident faces in {} sampled of {} polygons; no edits'.format(
                        found, checked, total))
        return {'FINISHED'}



# Non-destructive armature draw-path isolation for Android 11 Mali Vulkan.
# This deliberately does NOT add, delete, parent, or evaluate any bones.
_bone_safe_mode = 'OFF'
_bone_safe_original = None
_bone_safe_last_count = None


def _bone_safe_armature(context):
    obj = context.active_object
    if obj is None:
        return None
    if obj.type == 'ARMATURE':
        return obj
    if obj.type == 'MESH':
        try:
            armature = obj.find_armature()
            return armature if armature and armature.type == 'ARMATURE' else None
        except (RuntimeError, ReferenceError):
            return None
    return None


def _bone_safe_capture(context):
    obj = _bone_safe_armature(context)
    if obj is None:
        raise RuntimeError('Select an armature, or its parented mesh, first')
    mesh_views = {}
    # A one-time scan only when user enables the optional isolation mode.
    # Bound all meshes together so no armature-linked part remains unexpectedly heavy.
    for child in context.view_layer.objects:
        if child.type != 'MESH':
            continue
        if child.parent == obj or any(
            mod.type == 'ARMATURE' and mod.object == obj
            for mod in child.modifiers
        ):
            mesh_views[child.name_full] = child.display_type
    arm = obj.data
    return {
        'object': obj.name_full,
        'armature_data': arm.name_full,
        'armature_display': arm.display_type,
        'bone_names': arm.show_names,
        'meshes': mesh_views,
    }


def _bone_safe_set(is_restore=False):
    original = _bone_safe_original
    if original is None:
        return
    arm = bpy.data.armatures.get(original['armature_data'])
    if arm is None:
        return
    if is_restore:
        _set_value(arm, 'display_type', original['armature_display'])
        _set_value(arm, 'show_names', original['bone_names'])
    else:
        # STICK uses a lightweight line/dot armature GPU draw pass.
        _set_value(arm, 'display_type', 'STICK')
        _set_value(arm, 'show_names', False)

    for name, old_display in original['meshes'].items():
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            continue
        if is_restore:
            _set_value(obj, 'display_type', old_display)
        elif _bone_safe_mode == 'ISOLATE':
            # Bounds allow bone editing while omitting the heavy mesh triangles.
            _set_value(obj, 'display_type', 'BOUNDS')


def _bone_safe_stop():
    global _bone_safe_mode, _bone_safe_original, _bone_safe_last_count
    if _bone_safe_original is not None:
        try:
            _bone_safe_set(is_restore=True)
        except (ReferenceError, RuntimeError, AttributeError) as exc:
            print('[MobileBones] Restore skipped:', exc)
    _bone_safe_original = None
    _bone_safe_mode = 'OFF'
    _bone_safe_last_count = None


def _bone_safe_count():
    if _bone_safe_original is None:
        return None
    arm_obj = bpy.data.objects.get(_bone_safe_original['object'])
    if arm_obj is None or arm_obj.type != 'ARMATURE':
        return None
    data = arm_obj.data
    # Access collection length only: never dereference active EditBone
    # pointers during native deletion/undo or cache them for later use.
    if arm_obj.mode == 'EDIT':
        return arm_obj.mode, len(data.edit_bones)
    return arm_obj.mode, len(data.bones)


def _bone_safe_watch():
    global _bone_safe_last_count
    if _bone_safe_mode == 'OFF':
        return None
    try:
        current = _bone_safe_count()
        if current is None:
            _diagnostic('ARMATURE_NOT_FOUND')
            _bone_safe_stop()
            return None
        if current != _bone_safe_last_count:
            _bone_safe_last_count = current
            mode, count = current
            _diagnostic('BONE_COUNT_{}_{}'.format(mode, count))
    except (ReferenceError, RuntimeError, AttributeError) as exc:
        print('[MobileBones] Count sample skipped:', exc)
    return 0.75


@persistent
def _bone_safe_save_pre(_unused):
    if _bone_safe_mode != 'OFF':
        _bone_safe_set(is_restore=True)


@persistent
def _bone_safe_save_post(_unused):
    if _bone_safe_mode != 'OFF':
        _bone_safe_set(is_restore=False)


class WM_OT_mobile_bone_safety(Operator):
    bl_idname = 'wm.mobile_bone_safety'
    bl_label = 'Bone Safety Test'
    bl_description = 'Temporarily simplify armature draw; optionally show bound meshes only as bounds'
    bl_options = {'REGISTER'}

    mode: bpy.props.EnumProperty(items=[
        ('STICK', 'Stick Bones', 'Draw bones as simple lines'),
        ('ISOLATE', 'Isolate Bone Drawing', 'Also show skinned meshes as bounding boxes'),
        ('OFF', 'Restore Original View', 'Restore original bone and mesh display'),
    ], default='STICK')

    def execute(self, context):
        global _bone_safe_mode, _bone_safe_original, _bone_safe_last_count
        if self.mode == 'OFF':
            _bone_safe_stop()
            _diagnostic('BONE_SAFE_OFF')
            self.report({'INFO'}, 'Bone Safety OFF; previous display restored')
            return {'FINISHED'}
        _bone_safe_stop()
        try:
            snapshot = _bone_safe_capture(context)
            _bone_safe_original = snapshot
            _bone_safe_mode = self.mode
            _bone_safe_set(is_restore=False)
            _bone_safe_last_count = None
            if not bpy.app.timers.is_registered(_bone_safe_watch):
                bpy.app.timers.register(_bone_safe_watch, first_interval=0.75)
            _diagnostic('BONE_SAFE_{}'.format(self.mode))
        except Exception as exc:
            _bone_safe_stop()
            self.report({'ERROR'}, 'Bone Safety unavailable: ' + str(exc)[:150])
            return {'CANCELLED'}
        self.report({'INFO'}, 'Bone Safety {} active; bones and weights unchanged'.format(self.mode))
        return {'FINISHED'}


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
        layout.operator('wm.mobile_safe_texture', text='Safe Texture (No EEVEE)', icon='TEXTURE')
        a = layout.operator('wm.mobile_rig_lite', text='Rig / Weight Paint Lite ON', icon='ARMATURE_DATA')
        a.enabled = True
        b = layout.operator('wm.mobile_rig_lite', text='Rig / Weight Paint Lite OFF', icon='CANCEL')
        b.enabled = False
        d_on = layout.operator('wm.mobile_depth_test', text='Depth Precision Test ON', icon='VIEW_PERSPECTIVE')
        d_on.enable = True
        d_off = layout.operator('wm.mobile_depth_test', text='Depth Precision Test OFF', icon='CANCEL')
        d_off.enable = False
        layout.operator('wm.mobile_overlap_check', text='Check Coincident Faces', icon='MESH_DATA')
        layout.separator()
        b1 = layout.operator('wm.mobile_bone_safety', text='Bone Safe: Stick (lightweight)', icon='ARMATURE_DATA')
        b1.mode = 'STICK'
        b2 = layout.operator('wm.mobile_bone_safety', text='Bone Safe: Isolate Mesh (bounds)', icon='BBOX')
        b2.mode = 'ISOLATE'
        b3 = layout.operator('wm.mobile_bone_safety', text='Bone Safe: OFF / Restore', icon='CANCEL')
        b3.mode = 'OFF'
        layout.label(text='Weights, bones and meshes unchanged')
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
    bpy.utils.register_class(WM_OT_mobile_safe_texture)
    bpy.utils.register_class(WM_OT_mobile_rig_lite)
    bpy.utils.register_class(WM_OT_mobile_depth_test)
    bpy.utils.register_class(WM_OT_mobile_overlap_check)
    bpy.utils.register_class(WM_OT_mobile_bone_safety)
    for handler, callback in ((bpy.app.handlers.save_pre, _bone_safe_save_pre),
                              (bpy.app.handlers.save_post, _bone_safe_save_post)):
        if callback not in handler:
            handler.append(callback)
    for handler, callback in ((bpy.app.handlers.save_pre, _depth_save_pre),
                              (bpy.app.handlers.save_post, _depth_save_post)):
        if callback not in handler:
            handler.append(callback)
    for handler, fn in ((bpy.app.handlers.save_pre, _rig_save_pre),
                        (bpy.app.handlers.save_post, _rig_save_post)):
        if fn not in handler:
            handler.append(fn)
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
    _rig_stop()
    _depth_stop()
    _bone_safe_stop()
    if bpy.app.timers.is_registered(_bone_safe_watch):
        bpy.app.timers.unregister(_bone_safe_watch)
    for handler, callback in ((bpy.app.handlers.save_pre, _bone_safe_save_pre),
                              (bpy.app.handlers.save_post, _bone_safe_save_post)):
        if callback in handler:
            handler.remove(callback)
    for handler, callback in ((bpy.app.handlers.save_pre, _depth_save_pre),
                              (bpy.app.handlers.save_post, _depth_save_post)):
        if callback in handler:
            handler.remove(callback)
    if bpy.app.timers.is_registered(_rig_tick):
        bpy.app.timers.unregister(_rig_tick)
    for handler, fn in ((bpy.app.handlers.save_pre, _rig_save_pre),
                        (bpy.app.handlers.save_post, _rig_save_post)):
        if fn in handler:
            handler.remove(fn)
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
    bpy.utils.unregister_class(WM_OT_mobile_bone_safety)
    bpy.utils.unregister_class(WM_OT_mobile_overlap_check)
    bpy.utils.unregister_class(WM_OT_mobile_depth_test)
    bpy.utils.unregister_class(WM_OT_mobile_rig_lite)
    bpy.utils.unregister_class(WM_OT_mobile_safe_texture)
    bpy.utils.unregister_class(WM_OT_mobile_import_gltf)
    bpy.utils.unregister_class(WM_OT_mobile_file_diagnostics)
    bpy.utils.unregister_class(VIEW3D_MT_mobile_speed)
    bpy.utils.unregister_class(WM_OT_mobile_speed)
