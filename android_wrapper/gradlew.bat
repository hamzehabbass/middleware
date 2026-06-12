@echo off
setlocal enabledelayedexpansion

set DIR=%~dp0

if not exist "%DIR%gradle\wrapper\gradle-wrapper.jar" (
    echo ERROR: gradle-wrapper.jar not found in %DIR%gradle\wrapper\
    exit /b 1
)

java -cp "%DIR%gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain %*
exit /b %ERRORLEVEL%
