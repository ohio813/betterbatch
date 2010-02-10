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

------------------------------------------------------
Logfile specification
------------------------------------------------------
Example::

   - logfile path\to\logfile.bb

------------------------------------------------------
IF statements
------------------------------------------------------
Example::

   - if exists this_file:
     and exists that_file:
        - echo Great - both files exist
     else:
        - echo Oh :( one of the files does not exist


if defined variable_name




====================================
Variables Section (Optional)
====================================
Here you can specify variables that can be referenced later by putting angle
brackets around the variable name e.g. ::

    Variables:
     test_var:  test
     test_2_var = <test_var>_more_text
 
The resulting value of test_2_var will be "test_more_text".

If a variable is defined referencing a variable that is not defined e.g. ::
  
  Variables:
     using_unknown_var:  This <noun> is remarkable

an error will NOT be raised unless something uses the 'using_unknown_var' variable.


------------------------------------------------------
Variable Overriding
------------------------------------------------------
Variables can be overriden at many points:

1. You can force a particular value by specifying it at the command line
If you do this - this WILL be the value of that variable!

2. If the config file specified at the command line will defines that variable
and it is not overridden at the command line it's value will be used.

3. Variables will be taken from the included files if not overriden on the command
line or in the main config file. If more than one included config file has the 
variable then values in earlier config files will be overridden by later included
config files.


------------------------------------------------------
Special Variables
------------------------------------------------------
**__script_dir__ **
    The directory where the script file is stored. Note - these values are 
    not changed for included scripts, included scripts use the same values
    as the including scripts

**__script_filename__ **
    The filename of the script. 

**__working_dir__**
    The current directory when the script was executed. 

For example if you runn the following command::
    
    c:\Program Files\betterbatch> bbrun.py c:\MyProject\MakeBuild.bb
    
then the values of the special variables will be::
   
   __script_dir__        c:\MyProject
   __script_filename__   MakeBuild.bb
   __working_dir__       c:\Program Files\betterbatch

    
**shell.* **
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

