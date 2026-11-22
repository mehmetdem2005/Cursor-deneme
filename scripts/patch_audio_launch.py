#!/usr/bin/env python3
"""Inject a no-audio native launch flag BEFORE NativeActivity starts Blender.

Android-alpha-4 source reads <internalDataPath>/blender_args.txt into argv.
Preserves an existing custom args file and never alters Blender project data.
"""
from pathlib import Path
import sys

CALL = "    invoke-direct {p0}, Lorg/blender/blender/BlenderActivity;->initSafeAudioArgs()V"
SUPER = "    invoke-super {p0, p1}, Landroid/app/NativeActivity;->onCreate(Landroid/os/Bundle;)V"
METHOD = r"""
.method private initSafeAudioArgs()V
    .locals 5
    :try_start_safesound
    invoke-virtual {p0}, Lorg/blender/blender/BlenderActivity;->getFilesDir()Ljava/io/File;
    move-result-object v0
    new-instance v1, Ljava/io/File;
    const-string v2, "blender_args.txt"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->exists()Z
    move-result v2
    if-nez v2, :try_end_safesound
    new-instance v3, Ljava/io/FileOutputStream;
    invoke-direct {v3, v1}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V
    const-string v4, "-noaudio\n"
    invoke-virtual {v4}, Ljava/lang/String;->getBytes()[B
    move-result-object v4
    invoke-virtual {v3, v4}, Ljava/io/FileOutputStream;->write([B)V
    invoke-virtual {v3}, Ljava/io/FileOutputStream;->close()V
    :try_end_safesound
    goto :safesound_end
    :catch_safesound
    move-exception v0
    const-string v1, "BlenderSafeAudio"
    const-string v2, "Audio-off startup file unavailable"
    invoke-static {v1, v2, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    :safesound_end
    return-void
    .catch Ljava/lang/Exception; {:try_start_safesound .. :try_end_safesound} :catch_safesound
.end method
"""

def inject(s):
    if "initSafeAudioArgs()V" in s or s.count(SUPER) != 1:
        raise ValueError("Unexpected BlenderActivity or double injection")
    if s.count(".method protected onCreate(Landroid/os/Bundle;)V") != 1:
        raise ValueError("Expected original onCreate")
    if "publishLaunchFile(Landroid/content/Intent;)V" not in s.split(SUPER,1)[0]:
        raise ValueError("Upstream startup order changed")
    return s.replace(SUPER, CALL+"\n"+SUPER, 1)+"\n"+METHOD

def apply(decoded):
    entries=list(Path(decoded).glob("smali*/org/blender/blender/BlenderActivity.smali"))
    if len(entries)!=1:
        raise ValueError("Missing or duplicate BlenderActivity smali")
    p=entries[0]
    p.write_text(inject(p.read_text()), encoding="utf-8")
    return p

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_audio_launch.py decoded-dir")
    print("Installed native safe audio startup:",apply(sys.argv[1]))
