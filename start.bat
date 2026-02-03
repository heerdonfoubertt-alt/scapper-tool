@echo off
chcp 65001 >nul
cls
echo ============================================
echo   INFLUENCER SCRAPER - Version FastAPI
echo ============================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERREUR: Python n'est pas installé
    pause
    exit /b 1
)

echo [1/3] Vérification des dépendances...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installation des dépendances Python...
    pip install -r requirements.txt --break-system-packages
    if errorlevel 1 (
        echo ⚠️  Installation avec --break-system-packages a échoué
        echo Tentative sans le flag...
        pip install -r requirements.txt
    )
)

echo [2/3] Vérification des dossiers...
if not exist templates mkdir templates
if not exist static mkdir static

echo [3/3] Démarrage du serveur...
echo.
echo 🚀 Lancement en cours...
echo 📍 Interface web: http://localhost:3000
echo 📚 Documentation API: http://localhost:3000/docs
echo.
echo Appuyez sur Ctrl+C pour arrêter le serveur
echo ============================================
echo.

python app.py

pause
