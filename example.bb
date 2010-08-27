# this sets the log file. The log file CAN be changed 
# during execution (logfile can use variables defined in file 
# as opposed to includes)
- logfile <__script_dir__>\test_bb.log


# This is a very simple function definition
- function PrintArgs (arg1, arg2, arg3=hi, arg4=yo):
    - echo <arg1>, <arg2>, <arg3>, <arg4>

# call the function and pass an override for the arg4 default value
- call PrintArgs (here, there, arg4=elsewhere)

# Parallel sections allow all steps to be run in parallel
# each step is started in it's own thread and will be run all at the same time.
# do not depend on any one step completing before or after any other step.
- parallel:
    #- dir "Thjs would fail - other steps in parallel block would still execute" /b
    - dir <shell.tmp>\*.tmp /b
    - dir <shell.windir>\*.exe /b
    - dir <shell.windir>\*.exe /b

# the following two 'pseudo' variables allow you to 
# get directory where the script is and the directory
# from which the script was executed.
- echo __script_dir__ pseudo variable:  <__script_dir__>
- echo __working_dir__ pseudo variable: <__working_dir__>

# betterbatch pulls in the environment variables so that these can be used
# by better batch
- echo <shell.computername>


# for example this would be a good way to include machine specific 
# configuration
- if exist <shell.computername>.bb:
  - include <shell.computername>.bb

# or user specific configuration
- if exist <shell.username>.bb:
  - include <shell.username>.bb

- if exist betterbatch\tests\test_files\commands.yaml:
  - include betterbatch\tests\test_files\commands.yaml

# you can define your own variables
- set project_root = <__script_dir__>


# Note - include statements cannot use variables defined in the script (because 
# includes are executed before variable definitions statements are)
- include <__script_dir__>\betterbatch\tests\test_files\basic.yaml

# this will not work for example because <project_root> is
# not defined by the time the include will be executed
#- include <project_root>\betterbatch\tests\test_files\basic.yaml


# change 0 to 1 to test
- if compare 1 = 0:
    # because of the 'ui' qualifier the output of this command will not 
    # be captured because of the 'nocheck' qualifier the return value will
    # not be checked (so you can CTRL+C)
    - dir c:\ /s /p {*ui*} {*nocheck*}

# example of channging the logfile
- logfile <project_root>\test_bb2.log

# finally you can pass in variables on the command line:
# the following section will only be run if you pass something like:
#    perform_section=true at the command line
- if defined perform_section:
    - echo ************************************************
    - echo YOU PASSED SOMETHING AT THE COMMAND LINE
    - echo ************************************************


# qualifiers modify how the command is executed, qualifiers are:
# {*ui*}, {*nocheck*} and {*echo*}
#  ui      - does not capture the text, so the user can work with 
#            the output interactively
#  nocheck - does not check the return value - so even if it fails 
#            errors will be ignored
#  echo    - output will be echoed
# It doesn't make sense to have echo + ui
- cd non_existing_directory {*nocheck*} {*echo*}  


# add_tools_folder will make the executable programs in the specified folder
# availabe in the script without requing path or extension
- add_tools_dir c:\  # you a folder on your machine or in your config


# you can assign variables to the output of commands
# it can be multiline text there is a utility built in command to 
# replace new lines (\r\n)
- set boot.ini = {{{type c:\boot.ini}}}
- set boot.ini.one_line = {{{EscapeNewlines <boot.ini>}}}
- echo <boot.ini.one_line>

# the code within an {{{executable section}}} can include any shell
# command or any built_in commands. There can be more than one on a line
# But they cannot be embedded (on the same line - if you need to embed - you
# can do that by using a temporary variable)
- set dir_to_search = {{{echo <shell.windir>}}}
- set found = {{{dir <dir_to_search>\win.ini}}} {{{cd nowhere {*nocheck*}{*echo*}}}}


# commands can be split over many lines very easily
# either implicitely or by using > or | characters

# implicit or by using > character will result in all text being on one line
- set long_greater=different
    values here
      and here
# equivalent to 
- >
    set long_greater=different
    values here
      and here


- echo <long_greater>

# | character will result in all text being on many lines (i.e. 
#   it is kept as is with leading space stripped)
- |
    set long_pipe=different
    values here
      and here


- set escaped = {{{escapenewlines <long_pipe>}}}
- echo <escaped>

# scrpits can be ended at any, using an END statment
# it must include error return value and can include an optional message
- end 0, Enough for now - stopping
