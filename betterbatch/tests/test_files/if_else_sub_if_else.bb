- set my_file=<__script_dir__>\basic.bb

- If Exists <my_file>:
    - if exists otherfile:
        echo sub_if_else not exists!
      else:
        echo sub_if_else
  Else:
    echo BROKEN not exists <my_file>_

