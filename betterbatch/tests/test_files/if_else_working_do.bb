- set my_file = <__script_dir__>\basic.bb

- If Exists <my_file>:
    - echo "exists" <my_file>
  Else:
    - echo correct
