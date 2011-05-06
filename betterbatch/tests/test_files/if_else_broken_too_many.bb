- set my_file=<__script_dir__>\basic.bb

- If Exists <my_file>_:
      echo "BROKEN exists <my_file>
  Else:
        echo string_else
  run:
        shouldn't be here!
