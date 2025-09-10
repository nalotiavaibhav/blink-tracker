@echo off
echo Starting WellnessAtWork Debug Session...
echo.

REM Try to run the debug executable
if exist "dist\WellnessAtWork-Debug.exe" (
    echo Running debug executable...
    "dist\WellnessAtWork-Debug.exe"
) else if exist "dist\WellnessAtWork.exe" (
    echo Running regular executable...
    "dist\WellnessAtWork.exe"
) else if exist "dist\WellnessAtWork\WellnessAtWork.exe" (
    echo Running executable from directory...
    "dist\WellnessAtWork\WellnessAtWork.exe"
) else (
    echo ERROR: No executable found!
    echo Please build the application first:
    echo   .\build_desktop_exe.ps1
)

echo.
echo Application ended. Check above for any error messages.
pause
