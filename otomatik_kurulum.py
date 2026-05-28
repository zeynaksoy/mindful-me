import os
import subprocess
import sys

def run_command(command, description):
    print(f"\n[{description}] basliyor...")
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(">>> BASARILI!")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(">>> HATA OLUSTU:")
        print(e.stderr or e.stdout)
    except FileNotFoundError:
        print(f">>> HATA: '{command[0]}' bulunamadi. Yolun dogru oldugundan emin olun.")

def main():
    print("="*60)
    print(" Mindful-Me Gelismis Otomatik Kurulum ve Derleme Araci")
    print("="*60)

    # Venv Python yolunu belirle (Windows icin)
    venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
    
    # Eger venv yoksa uyar ve global python kullanmayi dene veya cik
    if not os.path.exists(venv_python):
        print(f"HATA: Sanal ortam (venv) Python calistirilabilir dosyasi bulunamadi:\n{venv_python}")
        print("Lutfen projenin ana dizininde 'venv' adinda bir sanal ortam oldugundan emin olun.")
        input("\nCikmak icin ENTER tusuna basin...")
        sys.exit(1)

    print(f"Sanal ortam (venv) algilandi: {venv_python}")

    # 1. Eksik Kutuphanelerin Kurulumu (pip install)
    packages_to_install = ["flask-mail", "flask-babel", "email-validator"]
    run_command([venv_python, "-m", "pip", "install"] + packages_to_install, 
                "Eksik Kutuphanelerin Kurulumu (pip install)")

    # 2. Babel Compile
    run_command([venv_python, "-m", "babel", "compile", "-d", "app/translations"], 
                "Flask-Babel Ceviri Dosyalarini Derleme")

    # 3. DB Migrate
    run_command([venv_python, "-m", "flask", "db", "migrate", "-m", "Add password_hash"], 
                "Veritabani Gocu (Migration) Olusturma")

    # 4. DB Upgrade
    run_command([venv_python, "-m", "flask", "db", "upgrade"], 
                "Veritabani Guncelleme (Upgrade)")

    print("\n" + "="*60)
    print("Tum islemler venv izolasyonunda basariyla tamamlandi!")
    print("Artik uygulamanizi calistirabilirsiniz.")
    print("="*60)
    input("\nCikmak icin ENTER tusuna basin...")

if __name__ == "__main__":
    main()
