import os
import sys

def main():
    print("=" * 60)
    print(" Mindful-Me Programatik Çeviri Derleyici (Babel)")
    print("=" * 60)

    try:
        from babel.messages.pofile import read_po
        from babel.messages.mofile import write_mo
    except ImportError:
        print("HATA: 'babel' kütüphanesi yüklü değil!")
        print("Lütfen sanal ortamınızın (venv) aktif olduğundan emin olun veya şu komutla yükleyin:")
        print("pip install babel")
        input("\nÇıkmak için ENTER tuşuna basın...")
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    translations_dir = os.path.join(base_dir, 'app', 'translations')
    
    languages = ['tr', 'en']
    compiled_count = 0

    for lang in languages:
        po_path = os.path.join(translations_dir, lang, 'LC_MESSAGES', 'messages.po')
        mo_path = os.path.join(translations_dir, lang, 'LC_MESSAGES', 'messages.mo')

        if os.path.exists(po_path):
            print(f"[{lang.upper()}] Çeviri dosyası okunuyor: {po_path}")
            try:
                with open(po_path, 'r', encoding='utf-8') as f:
                    catalog = read_po(f)
                
                os.makedirs(os.path.dirname(mo_path), exist_ok=True)
                
                with open(mo_path, 'wb') as f:
                    write_mo(f, catalog)
                print(f">>> BAŞARILI: {mo_path} derlendi.\n")
                compiled_count += 1
            except Exception as e:
                print(f">>> HATA: Derleme sırasında hata oluştu: {e}\n")
        else:
            print(f"[{lang.upper()}] HATA: Kaynak dosya bulunamadı: {po_path}\n")

    print("=" * 60)
    print(f"Derleme tamamlandı! Başarıyla derlenen katalog sayısı: {compiled_count}")
    print("=" * 60)
    pass

if __name__ == '__main__':
    main()
