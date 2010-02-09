- md <__script_dir__>\doc_build {*nocheck*}
- copy /y <__script_dir__>\*.txt <__script_dir__>\doc_build
- sphinx-build -b html <__script_dir__>\doc_build <__script_dir__>\betterbatch\docs

