@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m streamlit run app.py
) else if exist "C:\Users\Mufha\anaconda3\envs\penv\python.exe" (
  "C:\Users\Mufha\anaconda3\envs\penv\python.exe" -m streamlit run app.py
) else (
  py -m streamlit run app.py
)
