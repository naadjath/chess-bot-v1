@echo off
REM Double-cliquez sur ce fichier pour lancer l'application de jeu.
REM Le navigateur s'ouvre tout seul sur http://127.0.0.1:8000

cd /d "%~dp0"
python -m src.app.server

echo.
echo  Le serveur s'est arrete.
if "%~1"=="" pause
