#!/usr/bin/env python3
"""Exact v33 ARM64 EEVEE shadow pool memory-cap machine-code patch.

This is an experimental BINARY patch, NOT a source rebuild or graphics-driver fix.
It changes ONE AArch64 4-byte instruction in ShadowModule::init() from
'csel w9, w9, w23, gt' (undoes the 16 MB cap on RAM>=6GB)
to 'nop' (preserves the previously calculated min(scene_value,16)).
It refuses any binary where all EEVEE and sysconf callsite invariants
aren't exactly as expected. Only validated on pinned simfeo alpha-4 engine.
"""
import argparse
import io
import os
import struct
import tempfile
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

CODE_ADDR = 0x27D817C
NEIGHBORS = {
    0x27D811C: ("mov", "w0, #0x62"),
    0x27D8124: ("bl", None),
    0x27D812C: ("mov", "w0, #0x28"),
    0x27D8130: ("bl", None),
    0x27D813C: ("cmp", "w23, #0x10"),
    0x27D814C: ("csel", "w9, w23, w9, lt"),
    0x27D816C: ("ccmp", "x0, #0, #4, lo"),
    0x27D8170: ("ccmp", "x20, #0, #4, gt"),
    CODE_ADDR: ("csel", "w9, w9, w23, gt"),
    0x27D8188: ("sbfiz", "x9, x9, #0x14, #0x20"),
}
NOP = bytes.fromhex("1f2003d5")

def memory_offset(elf, address):
    sec = elf.get_section_by_name(".text")
    if sec is None or not (sec["sh_addr"] <= address < sec["sh_addr"] + sec["sh_size"]):
        raise ValueError("Target outside .text")
    return int(sec["sh_offset"])+address-int(sec["sh_addr"])

def decode_one(blob,address,offset):
    cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    insns=list(cs.disasm(blob[offset:offset+4],address))
    if len(insns)!=1 or insns[0].size!=4:
        raise ValueError(f"Not an instruction at 0x{address:x}")
    return insns[0].mnemonic,insns[0].op_str

def read_instructions(blob, post_patch=False):
    elf=ELFFile(io.BytesIO(blob))
    if elf.elfclass!=64 or elf["e_machine"]!="EM_AARCH64" or not elf.little_endian:
        raise ValueError("Require little-endian ARM64 ELF")
    if elf.get_section_by_name(".rela.plt") is None:
        raise ValueError("Missing imports")
    rel=elf.get_section_by_name(".rela.plt")
    dyn=elf.get_section_by_name(".dynsym")
    indices=[i for i,x in enumerate(rel.iter_relocations())
             if dyn.get_symbol(x["r_info_sym"]).name=="sysconf"]
    if len(indices)!=1:
        raise ValueError(f"Unexpected sysconf imports: {indices}")
    plt=elf.get_section_by_name(".plt")
    if plt is None:raise ValueError("Missing PLT")
    sysconf_plt=int(plt["sh_addr"])+32+16*indices[0]
    for addr,(mnemonic,operands) in NEIGHBORS.items():
        offset=memory_offset(elf,addr)
        actual=decode_one(blob,addr,offset)
        expected=("nop","") if post_patch and addr==CODE_ADDR else (mnemonic,operands)
        if actual[0]!=expected[0] or (expected[1] is not None and actual[1]!=expected[1]):
            raise ValueError(f"Unexpected native code at {addr:#x}: {actual!r}, expected {expected!r}")
        if addr in (0x27D8124,0x27D8130):
            if actual[1]!=f"#0x{sysconf_plt:x}":
                raise ValueError("Two sysconf calls don't target the one expected PLT import")
    return memory_offset(elf,CODE_ADDR)

def patch_blob(original):
    old_offset=read_instructions(original,False)
    old_word=original[old_offset:old_offset+4]
    if old_word==NOP:
        raise ValueError("Already patched")
    modified=bytearray(original)
    modified[old_offset:old_offset+4]=NOP
    result=bytes(modified)
    read_instructions(result,True)
    if result[:old_offset]!=original[:old_offset] or result[old_offset+4:]!=original[old_offset+4:]:
        raise AssertionError("More than one instruction changed")
    return result,old_word

def patch_file(path, verify=False):
    import hashlib
    path=Path(path)
    original=path.read_bytes()
    h=lambda blob:hashlib.sha256(blob).hexdigest()
    if verify:
        offset=read_instructions(original,True)
        print(f"Verified native EEVEE cap NOP at file offset 0x{offset:x}")
        print("sha256",h(original))
        return
    result,old=patch_blob(original)
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix=".blender-patched-",
                                     suffix=".so",delete=False) as fd:
        temp=Path(fd.name)
        fd.write(result)
    try:
        os.chmod(temp,path.stat().st_mode & 0o777)
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()
    print(f"ARM64 EEVEE CAP: 0x{CODE_ADDR:x}: {old.hex()} -> {NOP.hex()}")
    print("input SHA256",h(original))
    print("output SHA256",h(result))
    patch_file(path,verify=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("elf",type=Path)
    p.add_argument("--verify",action="store_true")
    args=p.parse_args()
    patch_file(args.elf,verify=args.verify)

if __name__=="__main__":main()
