#!/usr/bin/env python3
"""Exact-match native source patch, for future source rebuild ONLY.

Does not modify the prebuilt Blender v33 libblender.so or Android GPU driver.
No APK is produced. This is a safety research candidate.
"""
from pathlib import Path
import argparse

PATH = "source/blender/draw/engines/eevee/eevee_shadow.cc"
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
NEW = """#ifdef __ANDROID__
  /* Android Mali GPU memory budget is not equal to installed system RAM.
   * Cap the EEVEE shadow atlas even on phones with more than 6GB RAM. */
  pool_size_mb = min_ii(pool_size_mb, 16);
#endif"""


def patch_source(content):
    if content.count(OLD) != 1:
        raise ValueError("Unsupported Blender source revision: no changes made")
    return content.replace(OLD, NEW)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    file = args.source_root / PATH
    before = file.read_text(encoding="utf-8")
    after = patch_source(before)
    if args.apply:
        file.write_text(after, encoding="utf-8")
        print("SOURCE PATCHED (native rebuild required)", file)
    else:
        print("DRY RUN: source patch compatible", file)


if __name__ == "__main__":
    main()
