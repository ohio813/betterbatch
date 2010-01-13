"""Built in commands.

These commands are available as in commands

e.g. Run: dir /s
e.g. CountFiles:  <database_dir>\*.lpu 3  # ensure 3 LPU's
etc
"""
import operator
import os
import glob
import subprocess
import tempfile
import sys

RESULT_SUCCESS = 0
RESULT_FAILURE = 1

PUSH_DIRECTORY_LIST = []


def VerifyFileCount(file_pattern, count = None):
    """Verify that the file count is as specified

    filepattern is a glob for the files to count
    count is a specification for how many, it can be
    >=X, <=X, >X, <X, =X or just X (which is equivalent to =X) where X is any
    whole number.

    Returns RESULT_SUCCESS if the number of files match and
    returns RESULT_FAILURE and a message if the number does not match.
    """

    if not count:
        raise RuntimeError("You must specify a file count.")

    if isinstance(count, list):
        # strip all spaces from the count
        count = "".join(str(part) for part in count)
    else:
        count = str(count)

    count = count.strip()
    num_files = len(glob.glob(file_pattern))

    op = operator.eq
    desc = count

    if count.startswith(">="):
        op = operator.ge
        count = count[2:]

    elif count.startswith("<="):
        op = operator.le
        count = count[2:]

    elif count.startswith(">"):
        op = operator.gt
        count = count[1:]

    elif count.startswith("<"):
        op = operator.lt
        count = count[1:]

    elif count.startswith("="):
        count = count[1:]

    count = int(count)

    if op(num_files, count):
        message = "Check Passed - num files %d is %s %d"
        return RESULT_SUCCESS, message % (num_files, desc, count)
    else:
        message = "Check Failed. Counted: %d  expected count: %s"% (
            num_files, desc)
        raise RuntimeError(message)


def PathNotExists(path, dummy = None):
    """Check if the file exists returns 0 if the file doesn't exist and raises
    RuntimeError otherwise"""

    if os.path.exists(path):
        message = "Path found: '%s'"% path
        raise RuntimeError(message)
    else:
        return RESULT_SUCCESS, 'SUCCESS: Path does not exist'


def PathExists(path, dummy = None):
    """Check if the path exists returns 0 if the path exists and raises
    RuntimeError otherwise"""

    if os.path.exists(path):
        return RESULT_SUCCESS, 'SUCCESS: Path exists'
    else:
        message = "Path not found: '%s'"% path
        raise RuntimeError(message)


def SystemCommand(command, qualifiers = None):
    """Execute a system command, and optionally capture the output

    Allowed qualifiers are:
        - ui      output will not be captured - this allows the user to
                  interact with the command (i.e. if it may request the user
                  to hit a key.
        - nocheck Do not check the return value. Default is to raise an
                  exception if the return value is not 0 (success)
    """

    # as [] is a dangerous default - replace the default None with []
    # in the function body
    if qualifiers is None:
        qualifiers = []

    # if the
    new_stdout = sys.stdout
    if 'ui' not in qualifiers:
        new_stdout = tempfile.TemporaryFile()

    ret_value = subprocess.call(
        command,
        shell = True,
        stdout = new_stdout,
        stderr = new_stdout)

    output = ''
    if 'ui' not in qualifiers:
        new_stdout.seek(0)
        output = new_stdout.read()

        #new_stderr.seek(0)
        #errors = new_stderr.read()

    if 'nocheck' not in qualifiers and ret_value:
        output = "\n".join(["   " + line for line in output.split("\r\n")])
        message = ('Non zero return (%d) from command:\n  "%s"\nOUTPUT:\n%s'%(
                ret_value, command, output))
        raise RuntimeError(message)

    return ret_value, output


def dirname(path, dummy = None):
    return 0, os.path.dirname(path)

def basename(path, dummy = None):
    return 0, os.path.basename(path)

def ChangeCurrentDirectory(path, dummy = None):
    try:
        os.chdir(path)
        return 0, ""
    except OSError, e:
        raise RuntimeError(str(e))



def PushDirectory(path, dummy = None):
    try:
        PUSH_DIRECTORY_LIST.append(os.getcwd())
        os.chdir(path)
        return 0, ""
    except OSError, e:
        PUSH_DIRECTORY_LIST.pop()
        raise RuntimeError(str(e))


def PopDirectory(path = '', dummy = None):
    try:
        last_dir = PUSH_DIRECTORY_LIST.pop()
        os.chdir(last_dir)
        return 0, "Current directory is now '%s'"% last_dir
    except OSError, e:
        raise RuntimeError(str(e))
    except IndexError, e:
        raise RuntimeError("No previously pushed directory to pop")


class ExternalCommand(object):
    def __init__(self, full_path):
        self.full_path = full_path
    
    def __call__(self, params, qualifiers = None):
        if qualifiers is None:
            qualifiers = []
            
        if isinstance(params, list):
            params.append(qualifiers)
            params.insert(0, self.full_path)
        elif isinstance(params, basestring):
            #import pdb; pdb.set_trace()
            params = " ".join([self.full_path, params] + qualifiers)
        else:
            raise RuntimeError(
                "ExternalCommand.__call__ only accepts strings or lists")
            
        return SystemCommand(params)


NAME_ACTION_MAPPING = {
    'run'    : SystemCommand,
    'execute': SystemCommand,

    'exists': PathExists,
    'exist' : PathExists,
    'notexist' : PathNotExists,
    'notexists': PathNotExists,

    'count': VerifyFileCount,

    'dirname' : dirname,
    'filename': basename,
    'basename': basename,

    'cd'   : ChangeCurrentDirectory,
    'chdir': ChangeCurrentDirectory,

    'pushdir': PushDirectory,
    'pushd'  : PushDirectory,
    'popdir' : PopDirectory,
    'popd'   : PopDirectory,
}

def PopulateFromToolsFolder(tools_folder):
    
    for file in os.listdir(tools_folder):
        name, ext = os.path.splitext(file)
        name = name.lower()
        ext = ext.upper()
        
        if ext in (
            os.environ["pathext"].split(";") + [".PY", ".PL", ".PYW"]):
            
            if name not in NAME_ACTION_MAPPING:
                full_path = os.path.join(tools_folder, file)
                NAME_ACTION_MAPPING[name] = ExternalCommand(full_path)
            else:
                raise RuntimeError(
                    "External command conflicts with built-in command: '%s'"%
                        name)


# the following commands will not require to use the command syntax
# e.g.  " cd: <dir>"  to work correctly
DOS_REPLACE = [
    'cd',
    'chdir',
    'pushd',
    'popd',
]

PopulateFromToolsFolder(os.path.join(os.path.dirname(__file__), "tools"))