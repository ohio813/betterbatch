@echo off

copy /y readme.txt doc_build
sphinx-build -b html doc_build betterbatch\docs

