@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0fix-git-permission.ps1" %*
