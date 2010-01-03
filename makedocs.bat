@echo off

copy /y configdoc.txt doc_build
sphinx-build -b html doc_build betterbatch\docs

