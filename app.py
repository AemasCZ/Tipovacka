#!/usr/bin/env python3
"""
🔧 Rychlá diagnostika a oprava Streamlit aplikace
Spusť: python fix_app.py
"""

import os
import sys
import shutil
from pathlib import Path


def check_file_exists(filepath: str) -> bool:
    """Zkontroluje existenci souboru"""
    return Path(filepath).exists()


def backup_file(filepath: str):
    """Vytvoří zálohu souboru"""
    if check_file_exists(filepath):
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Záloha vytvořena: {backup_path}")
        return True
    return False


def main():
    print("🔍 Diagnostika Streamlit Tipovačky")
    print("=" * 50)
    
    # 1. Kontrola Python verze
    print("\n1️⃣ Kontrola Python verze...")
    python_version = sys.version_info
    if python_version >= (3, 8):
        print(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"   ❌ Python {python_version.major}.{python_version.minor} - potřebuješ 3.8+")
        return
    
    # 2. Kontrola souborů
    print("\n2️⃣ Kontrola souborů...")
    required_files = {
        "app.py": True,
        "ui_layout.py": True,
        "ui_menu.py": True,
        "requirements.txt": True,
        ".env": False,  # Nepovinný - může být v secrets
    }
    
    all_ok = True
    for file, required in required_files.items():
        exists = check_file_exists(file)
        if exists:
            print(f"   ✅ {file}")
        elif required:
            print(f"   ❌ {file} - CHYBÍ (KRITICKÉ)")
            all_ok = False
        else:
            print(f"   ⚠️  {file} - chybí (není kritické)")
    
    if not all_ok:
        print("\n❌ Některé důležité soubory chybí!")
        return
    
    # 3. Kontrola requirements
    print("\n3️⃣ Kontrola dependencies...")
    try:
        import streamlit
        print(f"   ✅ streamlit {streamlit.__version__}")
    except ImportError:
        print("   ❌ streamlit není nainstalován")
        print("      Spusť: pip install streamlit")
    
    try:
        import supabase
        print(f"   ✅ supabase")
    except ImportError:
        print("   ❌ supabase není nainstalován")
        print("      Spusť: pip install supabase")
    
    try:
        import dotenv
        print(f"   ✅ python-dotenv")
    except ImportError:
        print("   ❌ python-dotenv není nainstalován")
        print("      Spusť: pip install python-dotenv")
    
    # 4. Kontrola env variables
    print("\n4️⃣ Kontrola environment variables...")
    from dotenv import load_dotenv
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if supabase_url:
        print(f"   ✅ SUPABASE_URL nalezena")
    else:
        print(f"   ❌ SUPABASE_URL chybí v .env")
    
    if supabase_key:
        print(f"   ✅ SUPABASE_ANON_KEY nalezena")
    else:
        print(f"   ❌ SUPABASE_ANON_KEY chybí v .env")
    
    # 5. Nabídka opravy
    print("\n5️⃣ Opravy...")
    
    if check_file_exists("ui_layout.py") and check_file_exists("ui_layout_fixed.py"):
        print("   Nalezena opravená verze ui_layout.py")
        response = input("   Chceš nahradit ui_layout.py za opravenou verzi? (y/n): ")
        
        if response.lower() == 'y':
            backup_file("ui_layout.py")
            shutil.copy2("ui_layout_fixed.py", "ui_layout.py")
            print("   ✅ ui_layout.py nahrazena opravenou verzí")
    
    # 6. Kontrola pages/
    print("\n6️⃣ Kontrola stránek...")
    pages_dir = Path("pages")
    if pages_dir.exists():
        pages = list(pages_dir.glob("*.py"))
        print(f"   ✅ Nalezeno {len(pages)} stránek:")
        for page in sorted(pages):
            print(f"      - {page.name}")
        
        # Zkontroluj diagnostickou stránku
        if not check_file_exists("pages/_Diagnostika.py") and check_file_exists("pages_Diagnostika.py"):
            response = input("\n   Chceš přidat diagnostickou stránku? (y/n): ")
            if response.lower() == 'y':
                shutil.copy2("pages_Diagnostika.py", "pages/_Diagnostika.py")
                print("   ✅ Diagnostická stránka přidána")
    else:
        print(f"   ❌ Složka pages/ neexistuje")
    
    # 7. Kontrola assets/
    print("\n7️⃣ Kontrola assets...")
    assets_dir = Path("assets")
    if assets_dir.exists():
        images = list(assets_dir.glob("*.jpeg")) + list(assets_dir.glob("*.png"))
        print(f"   ✅ Nalezeno {len(images)} obrázků")
        for img in images:
            size_kb = img.stat().st_size / 1024
            print(f"      - {img.name} ({size_kb:.1f} KB)")
    else:
        print(f"   ⚠️  Složka assets/ neexistuje (není kritické)")
    
    # 8. Doporučení
    print("\n" + "=" * 50)
    print("📋 DOPORUČENÍ PRO KOLEGU:")
    print("=" * 50)
    print("""
1. Vyčisti Chrome cache (Ctrl+Shift+Del)
2. Zkus Incognito režim (Ctrl+Shift+N)
3. Zkus jiný prohlížeč (Firefox, Edge)
4. Zkontroluj volné místo na disku (min 1GB)
5. Otevři Developer Tools (F12) a zkontroluj Console
6. Pokud vidíš FILE_ERROR_NO_SPACE → vyčisti cache

Pro spuštění aplikace:
    streamlit run app.py

Pro zobrazení diagnostiky:
    Otevři aplikaci a přejdi na stránku "_Diagnostika"
""")
    
    print("\n✅ Diagnostika dokončena!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostika přerušena uživatelem")
    except Exception as e:
        print(f"\n❌ Chyba při diagnostice: {e}")
        import traceback
        traceback.print_exc()
