************************************
BetterBatch Readme
************************************

====================================
What is BetterBatch
====================================
BetterBatch is meant as a simple replacement for batch files. It has the following 
advantages over batch files:

* able to easily include other files
* allow setting of variables from the output of commands
* automatic checking of the return value of executed commands
* built in commands to allow easy checking of conditions (e.g. that a file exists)
* easier to understand variable format
* strongly encourages separation of code and configuration
  
  * No looping constructs in configuration files
  * allow easily and safely using code in external files

BetterBatch's sweet spot is for things that can be done by a batch command and 
need to be maintained over time by different people who may not have the same
knowledge of scripts nor want the extra complexity of scripts that are harder
to maintain.

The following example shows how to check if a file exists and copy from a 
location specified on the command line.

First of all enter the following text into a new text file named "copyfile.bb" ::

    variables:
        file_to_copy: <arg1>
        file_to_check: <tmp>\testing_betterbatch.txt

    Steps:
    - if:
        - notexists: <file_to_check>
        - do: copy <file_to_copy> <file_to_check>

Now run it by running the following at the DOS prompt ::

    bbrun.py copyfile.bb \autoexec.bat


====================================
Instalation
====================================

BetterBatch does not have to be installed, just download, unzip and run 
bbrun.py.

It can also be installed as a Python module (if you want to import and use
betterbatch functionality in python scripts). Use easy_install.py or your 
favourite python package installation method.


======================================================
Quick Start Example - replacing Tomcat's Catalina.bat
======================================================
I did a search on my hard drive for some batch file to convert that would give
a good example of where betterbatch could be used instead of DOS Batch files.

I found one example in Tomcat's catalina.bat. I don't replicate the comments
in this quick start example.

Create a new text file "catalina.yaml" ::

    variables:
     
    Steps:
    - exist: <CATALINA_HOME>\bin\catalina.bat
    - if:
        - exist: <CATALINA_HOME>\bin\catalina.bat
        - do:
            <CATALINA_HOME>\bin\catalina.bat
        - else:


====================================
Config Files
====================================

The config file is made up of named sections:
- "Includes" section
- "Variables" section
- Section for each command group


====================================
Inclues Section (Optional).
====================================
Here you specify which configuration files you would like to include. Included 
files are read in the order they are displayed.Which means that tems defined in 
an earlier include can be overridden in subsequent include files and the current 
config file (the file which specifies the includes) can override information in
included files.

example::

    Includes:
     - IncludeFile_1.yaml
     - IncludeFile_2.yaml
 
In this example IncludeFile_2.yaml can override any variable/command defined in 
IncludeFile_1.yaml


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
Variable Overriding:
------------------------------------------------------
Variables can be overriden at many points:

1. you can force a particular value by specifying it at the command line
If you do this - this WILL be the value of that variable!

2. If the config file specified at the command line will defines that variable
and it is not overridden at the command line it's value will be used.

3. Variables will be taken from the included files if not overriden on the command
line or in the main config file. If more than one included config file has the 
variable then values in earlier config files will be overridden by later included
config files.



====================================
Trouble Shooting:
====================================

------------------------------------------------------
Spaces in paths for "RUN" commands
------------------------------------------------------

This can be difficult but there are a number of ways around it.

All of the following will work as they are all valid YAML - it's up to you 
which you prefer

A. Wrap the whole command in single quotes (') and the path that has spaces in 
double quotes.
e.g. ::

 - Run: '"c:\program files\SDL Passolo 2009\pslcmd.exe" project.lpu /generate'

B. use one of the block string processors ('|' or '>'), put the command line on
the next line and finally surround the path with spaces in double quotes
e.g. ::

 - Run: |  # > would have worked just as well
    "c:\program files\SDL Passolo 2009\pslcmd.exe" project.lpu /generate

C Split it up into separate arguments by creating a list
e.g. ::

 - Run: 
    - c:\program files\SDL Passolo 2009\pslcmd.exe
    - project.lpu 
    - /generate


------------------------------------------------------
Integer and decimal variables
------------------------------------------------------
These are not accepted as variable values because the representation of the 
value may not be the same as the value, which could be confusing. For the most
part they are also not necessary as most shells treat arguments as strings.

For example if you have the following variable
specification
Variables::

   MyVar: 0001

After parsing MyVar will be the integer value 1, when in fact you probably wanted
a string value '0001'. To resolve this wrap the value in single or double quotes.

Similarly for decimals, leading and trailing 0's will be stripped off, and more
complications due to how computers represent decimal values may also arise ::

  MyVar: 0.1

When you print MyVar you may well see "0.10000000000000001" -  almost certainly
not what you want!

For these reasons decimal or integer variables are not allowed.



