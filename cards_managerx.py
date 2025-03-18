import streamlit as st
import json
import io
from ftplib import FTP
import tempfile
from datetime import datetime
import os
from PIL import Image

# FTP kapcsolat beállítások
FTP_HOST = "185.51.188.85"
FTP_USER = "pairfect"
FTP_PASS = "65Q6sjIhrF"
FTP_DATA_DIR = "public_html/games"

# Jelszó beállítása
CORRECT_PASSWORD = "pairfect2024"

# Ikon csoportok definiálása
icon_groups = {
    "math": {  # Tudomány
        "name": "Tudomány",
        "icons": ['🔬', '🧪', '⚛️', '🧮', '🔭']
    },
    "history": {  # Történelem
        "name": "Történelem",
        "icons": ['⌛', '🏛️', '📜', '👑', '⚔️']
    },
    "language": {  # Nyelvtanulás
        "name": "Nyelvtanulás", 
        "icons": ['🗣️', '🔤', '💭', '📝', '✏️']
    },
    "literature": {  # Irodalom
        "name": "Irodalom",
        "icons": ['📚', '✒️', '📖', '📜', '📗']
    },
    "programming": {  # Informatika
        "name": "Informatika",
        "icons": ['💻', '🤖', '🖥️', '⌨️', '📱']
    },
    "art": {  # Művészet
        "name": "Művészet",
        "icons": ['🎨', '🖼️', '✏️', '🎭', '🎪']
    },
    "music": {  # Szabadidő
        "name": "Szabadidő",
        "icons": ['🎵', '🎹', '🎼', '🎯', '🎲']
    }
}

# Session state inicializálás
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'current_icon' not in st.session_state:
    st.session_state.current_icon = None

if 'icon_category' not in st.session_state:
    st.session_state.icon_category = None

# Fájlnév segédfüggvények
def get_md_filename(txt_filename):
    """Markdown fájlnév generálása a txt fájlnévből"""
    return txt_filename.replace('.txt', '.md')

def get_jpg_filename(txt_filename):
    """JPG fájlnév generálása a txt fájlnévből"""
    return txt_filename.replace('.txt', '.jpg')

def check_password():
    """Jelszó ellenőrzés"""
    if not st.session_state.authenticated:
        st.title('🔒 Kártyacsomag Készítő - Bejelentkezés')
        
        password = st.text_input("Kérlek add meg a jelszót:", type="password")
        
        if st.button("Bejelentkezés"):
            if password == CORRECT_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Helytelen jelszó!")
        
        return False
    
    return True

def connect_ftp():
    """FTP kapcsolat létrehozása és váltás a games mappára"""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        
        try:
            ftp.cwd(FTP_DATA_DIR)
        except:
            # Létrehozzuk a teljes útvonalat, ha nem létezik
            for dir in FTP_DATA_DIR.split('/'):
                try:
                    ftp.cwd(dir)
                except:
                    ftp.mkd(dir)
                    ftp.cwd(dir)
        
        return ftp
    except Exception as e:
        st.error(f"Hiba az FTP kapcsolódás során: {str(e)}")
        raise e

def create_directory_if_not_exists(ftp, path):
    """Könyvtár létrehozása az FTP szerveren, ha nem létezik"""
    try:
        # Próbáljuk meg elérni a könyvtárat
        ftp.cwd(path)
        # Ha sikerült, lépjünk vissza a gyökérbe
        ftp.cwd('/')
    except:
        # Ha nem sikerült elérni, hozzuk létre a könyvtárakat
        current = ''
        for folder in path.split('/'):
            if folder:
                current += '/' + folder
                try:
                    ftp.cwd(current)
                except:
                    try:
                        ftp.mkd(current)
                        st.info(f"Könyvtár létrehozva: {current}")
                    except Exception as e:
                        st.error(f"Nem sikerült létrehozni a könyvtárat: {current}, hiba: {str(e)}")
                        raise

def load_config():
    """JSON konfiguráció betöltése FTP-ről"""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        config_buffer = io.BytesIO()
        
        try:
            # Debug: Kiírjuk az aktuális FTP könyvtárat
            current_dir = ftp.pwd()
            st.info(f"FTP kezdő könyvtár: {current_dir}")
            
            # Könyvtárak létrehozása, ha nem léteznek
            create_directory_if_not_exists(ftp, '/public_html/games')
            
            # Belépés a public_html/games mappába
            ftp.cwd('/public_html/games')
            
            # Debug: Kiírjuk az új könyvtárat
            new_dir = ftp.pwd()
            st.info(f"FTP célkönyvtár: {new_dir}")
            
            # Debug: Listázzuk a könyvtár tartalmát
            st.write("Könyvtár tartalma:")
            st.write(ftp.nlst())
            
            try:
                # data.json letöltése
                st.info(f"data.json betöltése innen: ftp://{FTP_HOST}{new_dir}/data.json")
                ftp.retrbinary('RETR data.json', config_buffer.write)
                config_buffer.seek(0)
                config = json.loads(config_buffer.read().decode('utf-8'))
            except:
                st.warning("Konfiguráció nem található, alapértelmezett beállítások létrehozása...")
                config = {
                    "games": [],
                    "categories": {
                        "math": {
                            "name": "Tudomány",
                            "color": "from-blue-500 to-purple-500"
                        },
                        "history": {
                            "name": "Történelem",
                            "color": "from-orange-500 to-red-500"
                        },
                        "language": {
                            "name": "Nyelvtanulás",
                            "color": "from-green-500 to-teal-500"
                        },
                        "literature": {
                            "name": "Irodalom",
                            "color": "from-pink-500 to-rose-500"
                        },
                        "programming": {
                            "name": "Informatika",
                            "color": "from-violet-500 to-purple-500"
                        },
                        "art": {
                            "name": "Művészet",
                            "color": "from-yellow-500 to-orange-500"
                        },
                        "music": {
                            "name": "Szabadidő",
                            "color": "from-red-500 to-pink-500"
                        }
                    }
                }
                
                # Alapértelmezett konfiguráció mentése
                json_str = json.dumps(config, indent=4, ensure_ascii=False)
                json_buffer = io.BytesIO(json_str.encode('utf-8'))
                ftp.storbinary('STOR data.json', json_buffer)
                st.success("Alapértelmezett konfiguráció létrehozva az FTP szerveren.")
            
            # FTP kapcsolat bezárása
            ftp.quit()
            
            return config
            
        except Exception as e:
            st.error(f"Hiba a könyvtár kezelése során: {str(e)}")
            return None
            
    except Exception as e:
        st.error(f"FTP kapcsolódási hiba: {str(e)}")
        return None

def save_config(config):
    """Konfiguráció mentése az FTP szerverre"""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        
        try:
            # JSON string létrehozása
            json_str = json.dumps(config, indent=4, ensure_ascii=False)
            json_buffer = io.BytesIO(json_str.encode('utf-8'))
            
            # Belépés a public_html/games mappába
            ftp.cwd('public_html/games')
            
            # data.json feltöltése
            ftp.storbinary('STOR data.json', json_buffer)
            
            # FTP kapcsolat bezárása
            ftp.quit()
            
            st.success("Konfiguráció sikeresen mentve az FTP szerverre.")
            return True
            
        except Exception as e:
            st.error(f"Nem sikerült menteni a konfigurációt az FTP szerverre: {str(e)}")
            return False
            
    except Exception as e:
        st.error(f"FTP kapcsolódási hiba: {str(e)}")
        return False

def save_card_pack(filename, content):
    """Kártyacsomag mentése FTP-re"""
    try:
        ftp = connect_ftp()
        with io.BytesIO(content.encode('utf-8')) as buffer:
            ftp.storbinary(f'STOR {filename}', buffer)
        ftp.quit()
    except Exception as e:
        st.error(f"Hiba a kártyacsomag mentése során: {str(e)}")
        raise e

def load_card_pack(filename):
    """Kártyacsomag betöltése FTP-ről"""
    try:
        ftp = connect_ftp()
        content_buffer = io.BytesIO()
        ftp.retrbinary(f'RETR {filename}', content_buffer.write)
        ftp.quit()
        content_buffer.seek(0)
        return content_buffer.read().decode('utf-8')
    except Exception as e:
        st.error(f"Hiba a kártyacsomag betöltése során: {str(e)}")
        raise e

def upload_file_to_ftp(filename, content):
    """Fájl feltöltése az FTP szerverre"""
    try:
        ftp = connect_ftp()
        ftp.storbinary(f'STOR {filename}', content)
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Hiba a fájl feltöltése során: {str(e)}")
        return False

def download_file_from_ftp(filename):
    """Fájl letöltése az FTP szerverről"""
    try:
        ftp = connect_ftp()
        content_buffer = io.BytesIO()
        try:
            ftp.retrbinary(f'RETR {filename}', content_buffer.write)
            content_buffer.seek(0)
            ftp.quit()
            return content_buffer
        except:
            ftp.quit()
            return None
    except Exception as e:
        st.error(f"Hiba a fájl letöltése során: {str(e)}")
        return None

def file_exists_on_ftp(filename):
    """Ellenőrzi, hogy létezik-e a fájl az FTP szerveren"""
    try:
        ftp = connect_ftp()
        files = []
        ftp.retrlines('NLST', files.append)
        ftp.quit()
        return filename in files
    except Exception as e:
        st.error(f"Hiba a fájl ellenőrzése során: {str(e)}")
        return False

def validate_card_content(content):
    """Kártyák tartalmának validálása"""
    if not content.strip():
        return False, "A tartalom nem lehet üres!"
        
    lines = content.strip().split('\n')
    
    if len(lines) < 3:
        return False, "A fájlnak legalább 3 sort kell tartalmaznia:\n1. sor: cím\n2. sor: leírás\n3. sortól: kártya párok"
    
    if not lines[0].strip():
        return False, "Az első sor (cím) nem lehet üres!"
    if ';' in lines[0]:
        return False, "A cím nem tartalmazhat pontosvesszőt!"
        
    if not lines[1].strip():
        return False, "A második sor (leírás) nem lehet üres!"
    if ';' in lines[1]:
        return False, "A leírás nem tartalmazhat pontosvesszőt!"
    
    for i, line in enumerate(lines[2:], 3):
        line = line.strip()
        if not line:  # Üres sorok átugrása
            continue
        if ';' not in line:
            return False, f"Hiba a {i}. sorban: Hiányzó pontosvessző!"
        parts = line.split(';')
        if len(parts) != 2:
            return False, f"Hiba a {i}. sorban: Pontosan egy pontosvesszőt kell tartalmaznia!"
        if not parts[0].strip() or not parts[1].strip():
            return False, f"Hiba a {i}. sorban: Mindkét oldal kitöltése kötelező!"
            
    return True, "OK"

def icon_selector():
    """Vizuális ikon választó egyedi ikon lehetőséggel"""
    st.write("### Válassz ikont")
    
    # Segítség az egyedi ikonokhoz
    with st.expander("Segítség az ikonok használatához"):
        st.markdown("""
        **Hogyan adhatsz meg egyedi ikont?**
        - Használhatsz bármilyen emojit (pl: 🎮, 🎲, 🎯)
        - Az ikon maximum 2 karakter hosszú lehet
        - Windows-on az emoji billentyűzet: Win + .
        - Mac-en az emoji billentyűzet: Cmd + Ctrl + Space
        - Vagy másolhatsz emojit bármilyen emoji gyűjteményből
        """)
    
    # Választás a beépített és egyedi ikon között
    icon_tipus = st.radio(
        "Ikon típusa",
        ["Beépített ikonok", "Egyedi ikon"],
        horizontal=True
    )
    
    if icon_tipus == "Egyedi ikon":
        egyedi_ikon = st.text_input(
            "Add meg az egyedi ikont:",
            max_chars=2,
            help="Itt megadhatsz bármilyen emojit vagy karaktert"
        )
        if egyedi_ikon:
            st.session_state.current_icon = egyedi_ikon
            return egyedi_ikon
    else:
        # Beépített ikonok választása kategóriánként
        selected_category = st.radio(
            "Ikon kategória",
            options=list(icon_groups.keys()),
            format_func=lambda x: icon_groups[x]["name"],
            horizontal=True
        )
        
        cols = st.columns(5)
        selected_icon = None
        
        for idx, icon in enumerate(icon_groups[selected_category]["icons"]):
            if cols[idx].button(
                icon,
                key=f"icon_{icon}",
                help=f"{icon_groups[selected_category]['name']} ikon",
                use_container_width=True
            ):
                selected_icon = icon
                st.session_state.current_icon = icon
                return selected_icon
    
    return None

def ikon_ellenorzes(ikon):
    """Ikon validálása"""
    if not ikon:
        return False, "Az ikon nem lehet üres!"
    if len(ikon) > 2:
        return False, "Az ikon maximum 2 karakter hosszú lehet!"
    return True, "OK"
            
def main():
    """Fő program"""
    st.title('🎴 Kártyacsomag szerkesztő a PairFect-hez V3')
    
    if not check_password():
        return
    
    config = load_config()
    if not config:
        st.error("Nem sikerült a konfigurációs fájl betöltése!")
        return
    
    # Session state inicializálása az ikonhoz, ha még nem létezik
    if 'current_icon' not in st.session_state:
        st.session_state.current_icon = None
    
    categories = list(config['categories'].keys())
    category = st.selectbox(
        'Válassz kategóriát',
        categories,
        format_func=lambda x: config['categories'][x]['name']
    )
    
    edit_mode = st.checkbox('Meglévő csomag szerkesztése')
    
    # Mai dátum meghatározása alapértelmezett értékként
    current_date = datetime.now().strftime('%Y-%m-%d')
    release_date = current_date  # Alapértelmezett: mai dátum
    
    # Változók inicializálása
    filename = ""
    content = """Csomag címe
Feladat leírása
első_oldal;második_oldal"""
    difficulty = 2
    markdown_content = ""
    image_data = None
    
    if edit_mode:
        existing_files = [game['file'] for game in config['games']]
        filename = st.selectbox('Válassz csomagot', existing_files)
        content = load_card_pack(filename)
        game_data = next(game for game in config['games'] if game['file'] == filename)
        difficulty = game_data['defaultDifficulty']
        st.session_state.current_icon = game_data['icon']  # Betöltjük a meglévő ikont
        
        # Meglévő kiadási dátum betöltése, ha van
        release_date = game_data.get('releaseDate', current_date)
        
        # Markdown és kép fájlok nevének meghatározása
        md_filename = get_md_filename(filename)
        jpg_filename = get_jpg_filename(filename)
        
        # Markdown fájl betöltése, ha létezik
        md_file = download_file_from_ftp(md_filename)
        if md_file:
            markdown_content = md_file.read().decode('utf-8')
        
        # Kép fájl betöltése előnézethez, ha létezik
        image_buffer = download_file_from_ftp(jpg_filename)
        if image_buffer:
            st.sidebar.image(image_buffer, caption=f"{jpg_filename} (meglévő kép)", use_container_width=True)
    else:
        filename = st.text_input('Fájl neve', value='', help='Add meg a fájl nevét .txt kiterjesztéssel')
    
    difficulty = st.slider('Nehézségi szint', 1, 5, difficulty)
    
    # Kiadási dátum választó
    release_date = st.date_input(
        'Kiadási dátum',
        value=datetime.strptime(release_date, '%Y-%m-%d').date() if release_date else datetime.now().date(),
        help='A kártyacsomag kiadási dátuma'
    ).strftime('%Y-%m-%d')
    
    # Ikon választó
    selected_icon = icon_selector()
    if selected_icon:  # Ha új ikont választottak
        st.session_state.current_icon = selected_icon
        st.success(f"Választott ikon: {selected_icon}")
    
    # Mindig mutassuk az aktuális ikont, ha van
    if st.session_state.current_icon:
        st.info(f"Aktuális ikon: {st.session_state.current_icon}")
    
    # Kártyacsomag tartalom beállítása
    st.subheader('Kártyák tartalma')
    st.info("""A tartalom formátuma:
1. sor: A csomag címe
2. sor: A feladat leírása
3. sortól: Kártya párok (pontosvesszővel elválasztva)""")
    
    content = st.text_area(
        'Tartalom',
        value=content,
        height=300,
        help='A teljes tartalom, beleértve a címet, leírást és a kártya párokat'
    )
    
    # Markdown fájl feltöltése
    st.subheader('Markdown leírás feltöltése (opcionális)')
    st.info("""A markdown (.md) fájl további információkat tartalmazhat a feladatról.
Ez jelenik meg a Pánik gomb megnyomása után a kártyapárok alatt.""")
    
    uploaded_markdown = st.file_uploader("Válassz egy markdown fájlt", type=["md"], key="md_uploader")
    
    if uploaded_markdown is not None:
        markdown_content = uploaded_markdown.getvalue().decode('utf-8')
        with st.expander("Markdown tartalom előnézete"):
            st.markdown(markdown_content)
    elif markdown_content:  # Ha van már betöltött tartalom, de nincs új feltöltés
        with st.expander("Meglévő markdown tartalom"):
            st.markdown(markdown_content)
    
    # Kép feltöltése
    st.subheader('Kép feltöltése (opcionális)')
    st.info("""A kép a játék fejlécében jelenik meg. Ajánlott méret: 800x200 pixel, JPG formátum.""")
    
    uploaded_image = st.file_uploader("Válassz egy képet", type=["jpg", "jpeg", "png"])
    
    if uploaded_image is not None:
        # Kép előnézet megjelenítése
        image_data = uploaded_image.getvalue()
        st.image(uploaded_image, caption="Feltöltött kép előnézete", use_container_width=True)
    
    # Mentés gomb
    if st.button('Kártyacsomag mentése'):
        if not filename:
            st.error('Add meg a fájl nevét!')
            return
        
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        # Ikon ellenőrzése
        if not st.session_state.current_icon:
            st.error('Válassz ikont!')
            return
        
        is_valid_icon, icon_error = ikon_ellenorzes(st.session_state.current_icon)
        if not is_valid_icon:
            st.error(icon_error)
            return
            
        is_valid, error_msg = validate_card_content(content)
        if not is_valid:
            st.error(error_msg)
            return
            
        try:
            # TXT fájl (kártyacsomag) mentése
            save_card_pack(filename, content)
            
            # Markdown fájl mentése, ha van feltöltve vagy már létezik tartalom
            md_filename = get_md_filename(filename)
            if markdown_content:
                with io.BytesIO(markdown_content.encode('utf-8')) as md_buffer:
                    upload_file_to_ftp(md_filename, md_buffer)
            
            # Kép mentése, ha van feltöltve
            jpg_filename = get_jpg_filename(filename)
            if image_data is not None:
                # Konvertálás JPG formátumba ha szükséges
                if uploaded_image.type != "image/jpeg":
                    try:
                        image = Image.open(io.BytesIO(image_data))
                        output = io.BytesIO()
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGB")
                        image.save(output, format="JPEG", quality=85)
                        output.seek(0)
                        upload_file_to_ftp(jpg_filename, output)
                    except Exception as e:
                        st.error(f"Hiba a kép konvertálása során: {str(e)}")
                        return
                else:
                    with io.BytesIO(image_data) as img_buffer:
                        upload_file_to_ftp(jpg_filename, img_buffer)
            
            # Konfiguráció frissítése
            if not edit_mode:
                new_game = {
                    "file": filename,
                    "defaultDifficulty": difficulty,
                    "category": category,
                    "icon": st.session_state.current_icon,
                    "releaseDate": release_date
                }
                config['games'].append(new_game)
            else:
                for game in config['games']:
                    if game['file'] == filename:
                        game.update({
                            "defaultDifficulty": difficulty,
                            "category": category,
                            "icon": st.session_state.current_icon,
                            "releaseDate": release_date
                        })
            
            save_config(config)
            
            # Sikeres mentés üzenet
            st.success(f'Kártyacsomag sikeresen mentve: {filename}')
            
            # Feltöltött fájlok listázása
            uploaded_files = [filename]
            if markdown_content:
                uploaded_files.append(md_filename)
            if image_data is not None:
                uploaded_files.append(jpg_filename)
                
            st.success(f'Feltöltött fájlok: {", ".join(uploaded_files)}')
            
            # Jelenlegi kártyacsomagok listázása
            st.subheader('Jelenlegi kártyacsomagok:')
            for game in config['games']:
                release_info = f", kiadás: {game.get('releaseDate', 'ismeretlen')}"
                st.write(f"{game['icon']} {game['file']} "
                        f"({config['categories'][game['category']]['name']}, "
                        f"nehézség: {game['defaultDifficulty']}{release_info})")
                
        except Exception as e:
            st.error(f'Hiba történt a mentés során: {str(e)}')
            
if __name__ == '__main__':
    main()