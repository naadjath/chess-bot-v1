@echo off
REM Cree une archive du projet a envoyer sur Google Colab (option B du notebook).
REM Les donnees, les poids et l'environnement virtuel sont exclus : seul le code
REM est necessaire, et l'archive reste legere.

cd /d "%~dp0"

echo.
echo  Creation de l'archive du projet...
echo.

python tools\make_zip.py

echo.
if "%~1"=="" pause
