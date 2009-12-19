"""Built in commands.

These commands are available as in commands

e.g. Run: dir /s
e.g. CountFiles:  <database_dir>\*.lpu 3  # ensure 3 LPU's
etc
"""
import operator
import os.path
import glob
import subprocess
import tempfile


RESULT_SUCCESS = 0
RESULT_FAILURE = 1


def VerifyFileCount(file_pattern, count):
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

    # strip all spaces from the count
    count = "".join(count)

    num_files = len(glob.glob(file_pattern))

    op = operator.eq
    desc = 'equal'

    if isinstance(count, basestring):
        count = count.strip()

        if count.startswith(">="):
            op = operator.ge
            count = count[2:]
            desc = "greater than or equal"

        elif count.startswith("<="):
            op = operator.le
            count = count[2:]
            desc = "less than or equal"

        elif count.startswith(">"):
            op = operator.gt
            count = count[1:]
            desc = "greater than"

        elif count.startswith("<"):
            op = operator.lt
            count = count[1:]
            desc = "less than"

        elif count.startswith("="):
            count = count[1:]

        count = int(count)

    if not op(count, num_files):
        raise RuntimeError("Check Failed - num files %d is NOT %s %d"% (
            num_files, desc, count))
    else:
        message = "Check Passed - num files %d is %s %d"
        return RESULT_SUCCESS, message % (num_files, desc, count)


def FileExists(path, dummy):
    "Check if the file exists"

    if os.path.exists(path):
        return RESULT_SUCCESS, ''
    else:
        raise RuntimeError("File not found: '%s'"% path)


def Output(message, dummy):
    "Output the message"

    LOG.info(message)

    return RESULT_SUCCESS, ''


def CheckedSystemCommand(command, capture_output = True):
    ret, output = SystemCommand(command, capture_output)

    if ret:
        raise RuntimeError(
            "Non zero return (%d) from command:\n  %s:\nOUTPUT: %s"%(
                ret, command, output))

    else:
        return ret, output

def SystemCommand(command, capture_output = True):
    "Execute a system command, and optionally capture the output"

    if capture_output:
        new_stdout = tempfile.TemporaryFile()

    ret_value = subprocess.call(
        command,
        shell = True,
        stdout = new_stdout,
        stderr = subprocess.STDOUT)

    output = ''
    if capture_output:
        new_stdout.seek(0)
        output = new_stdout.read()

        #new_stderr.seek(0)
        #errors = new_stderr.read()

    return ret_value, output


NAME_ACTION_MAPPING = {
    'run':         CheckedSystemCommand,
    'exists':      FileExists,
    'count':       VerifyFileCount,
    'print':       repr,
}


