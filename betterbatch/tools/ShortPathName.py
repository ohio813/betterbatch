import sys
import ctypes

GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW

long_path = unicode(" ".join(sys.argv[1:]))
long_path = long_path.strip('"')

short_buf = ctypes.create_unicode_buffer(len(long_path)+1)

ret = GetShortPathName(long_path, short_buf, len(long_path)+1)

if not ret:
    print "failed to get short path for '%s'"% long_path
    sys.exit(1)

print short_buf.value
