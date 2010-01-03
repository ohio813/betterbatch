

VERSION = '1.0'

LONG_DESCRIPTION = """BetterBatch scripts are very basic - and most 
functionality is in external commands. This keeps BetterBatch simple - and also 
fosters re-use of existing components and creation of small modular components.

A 'plugin' of BetterBatch is any tool that can be run at the OS shell prompt.
 Additional the command should return 0 for success and any non-zero value for
failure.

Simple 'BetterBatch' file example:

    includes:
        - an_include_file.yaml

    Variables:
        root: c:\here\there
        src: <root>\source
        dest: <root>\destination

    commands:
        # source has to exist
        - exists: <src>

        # Don't fail if the directory already exists
        - md nocheck: <dest>

        # copy the source directory to the destination directory
        - xcopy /s /e <src> <dest>
    
"""

from distutils.core import setup

setup(
    name='BetterBatch',
    version = VERSION,
    description = "Simplified script runner",
    long_description = LONG_DESCRIPTION,
    keywords = 'python batch script automation',

    author = "Mark Mc Mahon",
    author_email =  "mark.m.mcmahon@gmail.com",
    
    packages = ["betterbatch", "betterbatch.tests"],
    scripts = ['betterbatch/scripts/betterbatch.py'],
    requires=['yaml'],
    
    #download_url=(
    #    'http://www.example.com/pypackage/dist/pkg-%s.tar.gz'% VERSION),
    #url = '',
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
    )
