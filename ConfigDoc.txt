BetterBatch Readme

====================================
Introduction
====================================
BetterBatch is meant as a replacement for batch files. It has the following 
advantages over batch files:
 
* able to include easily data from other files
* allow setting of variables from the output of commands
* Automatic checking of the return value of executed commands
* Built in commands to allow easy checking of conditions (e.g. that a file exists)
* Easier to understand variable format
* Strongly encourages separation of code and configuration
  
  * No branching/looping constructs in configuration files
  * Allow easily using code in external files


====================================
Instalation
====================================

If you have easy_install already on your machine then run the following at the 
command probmp::

 easy_install BetterBatch

* Otherwise then go to PYPi 
* download the BetterBatch zip
* Extract the zip file
* At the command prompt run
::

  path/to/python/python.exe setup.py install


(download and setup)


====================================
Quick Start - 
====================================
Create a new text file called ""




====================================
Converting from BatchFiles
====================================

====================================
Why use BetterBatch rather than ...?
====================================
BetterBatch is similar to other things already out there so why use it?

------------------------------------------------------
DOS Batch files
------------------------------------------------------

Safer (Error checking)
------------------------------------------------------
BetterBatch by default checks the return value for every command. If a command
fails then the script will stop. Batch files make it very easy to ignore that 
an individual step has failed.


Assign the output of a command to a variable
------------------------------------------------------
This may sound like a minor improvement but it makes a huge difference. It 
allows individual bits of functionality to be easily broken up.

If you want to avoid having to specify a variable that can be
reasonably calculated from another variable you can easily factor this out to
a simple script. In the following example I show how to set the ISO 639 Language
code (used in XML) from the language name.

DOS Batch::

    if /i "%lang_name%"== 'ABHAZIAN' set lang_iso_639=AB
    if /i "%lang_name%"== 'AFAN (OROMO)' set lang_iso_639=OM
    ...
    if /i "%lang_name%"== 'ZHUANG' set lang_iso_639=ZA
    if /i "%lang_name%"== 'ZULU' set lang_iso_639=ZU


BetterBatch::

    lang_iso_639 = (system) Get_iso_639_lang.pl <lang_name>

This perl file of course has to have the language table coded into it also
but not it can be called easily from anywhere else too. And as the funcitonality
is broken up - it will be easier to test for errors.


Easier to add other checks
------------------------------------------------------
It is very easy to add checks at any point in the process. Compare the following
two methods of checking if a file exists...

DOS Batch::

    if not exist somefile goto Some_Error_Condition

BetterBatch::
 
    - exists: somefile

Any other check can be easily added by calling a batch/exe/script that returns 0
for sucess and a non-zero value for failure.


Verifies variables are defined
------------------------------------------------------
In Dos batch files if a variable does not exist then no error message will 
shown, and the variable will be replaced with "" (empty string). 

In BetterBatch all variable definitions are checked before anything is run.


Easier to read
------------------------------------------------------
BetterBatch files are simpler than DOS Batch files in many ways which makes
them easier to understand. 

Variable references are also easier to read. In Batch files variable references
are defined using %% for both start and end tags while in BetterBatch files
they are defined using < and > for hte start and end tags respetively. If there
are multiple variables in a line - then it makes it much simpler to see all the
variable references

DOS Batch::

    set build_folder=%PROJECT_FOLDER%\%BUILD%\%LANG%

BetterBatch::
 
    build_folder:  <PROJECT_FOLDER>\<BUILD>\<LANG>


Include other configuration files
------------------------------------------------------
In Batch files it can be difficult to create another batch file that defines
all the variables required. It can be done - but as there is no checking for
undefined variables - it makes it difficult to track down errors. Commands and
Variables can be used in other YAML files making it possible to define common
YAML files that have no project nor machine specific information.


Allow long lines to be split
------------------------------------------------------
In DOS batch files you cannot split a long line over multiple lines (to aid 
readability). In BetterBatch there are a number of ways of doing it:

Specify value as a YAML string (starting on the first line - automatically
continued on the following lines - as long as they are more indented::

    - run: echo this is a very
        long string that will treated after parsing a single line
        by BetterBatch - this is a feature of YAML.

By using a YAML string block::
    - run: >
        echo this is a very
        long string that will treated after parsing a single line
        by BetterBatch - this is a feature of YAML.

------------------------------------------------------
Python/Perl/LUA or other scripting languages
------------------------------------------------------

Simpler
------------------------------------------------------
The main reason for using BetterBatch rather than a full fledged scripting 
language is that the YAML configuration files are much simpler.

If a user does not know Python/Perl/Ruby/Lua/etc. it would be a significant 
effort for them to learn that language to do what they can do easily using 
BetterBatch.


Language Agnositc
------------------------------------------------------
You can create tools/checks/etc for BetterBatch in any language you want. As 
long as it can be executed on the command line - it can be used by BetterBatch.

This means that in a single YAML file you could set variables from PERL files,
call a check written in Python, and execute a script in a BATCH file


Foster re-use and modularization
------------------------------------------------------
BetterBatch files act as a glue between different components. BetterBatch does
not apply force restrictions on these components other than they can be run on 
the command line and that they return 0 on success. This means that anything 
written for a BetterBatch process will also work (and can be debugged) outside
of BetterBatch.



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

If a variable is defined referencing a variable that is not defined e.g.
Variables:
 using_unknown_var:  This <noun> is remarkable

an error will NOT be raised unless something uses the 'using_unknown_var' variable.


------------------------------------------------------
Variable Overriding:
------------------------------------------------------
Variables can be overriden at many points:
a) you can force a particular value by specifying it at the command line
If you do this - this WILL be the value of that variable!

b) If the config file specified at the command line will defines that variable
and it is not overridden at the command line it's value will be used.

c) Variables will be taken from the included files if not overriden on the command
line or in the main config file. If more than one included config file has the 
variable then values in earlier config files will be overridden by later included
config files.



====================================
Trouble Shooting:
====================================

Spaces in paths for "RUN" commands
This can be difficult but there are a number of ways around it.

All of the following will work as they are all valid YAML - it's up to you 
which you prefer

a) Wrap the whole command in single quotes (') and the path that has spaces in 
double quotes.
e.g. ::

 - Run: '"c:\program files\SDL Passolo 2009\pslcmd.exe" project.lpu /generate'

b) use one of the block string processors ('|' or '>'), put the command line on
the next line and finally surround the path with spaces in double quotes
e.g. ::

 - Run: |  # > would have worked just as well
    "c:\program files\SDL Passolo 2009\pslcmd.exe" project.lpu /generate

c) Split it up into separate arguments by creating a list
e.g. ::

 - Run: 
    - c:\program files\SDL Passolo 2009\pslcmd.exe
    - project.lpu 
    - /generate


Integers and decimals
These are not accepted as variable values because the representation of the 
value may not be the same as the value. For example if you have the following variable
specification
Variables::

   MyVar: 0001

After parsing MyVar will be the integer value 1, when in fact you probably wanted
a string value '0001'. To resolve this wrap the value in single or double quotes.

Similarly for decimals, leading and trailing 0's will be stripped off, and more
complicated due to how computers represent decimal values the following may happen
Variables::

  MyVar: 0.1

If you need to use MyVar as a string you may well see "0.10000000000000001".

For these reasons you cannot provide a normal variable value as an integer or decimal value.



Ideal localization automation process:

Variables separate from scripts (e.g. YAML or something simpler)

Tools are commands (i.e. not specialized scripts that only work with the framework)

Lots of checking on the environment before each build step.


Common structure that will work for all projects::

    \Builds
    \Tools
        \CUP (should be stored outside of build environemt - i.e. similar to Perl/Python?)
        \AutoMaster 
        \Parsers
        \Macros
        \ETC
    \Config

Very easy to call separate parts of the process (I see in Map batch files similar to ::

	1_DownloadEnuBuild.bat, 
	2_UpdateFilespec.bat, 
	3_AnalyzeFilespecNow.txt
	4_Extractfiles.bat

I like this - but there needs to be a better way to share environment between the scripts (and also validation of the environment)
	
Tools should often work on single files and on multiple files:
 e.g::
 
 	upload_to_pp srcfile1.lpu dest username password
 	upload_to_pp srcfile2.lpu dest username password
 	upload_to_pp srcfile3.lpu dest username password
 	upload_to_pp srcfile4.lpu dest username password
 
 it is so much nicer to write ::
 
  	upload_to_pp srcfile?.lpu dest username password
 
 or maybe::
 
 	upload_to_pp srcfile[1-4].lpu dest username password


Maybe::

	YAML config file, specifies main variables, etc
	
    Run 2_UpdateFilespec 26.6 DEU
        reads configuration
        Checks the environment
        creates batch file
        Runs Batch File