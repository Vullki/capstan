@echo off
rem Run with a console and the WebView dev tools (for debugging)
pushd "%~dp0app"
python.exe main.py --debug
popd
