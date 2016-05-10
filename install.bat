@echo off

:: SoundCast installer batch file
:: =======================================
:: Full install instructions are always at
:: http://soundcast.readthedocs.io

set ZIPINSTALLER='http://www.7-zip.org/a/7z1600-x64.msi'
set POWERSHELL=%windir%\System32\WindowsPowerShell\v1.0\powershell.exe

:: ------------------------------
:: Test for python in system path

echo.
echo Checking for python...
where python.exe || goto :python-error

echo.
echo Checking for pip...
where pip.exe || goto :python-error

echo.
echo Installing python libraries...
pip install -r requirements.txt || goto :python-error

:: ----------------
:: Test for 7-zip

:test-zip
echo.
echo Checking for 7-Zip...
where 7z.exe || goto :zip-missing
goto :zip-ok

:zip-missing
echo 7-Zip not found. Installing...
"%POWERSHELL%" -Command "(New-Object Net.WebClient).DownloadFile(%ZIPINSTALLER%, '7z-setup.msi')" || :zip-error

7z-setup.msi /passive
setx path "%PATH%;C:\Program Files\7-Zip"
set PATH=%PATH%;C:\Program Files\7-Zip
goto :test-zip

:zip-ok

goto :success

:: =======================================
:python-error
echo.
echo Failed with error code #%errorlevel%
echo You need to install or set up Python. Anaconda Python is easiest:
echo https://www.continuum.io/downloads
echo.
echo Ensure python and pip are in your PATH and try again.
exit /b %errorlevel

:zip-error
echo.
echo Failed with error code #%errorlevel%
echo You need to install 7-zip and add it to your PATH
echo http://www.7-zip.org
echo.
echo Install it and try again.
exit /b %errorlevel


:: =======================================
:success
echo.
echo Done!

