@echo off
rem Capstan launcher
pushd "%~dp0app"
start "" pythonw.exe main.py %*
popd
