@echo off
echo ============================================================
echo ADVANCED BRAND PROTECTION - Full Pipeline
echo ============================================================
cd /d D:\Projects\brand-protection-poc

REM Set PYTHONPATH to include current directory
set PYTHONPATH=%CD%

echo [1/3] Checking environment...
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please create a .env file with your SUPABASE_URL and SUPABASE_KEY.
    pause
    exit /b 1
)

echo [2/3] Running Full Pipeline (Scrape -^> Enrich -^> Audit)...
echo This may take several minutes depending on enrichment needs.
echo.
python main.py

echo.
echo ============================================================
echo Done! Check the Dashboard to see updated results.
echo ============================================================
pause
