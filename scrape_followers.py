"""
Archivo: scrape_followers.py (PRINCIPAL)
Descripción: Orquestador principal del scraping
"""

from browser import init_browser
from auth import load_credentials, load_cookies, login, verify_session
from scraper import scrape_followers, collect_followers_data
from file_manager import save_followers_txt, save_followers_data_json, save_profile_data_excel
from benford_analysis import analizar_benford
from utils import human_delay


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("  INSTAGRAM FOLLOWERS SCRAPER + BENFORD ANALYSIS")
    print("="*60 + "\n")
    
    # Cargar credenciales
    username, password = load_credentials()
    
    # Inicializar navegador
    print("Iniciando navegador...")
    driver = init_browser()
    
    try:
        # Autenticación
        print("\nAutenticando...")
        cookies_loaded = load_cookies(driver)
        
        if not cookies_loaded:
            print(" Login manual requerido...")
            if not login(driver, username, password):
                print(" Login fallido")
                return
        else:
            driver.get("https://www.instagram.com/")
            human_delay(3, 4)
            
            if not verify_session(driver):
                print(" Cookies inválidas, reintentando login...")
                if not login(driver, username, password):
                    print(" Login fallido")
                    return
        
        # Solicitar datos
        print("\n" + "="*60)
        profile = input(" Ingresa el username objetivo: ").strip()
        limit = int(input(" Límite de seguidores a scrapear: "))
        
        # Scraping de followers
        print("\n" + "="*60)
        print("FASE 1: EXTRACCIÓN DE FOLLOWERS")
        print("="*60)
        followers = scrape_followers(driver, profile, limit)
        
        if not followers:
            print("No se encontraron followers.")
            return
        
        # Guardar lista de followers
        save_followers_txt(followers, profile)
        
        # Recopilar datos de followers
        print("\n" + "="*60)
        print("FASE 2: RECOPILACIÓN DE DATOS")
        print("="*60)
        followers_data, followers_data_profile = collect_followers_data(driver, followers, max_profiles=100)
        # Guardar datos JSON
        json_file = save_followers_data_json(followers_data, profile)
        #Guardar datos del perfil detallado



        excel_file_profile = save_profile_data_excel(followers_data_profile, profile)


        # Análisis de Benford
        print("\n" + "="*60)
        print("FASE 3: ANÁLISIS DE BENFORD")
        print("="*60)
        benford_results = analizar_benford(json_file, profile)
        print("Se guardan los resultados de los datos de los perfiles detallados")
        if benford_results:
            print("\n" + "="*60)
            print(" PROCESO COMPLETADO EXITOSAMENTE")
            print("="*60)
            print("\n Archivos generados:")
            print(f"   • Lista de followers (TXT)")
            print(f"   • Datos de followers (JSON): {json_file}")
            
            print(f"   • Datos de perfil detallado (XLSX): {excel_file_profile}")

            print(f"   • Análisis Benford (XLSX): {benford_results['excel']}")
            print(f"   • Gráfica Benford (PNG): {benford_results['png']}")
            print("\n" + "="*60)
        
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n  Presiona ENTER para cerrar el navegador...")
        driver.quit()
        print(" Navegador cerrado. Fin del programa.")
if __name__ == "__main__":
    main()