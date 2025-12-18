"""
Archivo: scraper.py
Descripción: Funciones principales de scraping
"""

import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from config import INSTAGRAM_URLS, SCRAPING_CONFIG
from utils import human_delay, extract_username_from_url, parse_follower_count

def scrape_followers(driver, profile, limit=100):
    """
    Scrapea los followers de un perfil con manejo mejorado de scroll
    """
    print(f"\n🔍 Scrapeando followers de @{profile}...")
    
    # Ir al perfil
    driver.get(INSTAGRAM_URLS['profile'].format(username=profile))
    human_delay(3, 6)
    
    wait = WebDriverWait(driver, SCRAPING_CONFIG['default_timeout'])
    followers = set()

    try:
        # Verificar que el perfil existe
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        print("✅ Perfil cargado correctamente")
    except TimeoutException:
        print("❌ No se pudo cargar el perfil. Puede ser privado o no existe.")
        return set()

    # --- PASO 1: Abrir el modal de seguidores ---
    try:
        followers_link = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers')]"))
        )
        driver.execute_script("arguments[0].click();", followers_link)
        print("✅ Modal de followers abierto")
        time.sleep(3)
    except TimeoutException:
        print("❌ No se pudo abrir el modal de followers")
        return set()

    # --- PASO 2: Detectar el contenedor con scroll ---
    modal = None
    try:
        posibles = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@class]")

        for div in posibles:
            try:
                scroll_height = driver.execute_script("return arguments[0].scrollHeight", div)
                client_height = driver.execute_script("return arguments[0].clientHeight", div)

                if scroll_height > client_height + 100:
                    modal = div
                    print("🌀 Contenedor desplazable detectado")
                    break
            except Exception:
                continue

    except Exception as e:
        print(f"⚠️ Error buscando contenedor: {e}")

    if not modal:
        print("❌ No se encontró el contenedor desplazable del modal.")
        return set()

    # --- PASO 3: Scroll y extracción de usuarios ---
    print(f"📊 Iniciando extracción (límite: {limit})...")

    last_scroll_position = 0
    no_change_count = 0

    while len(followers) < limit:
        try:
            # Extraer usuarios visibles
            links = modal.find_elements(By.XPATH, ".//a[contains(@href,'/')]")

            for a in links:
                try:
                    href = a.get_attribute("href")
                    username = extract_username_from_url(href)
                    
                    if username and username not in followers:
                        followers.add(username)
                except Exception:
                    continue

            current_count = len(followers)
            print(f"📢 Followers capturados: {current_count}/{limit}", end="\r")

            if current_count >= limit:
                print(f"\n✅ Límite alcanzado: {limit} followers")
                break

            # Hacer scroll
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;",
                modal
            )

            time.sleep(random.uniform(
                SCRAPING_CONFIG['scroll_delay_min'],
                SCRAPING_CONFIG['scroll_delay_max']
            ))

            new_scroll_position = driver.execute_script(
                "return arguments[0].scrollTop",
                modal
            )

            # Verificar si hubo cambio
            if new_scroll_position == last_scroll_position:
                no_change_count += 1
                print(f"\n⚠️ Sin cambios en scroll ({no_change_count}/{SCRAPING_CONFIG['no_change_max']})")

                if no_change_count >= SCRAPING_CONFIG['no_change_max']:
                    print("🛑 No hay más followers para cargar")
                    break

                # Intento adicional: scroll más agresivo
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollTop + 1000;",
                    modal
                )
                time.sleep(2)
            else:
                no_change_count = 0
                last_scroll_position = new_scroll_position

        except Exception as e:
            print(f"\n⚠️ Error durante extracción: {e}")
            time.sleep(2)
            continue

    print(f"\n✅ Extracción completada: {len(followers)} followers encontrados")
    return followers


def get_followers_count(driver, username):
    """Obtiene el número de followers de un usuario"""
    try:
        url = INSTAGRAM_URLS['profile'].format(username=username)
        driver.get(url)
        human_delay(2, 4)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "header"))
        )

        # Método 1: Buscar span con title
        try:
            spans_with_title = driver.find_elements(By.XPATH, "//span[@title]")
            
            for span in spans_with_title:
                title = span.get_attribute('title')
                if title and title.replace(',', '').replace('.', '').isdigit():
                    parent_text = ''
                    try:
                        parent = span.find_element(By.XPATH, "./parent::*")
                        parent_text = parent.text.lower()
                    except:
                        pass

                    if any(word in parent_text for word in ['seguidores', 'followers', 'follower']):
                        follower_count = parse_follower_count(title)
                        if follower_count is not None:
                            print(f"  ✅ @{username}: {follower_count:,} followers")
                            return follower_count
        except Exception:
            pass

        # Método 2: Buscar en metadata
        try:
            import re
            meta_element = driver.find_element(
                By.XPATH,
                "//meta[@property='og:description']"
            )
            content = meta_element.get_attribute('content')

            patterns = [
                r'([\d,\.KMB]+)\s+[Ff]ollowers?',
                r'([\d,\.KMB]+)\s+[Ss]eguidores?'
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    follower_text = match.group(1)
                    follower_count = parse_follower_count(follower_text)
                    if follower_count is not None:
                        print(f"  ✅ @{username}: {follower_count:,} followers")
                        return follower_count
        except NoSuchElementException:
            pass

        # Método 3: Buscar en el HTML (JSON interno)
        try:
            import re
            page_source = driver.page_source

            patterns = [
                r'"edge_followed_by":\{"count":(\d+)\}',
                r'"follower_count":(\d+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, page_source)
                if match:
                    follower_count = int(match.group(1))
                    print(f"  ✅ @{username}: {follower_count:,} followers")
                    return follower_count
        except Exception:
            pass

        print(f"  ⚠️ @{username}: No se pudo obtener followers")
        return None

    except TimeoutException:
        print(f"  ❌ @{username}: Timeout")
        return None
    except Exception as e:
        print(f"  ❌ @{username}: Error {e}")
        return None


def get_bio(driver, username):
    """Obtiene la biografía (descripción) y enlaces del perfil de `username`."""
    try:
        url = INSTAGRAM_URLS['profile'].format(username=username)
        driver.get(url)
        human_delay(2, 4)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "header"))
        )

        # Método: meta og:description (suele contener resumen)
        try:
            meta = driver.find_element(By.XPATH, "//meta[@property='og:description']")
            content = meta.get_attribute('content') or ''
            if content:
                import re
                candidate = content.split('•')[0].strip()
                candidate = re.sub(r'\s*\(@[\w\.]+\)', '', candidate).strip()
                links = []
                try:
                    header = driver.find_element(By.TAG_NAME, 'header')
                    for a in header.find_elements(By.TAG_NAME, 'a'):
                        href = a.get_attribute('href')
                        if href:
                            links.append(href)
                except Exception:
                    pass
                if candidate:
                    print(f"  ✅ @{username}: Biografía encontrada (meta)")

                    return {'bio': candidate, 'links': links, 'raw': content}
        except Exception:
            pass
            
        # Método 2: buscar en el header elementos <span> o <div> con texto
        try:
            header = driver.find_element(By.TAG_NAME, 'header')
            # Buscar spans y divs que parezcan contener la bio
            candidates = header.find_elements(By.XPATH, ".//span|.//div")
            best = ''
            for el in candidates:
                try:
                    txt = el.text.strip()
                    if not txt:
                        continue
                    low = txt.lower()
                    if any(k in low for k in ['followers', 'seguidores', 'posts', 'siguiendo']):
                        continue
                    if len(txt) > len(best):
                        best = txt
                except Exception:
                    continue

            links = []
            try:
                for a in header.find_elements(By.XPATH, ".//a"):
                    href = a.get_attribute('href')
                    if href:
                        links.append(href)
            except Exception:
                pass

            if best:
                print(f"  ✅ @{username}: Biografía encontrada (header)")
                return {'bio': best, 'links': links, 'raw': best}
        except Exception:
            pass

        # Método 3: meta name="description"
        try:
            meta = driver.find_element(By.XPATH, "//meta[@name='description']")
            content = meta.get_attribute('content') or ''
            if content:
                print(f"  ✅ @{username}: Biografía encontrada (meta name=description)")
                return {'bio': content.strip(), 'links': [], 'raw': content}
        except Exception:
            pass

        print(f"  ⚠️ @{username}: No se encontró biografía")
        return {'bio': None, 'links': [], 'raw': None}

    except TimeoutException:
        print(f"  ❌ @{username}: Timeout")
        return {'bio': None, 'links': [], 'raw': None}
    except Exception as e:
        print(f"  ❌ @{username}: Error {e}")
        return {'bio': None, 'links': [], 'raw': None}


def collect_followers_data(driver, usernames_set, max_profiles=None):
    """
    Recopila el número de followers de cada username
    """
    print("\n" + "=" * 60)
    print("📊 RECOPILANDO DATOS DE FOLLOWING")
    print("=" * 60)

    followers_data = []
    usernames_list = list(usernames_set)

    if max_profiles:
        usernames_list = usernames_list[:max_profiles]

    total = len(usernames_list)
    print(f"Total de perfiles a procesar: {total}\n")

    followers_data_profile = []

    for index, username in enumerate(usernames_list, 1):
        print(f"[{index}/{total}] Procesando @{username}...")

        follower_count = get_followers_count(driver, username)
        follower_biography = get_bio(driver, username)

        followers_data.append({
            'username': username,
            'followers': follower_count
        })

        followers_data_profile.append({
            'username': username,
            'followers': follower_count,
            'bio': follower_biography.get('bio'),
            'links': follower_biography.get('links'),
            'raw': follower_biography.get('raw')
        })

        if index < total:
            human_delay()



    # Estadísticas finales
    successful = sum(1 for item in followers_data if item['followers'] is not None)
    failed = total - successful

    print("\n" + "=" * 60)
    print(f"✅ Completado: {successful}/{total} perfiles exitosos")
    if failed > 0:
        print(f"⚠️ Fallidos: {failed} perfiles")
    print("=" * 60 + "\n")

    return followers_data,followers_data_profile

