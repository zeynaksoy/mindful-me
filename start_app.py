import os
import subprocess
import sys

def main():
    print("="*60)
    print(" Mindful-Me Uygulama Baslatici (Venv)")
    print("="*60)

    # 1. Venv Python yolunu belirle
    venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
    
    if not os.path.exists(venv_python):
        print(f"HATA: Sanal ortam (venv) bulunamadi:\n{venv_python}")
        print("Lutfen projenin ana dizininde 'venv' klasoru olduguna emin olun.")
        input("\nCikmak icin ENTER tusuna basin...")
        sys.exit(1)

    print(f"Sanal ortam (venv) algilandi: {venv_python}")

    # 3. Flask'i venv icerisinden dogrudan run.py uzerinden baslat
    # flask run komutunun bazen FLASK_APP yolunu bulamamasi (NoAppException) sorununu
    # asmak icin direkt olarak python run.py mantigiyla calistiriyoruz.
    command = [venv_python, "run.py"]
    
    print("Uygulama baslatiliyor... Kapatmak icin CTRL+C kisayolunu kullanabilirsiniz.\n")
    print("-" * 60)
    
    try:
        # Flask sunucusunu baslat ve ciktilari doğrudan bu terminale yonlendir
        subprocess.run(command)
    except KeyboardInterrupt:
        print("\nUygulama kullanici tarafindan durduruldu.")
    except Exception as e:
        print(f"\nUygulama baslatilirken HATA OLUSTU: {e}")
        input("\nCikmak icin ENTER tusuna basin...")

if __name__ == "__main__":
    main()
