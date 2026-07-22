@echo off
REM Double-cliquez sur ce fichier pour refabriquer les pages HTML a envoyer
REM a partir des fichiers Markdown mis a jour.

cd /d "%~dp0"

echo.
echo  Regeneration des pages HTML...
echo.

python tools\build_html.py GUIDE-PROJET.md -o "POUR RAJAA\1 - Guide du projet.html"
python tools\build_html.py DEMARRAGE.md    -o "POUR RAJAA\2 - Demarrage Python.html"

echo.
echo  Termine. Les fichiers a envoyer sont dans le dossier "POUR RAJAA".
echo.

REM La pause garde la fenetre ouverte apres un double-clic.
REM On la saute si le script recoit un argument (pratique pour les tests).
if "%~1"=="" pause
