@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando o ambiente virtual...
    py -3 -m venv .venv 2>nul || python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo Python nao foi encontrado. Instale o Python e tente novamente.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import streamlit, pandas" 2>nul
if errorlevel 1 (
    echo Instalando Streamlit e Pandas...
    ".venv\Scripts\python.exe" -m pip install streamlit pandas
    if errorlevel 1 (
        echo Nao foi possivel instalar as bibliotecas.
        pause
        exit /b 1
    )
)

echo Iniciando o sistema...
".venv\Scripts\python.exe" -m streamlit run app.py
pause
