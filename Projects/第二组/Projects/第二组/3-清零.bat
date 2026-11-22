@echo off
chcp 936 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reset.ps1"