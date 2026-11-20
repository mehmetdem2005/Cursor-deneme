#!/usr/bin/env python3
"""Read-only locate sysconf PLT call sites in stripped Android ARM64 Blender ELF."""
from pathlib import Path
import io, struct, sys
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

def sign_extend(x,bits):
    return x-(1<<bits) if x & (1<<(bits-1)) else x

def main(filename):
    data=Path(filename).read_bytes()
    e=ELFFile(io.BytesIO(data))
    dyn=e.get_section_by_name(".dynsym")
    plt=e.get_section_by_name(".plt")
    text=e.get_section_by_name(".text")
    rela=e.get_section_by_name(".rela.plt")
    if not rela:
        raise ValueError("No .rela.plt")
    idxs=[i for i,x in enumerate(rela.iter_relocations())
          if dyn.get_symbol(x["r_info_sym"]).name=="sysconf"]
    print("sysconf reloc indexes:",idxs)
    if len(idxs)!=1: raise ValueError("Not one sysconf relocation")
    plt_addr=int(plt["sh_addr"])+32+idxs[0]*16
    print("sysconf PLT =",hex(plt_addr))
    blob=text.data()
    begin=int(text["sh_addr"])
    callsites=[]
    for off in range(0,len(blob)-4,4):
        ins=struct.unpack_from("<I",blob,off)[0]
        if ins & 0xfc000000 != 0x94000000:continue
        rel=sign_extend(ins & 0x03ffffff,26)*4
        addr=begin+off
        if addr+rel==plt_addr:
            callsites.append((addr,off))
    print("all direct sysconf callsites",len(callsites),[hex(a) for a,_ in callsites])
    cap=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    for idx,(addr,off) in enumerate(callsites):
        neighbors=[(addr2,off2) for addr2,off2 in callsites if 0<abs(addr2-addr)<400]
        print("\nCASE",idx,"address",hex(addr),"nearby",[(hex(x),x-addr) for x,_ in neighbors])
        start=max(0,off-88)
        end=min(len(blob),off+170)
        for i in cap.disasm(blob[start:end],begin+start):
            print(hex(i.address),i.mnemonic,i.op_str)
if __name__=="__main__":main(sys.argv[1])
