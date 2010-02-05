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

# the following commands are defined in the shell - so they won't work
# unless executed in the shell
# they raise an error when executed 
COMMANDS_REQUIRING_SHELL = [
    'assoc', 'break', 'call', 'cd', 'chcp', 'chdir', 'cls', 'color', 'copy', 
    'date', 'del', 'dir', 'diskcomp', 'diskcopy', 'echo', 'endlocal', 'erase', 
    'exit', 'for', 'format', 'ftype', 'goto', 'graftabl', 'if', 'md', 'mkdir',
    'mode', 'more', 'move', 'path', 'pause', 'popd', 'prompt', 'pushd', 'rd',
    'rem', 'ren', 'rename', 'rmdir', 'set', 'setlocal', 'shift', 'start', 
    'time', 'title', 'tree', 'type','ver', 'verify', 'vol']


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
        return RESULT_FAILURE, message 


def PathNotExists(path, dummy = None):
    """Check if the file exists returns 0 if the file doesn't exist and raises
    RuntimeError otherwise"""

    if os.path.exists(path):
        message = "Path found: '%s'"% path
        return RESULT_FAILURE, message
    else:
        return RESULT_SUCCESS, 'SUCCESS: Path does not exist'


def PathExists(path, dummy = None):
    """Check if the path exists returns 0 if the path exists and raises
    RuntimeError otherwise"""

    if os.path.exists(path):
        return RESULT_SUCCESS, 'SUCCESS: Path exists'
    else:
        message = "Path not found: '%s'"% path
        return RESULT_FAILURE, message


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
    
    #for shell_cmd in COMMANDS_REQUIRING_SHELL:
    #    if command.lower().startswith(shell_cmd):
    #        shell = True
    #        break

    # if the
    new_stdout = sys.stdout
    if 'ui' not in qualifiers:
        new_stdout = tempfile.TemporaryFile()

    if isinstance(command, basestring):
        command = command.strip()
        command_len = len(command)
    else:
        command_len = len(" ".join(command))
    
    subprocess_safe_command_limit = 2000
    if command_len > subprocess_safe_command_limit:
        raise RuntimeError(
            "The command is %d characters long. "
            "It cannot be longer than %d characters. '%s...'"% (
                command_len, subprocess_safe_command_limit, str(command)[:80]))
    
    # if we can turn shell off for some/all of the commands then it will
    # allow us to better handle catastrophic issues (e.g. command not found)
    #try:
    shell = True
    ret_value = subprocess.call(
        command,
        shell = shell,
        stdout = new_stdout,
        stderr = new_stdout)
    #except OSError, e:
    #    return e.errno, str(e)

    output = ''
    if 'ui' not in qualifiers:
        new_stdout.seek(0)
        output = new_stdout.read()

    return ret_value, output


def dirname(path, dummy = None):
    return 0, os.path.dirname(path)

def basename(path, dummy = None):
    return 0, os.path.basename(path)

def abspath(path, dummy = None):
    return 0, os.path.normpath(os.path.abspath(path))

def ChangeCurrentDirectory(path, dummy = None):
    try:
        if isinstance(path, list):
            path = path[0]
        os.chdir(path)
        return 0, ""
    except OSError, e:
        return e.errno, str(e)


def PushDirectory(path, dummy = None):
    try:
        PUSH_DIRECTORY_LIST.append(os.getcwd())
        os.chdir(path)
        return 0, ""
    except OSError, e:
        PUSH_DIRECTORY_LIST.pop()
        return e.errno, str(e)


def PopDirectory(path = '', dummy = None):
    try:
        last_dir = PUSH_DIRECTORY_LIST.pop()
        os.chdir(last_dir)
        return 0, "Current directory is now '%s'"% last_dir
    except OSError, e:
        return e.errno, str(e)
    except IndexError, e:
        raise RuntimeError("No previously pushed directory to pop")


class ExternalCommand(object):
    def __init__(self, full_path):
        if not os.path.exists(full_path):
            raise RuntimeError(
                "External command does not exist: '%s'"% full_path)
        self.full_path = full_path
    
    def __call__(self, params, qualifiers = None):
        if qualifiers is None:
            qualifiers = []
            
        if isinstance(params, list):
            params.extend(qualifiers)
            params.insert(0, self.full_path)
        elif isinstance(params, basestring):
            params = " ".join([self.full_path, params] + qualifiers)
        else:
            raise RuntimeError(
                "ExternalCommand.__call__ only accepts strings or lists")
        return SystemCommand(params)


def EscapeNewlines(input, qualifiers = ''):
        text = input.replace("\r", "\\\\r")
        text = text.replace("\n", "\\\\n")
        return 0, text    

def unescape_text(input):
    input = input.replace("\\t", "\t")
    input = input.replace("\\\\", "\\")
    input = input.replace("\\r", "\r")
    input = input.replace("\\n", "\n")
    return input
   

def Replace(input, qualifiers = None):
    #print input, qualifiers
    #import pdb; pdb.set_trace()
    to_find = unescape_text(qualifiers[0])
    replace_with = unescape_text(qualifiers[1])
    replaced = input.replace(to_find, replace_with)
    print to_find
    print replace_with
    print replaced
    import pdb; pdb.set_trace()
    
    return 0, replaced
    

def PopulateFromToolsFolder(tools_folder, dummy = []):
    
    for file in os.listdir(tools_folder):
        name, ext = os.path.splitext(file)
        name = name.lower()
        ext = ext.upper()
        
        if ext in (
            os.environ["pathext"].split(";") + [".PY", ".PL", ".PYW"]):
            
            full_path = os.path.join(tools_folder, file)
            if name not in NAME_ACTION_MAPPING:
                NAME_ACTION_MAPPING[name] = ExternalCommand(full_path)
            else:
                raise RuntimeError(
                    "External command conflicts with built-in command: '%s'"%
                        full_path)
    return 0, ""


NAME_ACTION_MAPPING = {
    'run'    : SystemCommand,
    'execute': SystemCommand,
    'system' : SystemCommand,

    'exists': PathExists,
    'exist' : PathExists,
    'notexist' : PathNotExists,
    'notexists': PathNotExists,

    'count': VerifyFileCount,

    'dirname' : dirname,
    'filename': basename,
    'basename': basename,
    'abspath' : abspath,

    'cd'   : ChangeCurrentDirectory,
    'chdir': ChangeCurrentDirectory,

    'pushdir': PushDirectory,
    'pushd'  : PushDirectory,
    'popdir' : PopDirectory,
    'popd'   : PopDirectory,

    'escape_newlines': EscapeNewlines,
    'escapenewlines' : EscapeNewlines,
    'replace' :        Replace,

    'add_tools_dir'   : PopulateFromToolsFolder,
}




# the following commands will not require to use the command syntax
# e.g.  " cd: <dir>"  to work correctly
DOS_REPLACE = [
    'cd',
    'chdir',
    'pushd',
    'popd',
]

PopulateFromToolsFolder(os.path.join(os.path.dirname(__file__), "tools"))