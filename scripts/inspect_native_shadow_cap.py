#!/usr/bin/env python3
"""Read-only AArch64 inspection of libblender.so (no patches, no APK)."""
from pathlib import Path
import io
import re
import sys
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

def main(path):
    blob=Path(path).read_bytes()
    e=ELFFile(io.BytesIO(blob))
    assert e["e_machine"]=="EM_AARCH64"
    print("ELF bytes",len(blob),"sections",e.num_sections())
    ds=e.get_section_by_name(".dynsym")
    for sec in [e.get_section_by_name(".symtab"),ds]:
        if sec is None:
            print("No static symbols")
            continue
        a=[(s.name,int(s["st_value"]),int(s["st_size"])) for s in sec.iter_symbols()
           if re.search("shadow|sysconf|preview|eevee",s.name,re.I)]
        print("Matched symbols",len(a))
        print("\n".join(repr(x) for x in a[:100]))
    code=e.get_section_by_name(".text")
    print("TEXT base/size",hex(code["sh_addr"]),code["sh_size"])
    dyn={s.name:int(s["st_value"]) for s in ds.iter_symbols()}
    for x in ["sysconf","__system_property_get"]:
        print("IMPORT",x,dyn.get(x))
    for word in [b"shadow_pool_size", b"Could not allocate shadow atlas",
                 b"sysconf", b"EEVEE"]:
        print("ASCII",word.decode(),blob.find(word))
    plt=e.get_section_by_name(".plt")
    print("PLT",None if plt is None else (hex(plt["sh_addr"]),plt["sh_size"]))
    cap=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    cap.detail=False
    if plt is not None:
        print("PLT SAMPLE")
        for i in list(cap.disasm(plt.data()[:384],plt["sh_addr"]))[:45]:
            print(hex(i.address),i.mnemonic,i.op_str)

if __name__=="__main__":
    main(sys.argv[1])
