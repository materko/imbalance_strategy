@echo off
rem Dvojklik na Windows: spusti webovu aplikaciu pre testerov (docs/WEBAPP.md).
rem Obchadza ExecutionPolicy len pre tento skript, nic v systeme nemeni.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0webapp.ps1" %*
if errorlevel 1 pause
