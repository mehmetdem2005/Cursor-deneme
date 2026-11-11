#!/usr/bin/env python3
"""Rename exactly two pinned Blender Android dynamic imports for a private shim."""
from io import BytesIO
from pathlib import Path
import struct
import sys
from elftools.elf.elffile import ELFFile

OLD = b"__system_property_get"
NEW = b"blender_renderdiv_get"
POLL_OLD = b"ALooper_pollOnce"
POLL_NEW = b"blender_pollOnce"
IMPORTS = ((OLD, NEW), (POLL_OLD, POLL_NEW))


def rewrite(blob: bytearray) -> int:
    elf = ELFFile(BytesIO(blob))
    if elf.elfclass != 64 or not elf.little_endian or elf["e_machine"] != "EM_AARCH64":
        raise ValueError("Expected little-endian ELF64 AArch64")
    syms = elf.get_section_by_name(".dynsym")
    strings = elf.get_section_by_name(".dynstr")
    versions = elf.get_section_by_name(".gnu.version")
    if any(x is None for x in (syms, strings, versions)):
        raise ValueError("Missing ELF dynamic sections")
    first_idx = -1
    for old, new in IMPORTS:
        if len(old) != len(new):
            raise ValueError("Import name widths differ")
        matches = [(i, s) for i, s in enumerate(syms.iter_symbols()) if s.name == old.decode()]
        if len(matches) != 1:
            raise ValueError(f"Expected one import of {old!r}, found {len(matches)}")
        idx, symbol = matches[0]
        if first_idx == -1:
            first_idx = idx
        if symbol["st_shndx"] != "SHN_UNDEF":
            raise ValueError("Expected imported undefined symbol")
        offset = strings["sh_offset"] + symbol["st_name"]
        if blob[offset:offset + len(old) + 1] != old + b"\x00":
            raise ValueError("Unexpected ELF dynstr bytes")
        version_offset = versions["sh_offset"] + idx * 2
        version = struct.unpack_from("<H", blob, version_offset)[0] & 0x7FFF
        if version == 0:
            raise ValueError("Local-only symbol; stop")
        blob[offset:offset + len(old)] = new
        struct.pack_into("<H", blob, version_offset, 1)
    return first_idx


def patch(path: Path):
    binary = bytearray(path.read_bytes())
    rewrite(binary)
    with ELFFile(BytesIO(binary)) as elf:
        symbols = list(elf.get_section_by_name(".dynsym").iter_symbols())
        for old, new in IMPORTS:
            if sum(s.name == new.decode() and s["st_shndx"] == "SHN_UNDEF"
                   for s in symbols) != 1 or any(s.name == old.decode() for s in symbols):
                raise ValueError(f"Failed to verify rewritten import {new!r}")
    path.write_bytes(binary)
    print("Rewired renderdiv and Android zero-timeout poll imports to private shim")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_blender_elf.py libblender.so")
    patch(Path(sys.argv[1]))
