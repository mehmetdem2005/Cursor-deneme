#!/usr/bin/env python3
"""Redirect Blender's imported Android system property getter to a local hook.

A user APK cannot set system property debug.blender.renderdiv. We preserve all
other property queries and patch only the dynamic symbol import in pinned ELF.
"""
from io import BytesIO
from pathlib import Path
import struct
import sys
from elftools.elf.elffile import ELFFile

OLD = b"__system_property_get"
NEW = b"blender_renderdiv_get"


def rewrite(blob: bytearray) -> int:
    if len(OLD) != len(NEW):
        raise ValueError("replacement symbol length is not identical")
    elf = ELFFile(BytesIO(blob))
    if elf.elfclass != 64 or not elf.little_endian or elf["e_machine"] != "EM_AARCH64":
        raise ValueError("Expected ELF64 little-endian arm64")
    symtab = elf.get_section_by_name(".dynsym")
    strtab = elf.get_section_by_name(".dynstr")
    versions = elf.get_section_by_name(".gnu.version")
    if any(s is None for s in (symtab, strtab, versions)):
        raise ValueError("Missing required dynamic section")
    matches = [(i, sym) for i, sym in enumerate(symtab.iter_symbols()) if sym.name == OLD.decode()]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one native property import, found {len(matches)}")
    idx, symbol = matches[0]
    if symbol["st_shndx"] != "SHN_UNDEF":
        raise ValueError("System property symbol was not an import")
    offset = strtab["sh_offset"] + symbol["st_name"]
    if blob[offset:offset + len(OLD) + 1] != OLD + b"\x00":
        raise ValueError("Unexpected symbol string bytes")
    v_off = versions["sh_offset"] + 2 * idx
    prev = struct.unpack_from("<H", blob, v_off)[0]
    if prev < 2:
        raise ValueError(f"Expected versioned libc symbol, found {prev}")
    blob[offset:offset + len(OLD)] = NEW
    struct.pack_into("<H", blob, v_off, 1)  # VER_NDX_GLOBAL instead of @LIBC
    return idx


def patch(path: Path):
    blob = bytearray(path.read_bytes())
    idx = rewrite(blob)
    path.write_bytes(blob)
    with ELFFile(BytesIO(blob)) as elf:
        sym = elf.get_section_by_name(".dynsym").get_symbol(idx)
        if sym.name != NEW.decode():
            raise ValueError("Failed to re-read patched dynamic symbol")
    print(f"Redirected Blender Android property import at ELF dynamic symbol {idx}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_blender_elf.py libblender.so")
    patch(Path(sys.argv[1]))
