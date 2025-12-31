@echo off
REM Script para actualizar el repo en GitHub Pages
REM Uso: update.bat "mensaje de commit"

SET MSG=%1
IF "%MSG%"=="" SET MSG=Actualizacion version profesional v19

echo 📦 Agregando cambios...
git add .

echo 📝 Commit con mensaje: %MSG%
git commit -m "%MSG%"

echo 🚀 Subiendo a GitHub...
git push origin main

echo ✅ Actualización enviada. Revisa tu página en GitHub Pages.
pause
