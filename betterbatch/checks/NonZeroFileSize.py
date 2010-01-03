#NonZeroFileSize

import sys
import os
if os.stat(sys.argv[1]).st_size:
    sys.exit(0)

sys.exit(1)