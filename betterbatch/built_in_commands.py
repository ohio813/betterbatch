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
import re
import shlex
import compare

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
        message = "Files counted: %d  %s %d (TRUE)"
        return RESULT_SUCCESS, message % (num_files, desc, count)
    else:
        message = "Files counted: %d  %s %d (FALSE)"% (
            num_files, desc, count)
        return RESULT_FAILURE, message


def PathNotExists(path, dummy = None):
    """Check if the file exists returns 0 if the file doesn't exist and raises
    RuntimeError otherwise"""

    #strip leading and trailing quote characters
    path = path.strip('"')
    if os.path.exists(path):
        return RESULT_FAILURE, "Path exists: '%s'"% path
    else:
        return RESULT_SUCCESS, "Path does not exist: '%s'"% path


def PathExists(path, dummy = None):
    """Check if the path exists returns 0 if the path exists and raises
    RuntimeError otherwise"""

    #strip leading and trailing quote characters
    path = path.strip('"')
    if os.path.exists(path):
        return RESULT_SUCCESS, "Path exists: '%s'"% path
    else:
        return RESULT_FAILURE, "Path does not exist: '%s'"% path


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

    #use_shell = False
    #if command.strip().lower().split()[0] in COMMANDS_REQUIRING_SHELL:
    #    use_shell = True

    # if the 'ui' qualifier has not been specified then
    # capture the output
    new_stdout = sys.stdout
    if 'ui' not in qualifiers:
        new_stdout = tempfile.TemporaryFile()

    command = command.strip()
    command_len = len(command)

    subprocess_safe_command_limit = 2000
    if command_len > subprocess_safe_command_limit:
        raise RuntimeError(
            "The command is %d characters long. "
            "It cannot be longer than %d characters. '%s...'"% (
                command_len, subprocess_safe_command_limit, str(command)[:80]))

    # if we can turn shell off for some/all of the commands then it will
    # allow us to better handle catastrophic issues (e.g. command not found)

    # for some reason when passing to the shell - we need to quote the
    # WHOLE command with ""
    command = '"%s"'% command
    ret_value = subprocess.call(
        command,
        shell = True,
        stdout = new_stdout,
        stderr = new_stdout)

    output = ''
    if 'ui' not in qualifiers:
        new_stdout.seek(0)
        output = new_stdout.read()

    return ret_value, output


def dirname(path, dummy = None):
    "Wrap os.path.dirname"
    return 0, os.path.dirname(path)

def basename(path, dummy = None):
    "Wrap os.path.basename"
    return 0, os.path.basename(path)

def abspath(path, dummy = None):
    "Wrap os.path.abspath"
    return 0, os.path.normpath(os.path.abspath(path))

def ChangeCurrentDirectory(path, dummy = None):
    """Try to change to the directory

    Replaces 'cd' command which would not achieve anything as the shell that
    it executes in would dissapear immediately"""
    try:
        if isinstance(path, list):
            path = path[0]
        os.chdir(path)
        return 0, ""
    except OSError, e:
        return e.errno, str(e)


def PushDirectory(path, dummy = None):
    "Change into the directory and store the previous current directory"
    try:
        PUSH_DIRECTORY_LIST.append(os.getcwd())
        os.chdir(path)
        return 0, ""
    except OSError, e:
        PUSH_DIRECTORY_LIST.pop()
        return e.errno, str(e)


def PopDirectory(path = '', dummy = None):
    "Change into the 'previous' directory on the stack pushed by PushDirectory"
    try:
        last_dir = PUSH_DIRECTORY_LIST.pop()
        os.chdir(last_dir)
        return 0, "Current directory is now '%s'"% last_dir
    except OSError, e:
        return e.errno, str(e)
    except IndexError, e:
        raise RuntimeError("No previously pushed directory to pop")


class ExternalCommand(object):
    "Wrap the a call to a system command or program"
    def __init__(self, full_path):
        if not os.path.exists(full_path):
            raise RuntimeError(
                "External command does not exist: '%s'"% full_path)
        self.full_path = full_path

    def __call__(self, params, qualifiers = None):
        if qualifiers is None:
            qualifiers = []

        if isinstance(params, basestring):
            params = " ".join([self.full_path, params] + qualifiers)
        else:
            raise RuntimeError(
                "ExternalCommand.__call__ only accepts strings")
        return SystemCommand(params)


def EscapeNewlines(text, qualifiers = ''):
    "Return the input with newlines replaced"
    text = text.replace("\r", "\\\\r")
    text = text.replace("\n", "\\\\n")
    return 0, text


#def unescape_text(text):
#    "Return the input with newlines replaced"
#    text = text.replace("\\t", "\t")
#    text = text.replace("\\\\", "\\")
#    text = text.replace("\\r", "\r")
#    text = text.replace("\\n", "\n")
#    return text
#
#
def Replace(text, qualifiers = None):
    "Replace a string in the input"
    flags = 0
    if 'nocase' in qualifiers:
        flags |= re.IGNORECASE
        del qualifiers[qualifiers.index('nocase')]

    use_re = False
    if 're' in qualifiers:
        del qualifiers[qualifiers.index('re')]
        use_re = True

    require = False
    if 'require' in qualifiers:
        del qualifiers[qualifiers.index('require')]
        require = True

    to_find = qualifiers[0]
    replace_with = qualifiers[1]
    if use_re:
        search_re = re.compile(to_find, flags)
        replaced, count = search_re.subn(replace_with, text)
    else:
        search_re = re.compile(re.escape(to_find), flags)
        count = 0
        replaced = text
        for found in search_re.findall(text):
            replaced = text.replace(found, replace_with)
            count += 1

    if require and not count:
        raise RuntimeError(
            "Required replace in '%s' in '%s' but not found"% (to_find, text))

    return 0, replaced


def Split(text, split_text = None):
    """Split the input on the split_text text

    if split_text is not defined then it will split on all whitespace"""
    if not split_text:
        split_text = None
    else:
        split_text = split_text[0]
    bits = [b.strip() for b in text.split(split_text)]
    return 0, "\n".join(bits)


def PopulateFromToolsFolder(tools_folder, dummy = None):
    """Make the commands in the specified tools_folder easy to call

    All executable programs will be added to the list of available tools
    they can be called without specifying the path to the tool
    """

    for tool_file in os.listdir(tools_folder):
        name, ext = os.path.splitext(tool_file)
        name = name.lower()
        ext = ext.upper()

        if ext in (
            os.environ["pathext"].split(";") + [".PY", ".PL", ".PYW"]):

            full_path = os.path.join(tools_folder, tool_file)
            if name not in NAME_ACTION_MAPPING:
                NAME_ACTION_MAPPING[name] = ExternalCommand(full_path)
            else:
                raise RuntimeError(
                    "External command conflicts with built-in command: '%s'"%
                        full_path)
    return 0, ""


def Compare(text, qualifiers = None):
    """Compare the two strings

    text should be
        str1 op str2
    e.g.
        About == about
        "Beautiful Day" contains day

    see compare.py for a full list of operators
    """
    try:
        str1, op_text, str2 = shlex.split(text)
    except ValueError:
        raise RuntimeError("Comparison was not defined correctly: '%s'"% text)

    if qualifiers is None:
        qualifiers = []

    if "nocase" in qualifiers:
        str1 = str1.lower()
        str2 = str2.lower()

    if "asint" in qualifiers:
        str1 = int(str1)
        str2 = int(str2)

    op = compare.ParseComparisonOperator(op_text)

    matches = compare.RunComparison(str1, op, str2)

    if matches:
        return 0, ""
    else:
        return 1, ""


def UpperCase(text, qualifiers = None):
    "return the string uppercased"
    return 0, text.upper()


def LowerCase(text, qualifiers = None):
    "return the string lowercased"
    return 0, text.lower()


NAME_ACTION_MAPPING = {
    #'run'    : SystemCommand,
    #'execute': SystemCommand,
    #'system' : SystemCommand,

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
    'split' :          Split,

    'compare' :      Compare,
    'upper' :        UpperCase,
    'uppercase' :    UpperCase,
    'lower' :        LowerCase,
    'lowercase' :    LowerCase,

    'add_tools_dir'   : PopulateFromToolsFolder,
}

BETTER_BATCH_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")
if os.path.exists(BETTER_BATCH_TOOLS_DIR):
    PopulateFromToolsFolder(BETTER_BATCH_TOOLS_DIR)
