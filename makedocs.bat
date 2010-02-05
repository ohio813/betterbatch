@echo off

copy /y *.txt doc_build
sphinx-build -b html doc_build betterbatch\docs

