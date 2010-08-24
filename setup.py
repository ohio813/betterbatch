r"""BetterBatch scripts are designed as a middle ground 
between shell/batch scripts and more complete programming languages 
(Python, Perl, etc.). 

It is designed to make it very easy to call shell commands but to also do so 
safely, in that an error will make the script stop immediately.

As such you can generally provide scripts that do not have to perform much
error checking while still being very safe.

Also scripts are validated as much as possible before executation starts, so 
this should avoid simple errors only being found after some steps have been 
executed.

BetterBatch has been designed as a very simple process automation script (e.g.
build script, and could be used for processes that are not required to track
build dependencies (waf, scons are more suitable for those kinds of projects).


Here is an example script::


    # or user specific configuration
    - if exist <shell.username>.bb:
        - include <shell.username>.bb

    # you can define your own variables
    - set project_root=<__script_dir__>
    
    - copy <project_root>\*.xyz <shell.tmp>\backup

Tested with python 2.5.1 and 2.6.4

Current test coverage: 93%

"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import betterbatch

setup(
    name='BetterBatch',
    version = betterbatch.__version__,
    description = "Powerful batch file/script replacement",
    long_description = __doc__,
    keywords = 'python batch script automation',

    author = "Mark Mc Mahon",
    author_email =  "mark.m.mcmahon@gmail.com",
    
    packages = ["betterbatch", "betterbatch.tests"],
    scripts = ['bbrun.py', 'associate_bb_filetype.py'],
    requires=['yaml'],
    
    download_url=(
        'http://betterbatch.googlecode.com/'
        'files/betterbatch-%s.zip'% betterbatch.__version__),
    url = 'http://code.google.com/p/betterbatch/',
    
    license = "LGPL",

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: '
            'GNU Library or Lesser General Public License (LGPL)',
        'Programming Language :: Python',
        "Topic :: Software Development",
        "Topic :: Utilities",
        ],

    # setuptools script creation
    entry_points = {
        'console_scripts': ['bbrun = betterbatch.parsescript:Main',],}
    )
