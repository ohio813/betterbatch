# ================  variables  ======================
# executable sections executed at point of definition
# e.g.   set x = {{{dir /b}}}
#
# variable references are replaced when found??

# the problem is that if a variable isn't used - then
# there should be no warning if it references any variables that are not defined.

# the definition of language here isn't an error UNTIL 
# called in the command step, 
#
#    - set lang = <language>
#    - echo <lang>
#
# for this reason we only want to replace variables when they are used.



- set msg = hi

#- set msg = <msg> + Mark 
#- set msg = <msg> + Mark 
#- echo <msg>
- for line in {{{dir /b }}}:
    - set msg = <msg> + <line>
    - echo <msg>
 
- echo <msg>