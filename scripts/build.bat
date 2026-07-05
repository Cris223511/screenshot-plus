@echo off
rem construccion del ejecutable portable de screenshot plus. se corre desde
rem la raiz del proyecto o desde scripts/, da igual: el script se ubica
rem solo. el resultado queda en dist\ScreenshotPlus.exe
rem nota: sin tildes a proposito, cmd interpreta los .bat en cp850 y los
rem acentos utf-8 rompen la primera linea del archivo

cd /d "%~dp0.."

echo.
echo [1/3] dependencias de empaquetado...
pip install pyinstaller >nul 2>&1

echo [2/3] el logo se convierte al formato de icono de windows...
python -c "from PIL import Image; img = Image.open('assets/logo/logo.jpg'); img.save('assets/logo/logo.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if errorlevel 1 (
    echo no se pudo convertir el logo; revisa que Pillow este instalado
    exit /b 1
)

echo [3/3] pyinstaller arma el ejecutable...
pyinstaller --noconfirm --onefile --windowed ^
    --name ScreenshotPlus ^
    --icon assets\logo\logo.ico ^
    --add-data "assets;assets" ^
    --add-data "src\i18n\locales;src\i18n\locales" ^
    --add-data "src\ui\themes;src\ui\themes" ^
    --add-data "docs;docs" ^
    main.py

if errorlevel 1 (
    echo la construccion fallo; revisa los mensajes de arriba
    exit /b 1
)

echo.
echo listo: dist\ScreenshotPlus.exe
