- set my_file=<__script_dir__>\basic.bb

- If Exists <my_file>:
        echo string_do
  Else:
        echo BROKEN not exists <my_file>_

