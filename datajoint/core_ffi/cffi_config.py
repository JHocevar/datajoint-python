import sys
from os import path

prefix = {'win32': ''}.get(sys.platform, 'lib')
extension = {'darwin': '.dylib', 'win32': '.dll'}.get(sys.platform, '.so')
dirname = path.dirname(__file__)
coreName = 'datajoint_core_ffi_c'
library_file = path.join(dirname + '/core/' + prefix + coreName + extension)
header_file = path.join(dirname + '/core/' + coreName + '.h')
