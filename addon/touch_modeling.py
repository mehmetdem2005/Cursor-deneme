# SPDX-License-Identifier: GPL-2.0-or-later
"""Opt-in Edit Mode diagnostics and native transform probes for Android touch.

Does not alter Blender's touch classifier or run a repeating timer.
An operator marked "probe" runs only after an explicit user tap.
"""
from collections import deque
import os
import time

import bpy
import bmesh
from bpy.types import Menu, Operator

_TRACE_ACTIVE = False
_TRACE = deque(maxlen=400)
_TRACE_START = 0.0
_LOG_DIR = "/sdcard/Download/Blender"


def _state(context):
    """Read-only, bounded selection and geometry state; never expose object names."""
    obj = context.active_object
    values = {"mode": context.mode, "mesh": bool(obj and obj.type == "MESH"),
              "v": -1, "e": -1, "f": -1, "energy": None}
    if context.mode != "EDIT_MESH" or not obj or obj.type != "MESH":
        return values
    try:
        mesh = bmesh.from_edit_mesh(obj.data)
        if len(mesh.verts) > 10000 or len(mesh.edges) > 15000 or len(mesh.faces) > 10000:
            return values  # do not stall low-memory phones for a diagnostic
        chosen = [v for v in mesh.verts if v.select]
        values["v"] = len(chosen)
        values["e"] = sum(1 for e in mesh.edges if e.select)
        values["f"] = sum(1 for f in mesh.faces if f.select)
        values["energy"] = round(sum(v.co.length_squared for v in chosen), 7)
    except (RuntimeError, ReferenceError, AttributeError, ValueError):
        pass
    return values


def _record(kind, context, event=None, extra=""):
    global _TRACE_START
    try:
        elapsed = round(time.monotonic() - _TRACE_START, 3) if _TRACE_START else 0
        st = _state(context) if kind != "move" else {"mode": context.mode}
        details = ""
        if event is not None:
            # No text events, object names, paths, or typed keys are recorded.
            details = " event=%s/%s screen=(%d,%d) region=(%d,%d)" % (
                event.type, event.value, event.mouse_x, event.mouse_y,
                event.mouse_region_x, event.mouse_region_y)
        _TRACE.append("%s +%.3fs %s %s%s %s" %
                      (kind, elapsed, context.mode, st, details, extra))
    except (AttributeError, TypeError, ValueError, RuntimeError):
        _TRACE.append("diagnostic_metadata_unavailable")


def _flush():
    rows = list(_TRACE)
    if not rows:
        return False
    header = "Touch/Edit trace (max 400 recent events, no project names)\n"
    payload = header + "\n".join(rows) + "\n"
    print("[EditProbe] " + payload, flush=True)
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        with open(os.path.join(_LOG_DIR, "edit-touch-trace.log"),
                  "a", encoding="utf-8") as fh:
            fh.write(payload)
        return True
    except (OSError, PermissionError):
        return False


def _viewport_region(context):
    area = context.area
    if area is None or area.type != "VIEW_3D":
        return None
    return next((r for r in area.regions if r.type == "WINDOW"), None)


def _selected(context):
    st = _state(context)
    return st["mode"] == "EDIT_MESH" and st["v"] > 0


class VIEW3D_OT_edit_probe_snapshot(Operator):
    bl_idname = "view3d.edit_probe_snapshot"
    bl_label = "Inspect Selection (Read Only)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        _record("snapshot", context)
        saved = _flush()
        s = _state(context)
        self.report({"INFO"}, "Edit selection: V=%s E=%s F=%s (log %s)" %
                    (s["v"], s["e"], s["f"], "saved" if saved else "console"))
        return {"FINISHED"}


class VIEW3D_OT_edit_probe_scale(Operator):
    """Directly call Blender's existing transform.resize, never scale mesh by hand."""
    bl_idname = "view3d.edit_probe_scale"
    bl_label = "Probe Native Numeric Scale"
    bl_options = {"REGISTER"}
    factor: bpy.props.FloatProperty(name="Factor", default=1.25, min=0.01, max=10.0)

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH" and _viewport_region(context) is not None

    def execute(self, context):
        if not _selected(context):
            self.report({"WARNING"}, "No selected mesh vertices: choose a vertex, edge, or face")
            _record("numeric_scale_no_selection", context)
            return {"CANCELLED"}
        region = _viewport_region(context)
        before = _state(context)
        try:
            with context.temp_override(area=context.area, region=region):
                result = bpy.ops.transform.resize("EXEC_DEFAULT",
                                                   value=(self.factor,) * 3)
        except (RuntimeError, TypeError, ValueError) as exc:
            _record("numeric_scale_exception", context, extra=type(exc).__name__)
            self.report({"ERROR"}, "Native transform failed: " + str(exc)[:100])
            return {"CANCELLED"}
        after = _state(context)
        changed = (before["energy"] is not None and
                   after["energy"] is not None and
                   abs(before["energy"] - after["energy"]) > 0.0000001)
        _record("numeric_scale", context,
                extra="factor=%g result=%s mesh_delta=%s" %
                (self.factor, sorted(result), changed))
        _flush()
        if "FINISHED" not in result or not changed:
            self.report({"WARNING"}, "Scale returned %s; mesh delta=%s, check trace" %
                        (sorted(result), changed))
            return {"CANCELLED"} if "FINISHED" not in result else {"FINISHED"}
        self.report({"INFO"}, "Selected mesh coordinates changed (factor %.2f)" %
                    self.factor)
        return {"FINISHED"}


class VIEW3D_OT_edit_probe_modal_scale(Operator):
    bl_idname = "view3d.edit_probe_modal_scale"
    bl_label = "Probe Native Interactive Scale"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH" and _viewport_region(context) is not None

    def invoke(self, context, event):
        if not _selected(context):
            self.report({"WARNING"}, "Select vertices, an edge or a face first")
            return {"CANCELLED"}
        _record("modal_scale_invoke", context, event)
        try:
            with context.temp_override(area=context.area, region=_viewport_region(context)):
                return bpy.ops.transform.resize("INVOKE_DEFAULT")
        except (RuntimeError, TypeError, ValueError) as exc:
            self.report({"ERROR"}, "Native modal Scale failed: " + str(exc)[:100])
            return {"CANCELLED"}


class VIEW3D_OT_edit_probe_trace(Operator):
    bl_idname = "view3d.edit_probe_trace"
    bl_label = "Start Edit Touch Trace"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        global _TRACE_ACTIVE, _TRACE_START
        if _TRACE_ACTIVE:
            self.report({"WARNING"}, "Trace already running; stop it from View menu")
            return {"CANCELLED"}
        _TRACE.clear()
        _TRACE_START = time.monotonic()
        _TRACE_ACTIVE = True
        _record("start", context, event)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if not _TRACE_ACTIVE:
            return {"FINISHED"}
        try:
            if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
                _record("move", context, event)
            elif event.type in {"LEFTMOUSE", "RIGHTMOUSE", "MIDDLEMOUSE"}:
                _record("button", context, event)
            elif event.type.startswith("EVT_TWEAK"):
                _record("tweak", context, event)
        except (RuntimeError, AttributeError):
            pass
        return {"PASS_THROUGH"}  # do not capture the event from Blender tools

    def cancel(self, context):
        global _TRACE_ACTIVE
        _TRACE_ACTIVE = False
        _record("cancel", context)
        _flush()


class VIEW3D_OT_edit_probe_trace_stop(Operator):
    bl_idname = "view3d.edit_probe_trace_stop"
    bl_label = "Stop and Save Edit Touch Trace"
    bl_options = {"REGISTER"}

    def execute(self, context):
        global _TRACE_ACTIVE
        _record("stop", context)
        _TRACE_ACTIVE = False
        saved = _flush()
        self.report({"INFO"}, "Trace %s: Download/Blender/edit-touch-trace.log" %
                    ("saved" if saved else "printed to console"))
        return {"FINISHED"}


class VIEW3D_MT_edit_probe(Menu):
    bl_label = "Edit Mode Touch Diagnostics"

    def draw(self, context):
        layout = self.layout
        layout.operator("view3d.edit_probe_snapshot", text="Inspect Selection / Log")
        layout.separator()
        op = layout.operator("view3d.edit_probe_scale",
                             text="Scale Selection 1.25x (Numeric Test)")
        op.factor = 1.25
        op = layout.operator("view3d.edit_probe_scale",
                             text="Scale Selection 0.80x (Numeric Test)")
        op.factor = 0.80
        layout.operator("view3d.edit_probe_modal_scale",
                        text="Start Blender's Native Interactive Scale")
        layout.separator()
        layout.operator("view3d.edit_probe_trace", text="Start Event Trace")
        layout.operator("view3d.edit_probe_trace_stop", text="Stop and Save Trace")
        layout.label(text="Trace is opt-in; no automatic mesh edits")


def _draw_view_menu(self, context):
    self.layout.menu("VIEW3D_MT_edit_probe", text="Edit Mode Touch Diagnostics")


def _add_menu_once():
    if not hasattr(bpy.types, "VIEW3D_MT_view"):
        return 0.5
    try:
        bpy.types.VIEW3D_MT_view.append(_draw_view_menu)
    except (AttributeError, RuntimeError, ValueError):
        pass
    return None


_CLASSES = (VIEW3D_OT_edit_probe_snapshot, VIEW3D_OT_edit_probe_scale,
            VIEW3D_OT_edit_probe_modal_scale, VIEW3D_OT_edit_probe_trace,
            VIEW3D_OT_edit_probe_trace_stop, VIEW3D_MT_edit_probe)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    if not bpy.app.background:
        bpy.app.timers.register(_add_menu_once, first_interval=1.5)


def unregister():
    global _TRACE_ACTIVE
    _TRACE_ACTIVE = False
    if bpy.app.timers.is_registered(_add_menu_once):
        bpy.app.timers.unregister(_add_menu_once)
    parent = getattr(bpy.types, "VIEW3D_MT_view", None)
    if parent:
        try:
            parent.remove(_draw_view_menu)
        except (AttributeError, RuntimeError, ValueError):
            pass
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
