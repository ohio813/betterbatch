************************************
BetterBatch Readme
************************************

====================================
What is BetterBatch
====================================
BetterBatch is meant as a replacement for batch files. It has the following 
advantages over batch files:

* easily include commands/variables from other files
* set variables from the output of system commands
* automatically checks the return value of executed commands
* built-in commands to allow easy checking of conditions (e.g. that a file exists)
* easier to read variable format
* strongly encourages separation of code and configuration
* allow easily and safely using external scripts/executables

BetterBatch's sweet spot is for things that can be done by a batch command and 
need to be maintained over time by different people who may not have the same
knowledge of scripts nor want the extra complexity of scripts (which are harder
to maintain).

The following example shows how to check if a file exists and copy from a 
location specified on the command line.

First of all enter the following text into a new text file named "copyfile.bb" ::

    - set file_to_check=<shell.temp>\testing_betterbatch.txt

    - if notexists <file_to_check>:
        - copy <file_to_copy> <file_to_check>

Now run it by running the following at the DOS prompt ::

    bbrun.py copyfile.bb file_to_copy=autoexec.bat


====================================
Instalation
====================================

BetterBatch does not have to be installed as a Python Package, just download, 
unzip and run bbrun.py.

Note - it does have a requirement on PyYAML (http://pyyaml.org/)
If you have Setuptools you can use the followin command::

    easy_install -U pyyaml

BetterBatch can also be installed as a Python module (if you want to import 
and use BetterBatch functionality in python scripts). Use easy_install.py or your 
favourite python package installation method.

If you want to associate the BetterBatch extension ".bb" with bbrun.py then you 
can run::

    bbrun associate_filetype.bb

This expects that python is on the path - but you can update it to your 
python installation if python is not on the path.


====================================
Script File Syntax
====================================

------------------------------------------------------
YAML
------------------------------------------------------

Script files need to be valid YAML, but don't worry too much about that!
The major ways that this will affect you are the following:

 * Tab characters should be avoided (BetterBatch actually will replace them 
   and print a warning when it loads a file with tab characters)
 * avoid colon (:) followed by whitespace other than where dictated by the
   BetterBatch syntax. The Yaml parser will treat it as the 'key' in a 'mapping'
   and it will cause the script not to run.

Note - while a YAML parser is being used to parse the file, some things which 
would fail if parsing as YAML directly will pass with betterbatch. This is 
because pre-processing is done on the contents of the file before it is passed
to the YAML parser.

------------------------------------------------------
Statements
------------------------------------------------------
A simple statement starts with a dash (-), whitespace and then the statement.

For example the typical Hello World! BetterBatch script is::

    - echo Hello World!

------------------------------------------------------
Executable Statements
------------------------------------------------------
Unless a statement is one of the other types it is an Executable Statement

If the executable statement is not a built-in command then it will be
executed in the shell, just as if you typed it at the command line.

Note - by default BetterBatch captures the output of the command 
(output and error output) and adds it to the logfile (if set). It will
also by default stop execution of the script if the command returns an
error value (return code other than zero(0)). This behaviour can be modified
by qualifiers.

The following qualifiers are available:
   **echo**
        output will still be captured - but it will be echoed to the terminal
        after the command has finished running
   **nocheck**
        an error return value from the command will not cause the script to
        terminate. A warning will be output in this case - but the script will
        continue.
   **ui**
        command output will not be captured by BetterBatch. The output will
        go directly to the terminal. This is useful if the command requires
        some interaction. For example dir /p requires the user to press a key
        after each screen of output.

------------------------------------------------------
Variable Definitions
------------------------------------------------------

Example::
   
   - set variable_name = variable value

Variable definitions can include other variables or executable sections. For 
example::

   - set variable_name = The value of <variable> and output of {{{executable section}}}

Refer to :ref:`executable-section` for more information on executable sections.

------------------------------------------------------
Variable References
------------------------------------------------------
You can reference any defined variable by using <variable_reference>.

The value of the variable will replace the variable reference.

If you need to have < or > in your script - then you double them. e.g.


------------------------------------------------------
Include statements
------------------------------------------------------
Example::
   
   - include path\to\includefile.bb

The steps in the included file will be executed at the point of inclusion as
if they were defined in the including file.

------------------------------------------------------
Logfile specification
------------------------------------------------------
Example::

   - logfile path\to\logfile.bb

If a previous logfile statement was given then that logfile will be closed 
(if it can be) and all logging information will be written to the new logfile.

------------------------------------------------------
IF statements
------------------------------------------------------
These statements allow you to 

Example::

   - if exists this_file:
     and exists that_file:
        - echo Great - both files exist
     else:
        - echo OH! - one of the files does not exist

"and" or "or" can be used with the "if" part of the statement. You cannot
mix "and" and "or" in the same if statement (it should be consistently "or"
or "and" in a single statement).

CAREFUL - the if/and/or/else all have to line up vertically - or the 
statement will not be parsed correctly.

A special case of the condition is the "defined variable_name" e.g. ::

    - if defined build:
        - echo Value for build is <build>
      else:
        - end 1, The BUILD variable is not set - please specify a value

This can be used to require the user to set pass a value at the command
line - and if they do not, to print an informative error message.

------------------------------------------------------
For statements
------------------------------------------------------
For statements are extremely basic at the moment in betterbatch and should be 
used with care.

The format of the step is::

    - for LOOP_VARIABLE in INPUT:
        - exectute steps 
        - which can use <LOOP_VARIABLE>

The block of statements is executed once per line in the input, so for example
the general case of iterating over files in a directory that match a pattern::

    - for file in {{{dir <__working_dir__>/b *.txt}}}:
        - echo working on "<file>"
        - Curl - upload <file> to site..


------------------------------------------------------
Parallel statements
------------------------------------------------------
Many steps can often take quite a bit of time to complete, and you may want 
other actions to start before it the long runnig step has finished.

Obviously these steps should not depend on each other.

One good example is downloading separate files, downloading can take quite a 
while and you may want to start many downloading/uploading processes at the same
time.

In batch files you can acheive this by preceding the call to the tools with "start"
but then you will not be able to easily check return status nor retrieve the tool's
output, etc.

In a BetterBatch script you can still use "Start" if you want - but much better is
to put the steps you want to execute in parallel in a "parallel" block::

    - parallel:
        - cUrl.exe big_file....
        - cUrl.exe another_big_file....
        - cUrl.exe and lots of small files 1
        - cUrl.exe and lots of small files 2
        - cUrl.exe etc

As the order of execution of the items in the parallel section is not defined
you should never rely on one starting/finishing before another will start/finish.
Also ONLY command steps are allowed (i.e. no Variable Definitions, logfile, include, 
for or if statements are allowed.


.. _executable-section:

------------------------------------------------------
Executable Sections
------------------------------------------------------
Executable sections can be used in variable definition or executable 
statements. The section will be replaced from the output from the section 
after executing it.

Examples::

 - set file_contents = {{{type c:\autoexec.bat }}}
 - echo {{{ replace <file_contents> {*a*} {*b*} }}}
 - file_list {{{ dir c:\ /b }}}
 
Executable sections can call any built-in command or external command.
Executable sections can reference variables


------------------------------------------------------
Special Variables
------------------------------------------------------
**__script_dir__**
    The directory where the script file is stored. Note - these values are 
    not changed for included scripts, included scripts use the same values
    as the including scripts

**__script_filename__**
    The filename of the script. 

**__working_dir__**
    The current directory when the script was executed. 

For example if you runn the following command::
    
    c:\Program Files\betterbatch> bbrun.py c:\MyProject\MakeBuild.bb
    
then the values of the special variables will be::
   
   __script_dir__        c:\MyProject
   __script_filename__   MakeBuild.bb
   __working_dir__       c:\Program Files\betterbatch

    
**shell.***
    Shell environment variables are pre-fixed with 'shell.' to avoid conflicts 
    with any internal variables. 
    
    For example if your script expects the user to pass a 'buildnumber' value 
    to the script, but the environment has a 'buildnumber' variable defined. 
    Without the pre-fix the environment variable would have been used silently
    if no value was passed to the script. The shell prefix makes it clearer
    that the BetterBatch script is going to use the environment value.
    
    



====================================
Troubleshooting:
====================================

