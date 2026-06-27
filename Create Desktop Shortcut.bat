@echo off
set SCRIPT="%TEMP%\CreateShortcut.vbs"
set TARGET="%~dp0launch_app.pyw"
set SHORTCUT="%USERPROFILE%\Desktop\ExpenseIQ.lnk"

echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = %SHORTCUT% >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = %TARGET% >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "ExpenseIQ - Expense Tracker" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo Shortcut created on your Desktop!
pause
