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
import sys

RESULT_SUCCESS = 0
RESULT_FAILURE = 1


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

    num_files = len(glob.glob(file_pattern))

    op = operator.eq
    desc = count

    if isinstance(count, basestring):
        count = count.strip()

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
        raise RuntimeError("Check Failed. Counted: %d  expected count: %s"% (
            num_files, desc))


def FileExists(path, dummy = None):
    """Check if the file exists returns 0 if the file exists and raises
    RuntimeError if the file does not exist"""

    if os.path.exists(path):
        return RESULT_SUCCESS, 'SUCCESS: Path exists'
    else:
        raise RuntimeError("Required file not found: '%s'"% path)


def Output(message, dummy = None):
    "Output the message"

    LOG.info(message)

    return RESULT_SUCCESS, ''


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
        raise RuntimeError(
            "Non zero return (%d) from command:\n  %s:\nOUTPUT:\n%s"%(
                ret_value, command, output))

    return ret_value, output


NAME_ACTION_MAPPING = {
    'run':         SystemCommand,
    'exists':      FileExists,
    'count':       VerifyFileCount,
    'print':       repr,
}


