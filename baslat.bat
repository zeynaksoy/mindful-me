@echo off
TITLE Mindful-Me Baslatici
echo ==============================================
echo Mindful-Me Uygulamasi Baslatiliyor...
echo ==============================================

:: Proje dizinine gec (Her ihtimale karsi dogru klasorde calismasini saglar)
cd /d "C:\Users\ASUS\Desktop\mindful-me"

:: Venv icerisindeki python.exe'yi dogrudan cagirarak uygulamayi baslat
"C:\Users\ASUS\Desktop\mindful-me\venv\Scripts\python.exe" run.py

echo.
echo Uygulama calismayi durdurdu veya bir hata ile karsilasildi.
pause
