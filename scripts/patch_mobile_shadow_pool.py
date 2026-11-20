#!/usr/bin/env python3
"""Conservative source-only Android EEVEE shadow-budget optimization.

Only supports the EXACT simfeo/blender android-alpha-4 source block.
It cannot patch the already-built libblender.so in Blender Lite v33.
A rebuilt native Blender engine is REQUIRED for any effect in an APK.
This does not address shader compilation, Vulkan synchronization or driver bugs.
"""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile

RELATIVE_PATH = "source/blender/draw/engines/eevee/eevee_shadow.cc"
SUPPORTED_LIMIT_MB = (16, 32, 64)

OLD = """#ifdef __ANDROID__
  /* The desktop default (512MB) is larger than the whole GPU budget on a phone or tablet, and
   * is allocated even for a small material preview. Cap it on memory constrained devices. */
  {
    const long pages = sysconf(_SC_PHYS_PAGES);
    const long page_size = sysconf(_SC_PAGE_SIZE);
    const uint64_t total_bytes = (pages > 0 && page_size > 0) ?
                                     uint64_t(pages) * uint64_t(page_size) :
                                     0;
    if (total_bytes != 0 && total_bytes < (6ull << 30)) {
      pool_size_mb = min_ii(pool_size_mb, 16);
    }
  }
#endif"""


def replacement(limit_mb=16):
    """Keep EEVEE functional while removing the unsafe physical-RAM heuristic."""
    if type(limit_mb) is not int or limit_mb not in SUPPORTED_LIMIT_MB:
        raise ValueError("Choose a supported shadow budget: 16, 32, or 64 MB")
    return (
        "#ifdef __ANDROID__\n"
        "  /* Android Vulkan shadow atlas cap, independent of total physical RAM.\n"
        "   * Physical RAM != available GPU memory; mobile EEVEE previews can\n"
        "   * allocate a desktop-sized shadow atlas even for a single sphere.\n"
        "   * Do not change stored scene.eevee settings to achieve this.\n"
        "   * Native GPU synchronization/driver bugs are not fixed here. */\n"
        f"  pool_size_mb = min_ii(pool_size_mb, {limit_mb});\n"
        "#endif"
    )


def patch_source(source, limit_mb=16):
    """Fail closed on unknown source revisions, repeat application or ambiguity."""
    new = replacement(limit_mb)
    if not isinstance(source, str):
        raise TypeError("Expected UTF-8 source text")
    if source.count(OLD) != 1 or new in source:
        raise ValueError("Not exact android-alpha-4 EEVEE source; refusing edit")
    if source.count("int pool_size_mb = scene.eevee.shadow_pool_size;") != 1:
        raise ValueError("Unexpected scene pool assignment; refusing edit")
    patched = source.replace(OLD, new, 1)
    if patched.count(new) != 1:
        raise AssertionError("Replacement postcondition failed")
    return patched


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def patch_file(root, limit_mb=16, apply=False):
    target = Path(root) / RELATIVE_PATH
    before = target.read_bytes()
    old = before.decode("utf-8")
    updated = patch_source(old, limit_mb).encode("utf-8")
    details = {
        "source": str(target),
        "limit_mb": limit_mb,
        "before_sha256": sha256(before),
        "after_sha256": sha256(updated),
        "changed": before != updated,
        "applied": False,
        "native_rebuild_required": True,
    }
    if not apply:
        return details

    backup = target.with_name(target.name + ".pre-mali-budget.bak")
    if backup.exists():
        raise FileExistsError("Backup already exists; refusing to overwrite: " + str(backup))
    # Create exact backup first. The original data remains recoverable even if
    # the new write fails. Do not move or modify the backup afterwards.
    with backup.open("xb") as out:
        out.write(before)
    os.chmod(backup, target.stat().st_mode & 0o777)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".mali-budget-",
                                         suffix=".cc", delete=False) as out:
            out.write(updated)
            tmp_name = out.name
        os.chmod(tmp_name, target.stat().st_mode & 0o777)
        os.replace(tmp_name, target)
        if target.read_bytes() != updated:
            raise OSError("Source write verification failed")
        details["applied"] = True
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blender_source_root", type=Path)
    parser.add_argument("--limit-mb", type=int, choices=SUPPORTED_LIMIT_MB,
                        default=16)
    parser.add_argument("--apply", action="store_true",
                        help="Write source change and preserve a .bak; otherwise dry-run")
    args = parser.parse_args()
    result = patch_file(args.blender_source_root, args.limit_mb, apply=args.apply)
    for key, value in result.items():
        print(f"{key}={value}")
    if not args.apply:
        print("DRY RUN: no Blender source changed; no APK generated.")
    else:
        print("ONLY native C++ source changed; libblender.so must be rebuilt.")


if __name__ == "__main__":
    main()
