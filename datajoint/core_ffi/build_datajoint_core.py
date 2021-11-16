from os import path
from cffi import FFI
import cffi_config

ffi = FFI()

with open(cffi_config.header_file, 'r') as file:
    headers = file.read()
    ffi.cdef(headers)

dirname = path.dirname(__file__)
print(dirname)
ffi.set_source("datajoint.core-ffi._datajoint_core", None)

if __name__ == "__main__":
    ffi.compile()
