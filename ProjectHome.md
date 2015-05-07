`BetterBatch` scripts are very basic - and most functionality is in external commands. This keeps `BetterBatch` simple - and also fosters re-use of existing components and creation of small modular components.

A 'plugin' of `BetterBatch` is any tool that can be run at the OS shell prompt. Additional the command should return 0 for success and any non-zero value for failure.

BetterBatch scripts halt on the first error (unless otherwise specified) and all execution is logged (once logfile is set)

Please see the documentation at: http://betterbatch.googlecode.com/hg/betterbatch/docs/index.html

Discuss BetterBatch on the mailing list: http://groups.google.com/group/betterbatch-discuss/topics

Here is a BetterBatch script that shows many of the features:
```
# this sets the log file. The log file CAN be changed 
# during execution (logfile can use variables defined in file 
# as opposed to includes)
- logfile <__script_dir__>\test_bb.log

# the following two 'pseudo' variables allow you to 
# get directory where the script is and the directory
# from which the script was executed.
- echo __script_dir__ pseudo variable-  <__script_dir__>
- echo __working_dir__ pseudo variable- <__working_dir__>

# betterbatch pulls in the environment variables so that these can be used
# by better batch
- echo <computername>

# for example this would be a good way to include machine specific 
# configuration
- if exist <computername>.bb:
  - include <computername>.bb

# or user specific configuration
- if exist <username>.bb:
  - include <username>.bb

# you can define your own variables
- set project_root=<__script_dir__>


# Note - include statements cannot use variables defined in the script (because 
# includes are executed before variable definitions statements are)
- include <__script_dir__>\betterbatch\tests\test_files\basic.bb

# this will not work for example because <project_root> is
# not defined by the time the include will be executed
#- include <project_root>\betterbatch\tests\test_files\basic.bb


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
- add_tools_folder c:\  # you a folder on your machine or in your config


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
- set dir_to_search = {{{echo <windir>}}}
- set found = {{{dir <dir_to_search>\win.ini}}} {{{cd nowhere {*nocheck*}{*echo*}}}}


# commands can be split over many lines in two ways
# using either > or | characters

# > character will result in all text being on one line
- >
    set long_greater=different
    values here
      and here
      
- echo <long_greater>

# | character will result in all text being on many lines (i.e. it is only
# it is kept as is with leading space stripped
- |
    set long_pipe=different
    values here
      and here


- set escaped = {{{escapenewlines <long_pipe>}}}
- echo <escaped>

# scrpits can be ended at any, using an END statment
# it must include error return value and can include an optional message
- end 0, Enough for now - stopping

```