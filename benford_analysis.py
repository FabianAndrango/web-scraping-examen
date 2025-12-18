"""
Archivo: benford_analysis.py
Descripción: Análisis de la Ley de Benford
"""

import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from config import RESULTS_DIR


def cargar_json_instagram(ruta):
    """Carga JSON con múltiples formatos"""
    with open(ruta, "r", encoding="utf-8") as f:    #Abrir un archivo en forma de lectura
        data = json.load(f)                         # Cargar los datos del archivo JSON

    if isinstance(data, list):      #Determinamos si los datos son una lista
        return pd.DataFrame(data)

    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):    #Determinamos si es un diccionario y si contiene la clave data que es una lista
        return pd.DataFrame(data["data"])

    for key in data:    #Iteramos sobre las claves del diccionario 
        if isinstance(data[key], list) and len(data[key]) > 0 and isinstance(data[key][0], dict):   #Verificamos si el valor es una lisya y si el tamaños es mayor a cero
            return pd.DataFrame(data[key])

    if isinstance(data, dict):  #Verificamos si es un diccionario   
        return pd.DataFrame([data])  #Devolvemos un DataFrame con una sola fila

    raise ValueError(" No se pudo interpretar la estructura del JSON.")


def primer_digito_valor(valor):                 
    """Extrae el primer dígito de un valor"""
    if pd.isna(valor):  #Verificamos si el valor es NaN
        return np.nan
    s = str(valor).strip().replace(",", "") #Convertimos el valor a cadena y quitamos espacios y comas.
    m = re.search(r"[1-9]", s)      #Buscamos el patron de digitos del 1 al 9 en la cadena
    if m:                       #Si encontramos un valor no nulo en m
        return int(m.group(0))  #Devolvemos el primer digito encontrado convertido a entero
    return np.nan


def analizar_benford(json_file, profile):
    """
    Analiza datos con la Ley de Benford y genera gráfica
    """
    print("\n" + "=" * 60)
    print("ANÁLISIS LEY DE BENFORD")
    print("=" * 60)
    
    # Cargar datos del archivo JSON
    df = cargar_json_instagram(json_file)
    
    # Detectar columna de followers
    possible_cols = [c for c in df.columns if "follow" in c.lower()]
    # Si no se encuentra ninguna columna que contenga "follow" en su nombre
    if not possible_cols:
        print(" No se encontró columna de followers")
        return None
    # Si hay múltiples columnas que contienen "follow", se elige la primera
    follow_col = possible_cols[0]
    
    # Preparar datos
    df_clean = pd.DataFrame()       #Crear un DataFrame vacío para almacenar los datos limpios
    df_clean["username"] = df[df.columns[0]].astype(str)    # Asignar la primera columna del DataFrame original como nombres de usuario y transformarla a cadena
    df_clean["followers"] = df[follow_col]                  # Asignar la columna de seguidores detectada
    df_clean["primer_digito"] = df_clean["followers"].apply(primer_digito_valor)    # Extraer el primer dígito de los seguidores
    
    # Aplicar Benford
    digitos = np.arange(1, 10)  #Crear un array con los dígitos del 1 al 9 
    conteos = df_clean["primer_digito"].value_counts().reindex(digitos, fill_value=0)  #Contar la frecuencia de cada dígito y reindexar para asegurar que todos los dígitos del 1 al 9 estén presentes
    total_validos = conteos.sum()   #Calcular el total de valores válidos (no NaN)
    
    porcentaje_real = (conteos / total_validos) * 100                           #Calcular el porcentaje real de cada dígito
    porcentaje_benford = np.array([np.log10(1 + 1/d) * 100 for d in digitos])   #Calcular el porcentaje esperado según la Ley de Benford
    
    comparacion = pd.DataFrame({
        "Dígito": digitos,
        "Conteo": conteos.values,
        "Frecuencia_Real_%": porcentaje_real.round(3).values,
        "Benford_%": porcentaje_benford.round(3),
        "Diferencia_%": (porcentaje_real - porcentaje_benford).round(3)
    })
    
    # Guardar Excel
    excel_file = RESULTS_DIR / f"benford_{profile}.xlsx"
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:#Abrir un escritor de Excel usando openpyxl como motor
        df_clean.to_excel(writer, sheet_name="datos_originales", index=False)#Guardar los datos originales en una hoja llamada "datos_originales"
        comparacion.to_excel(writer, sheet_name="comparacion_benford", index=False)# Guardar la comparación de Benford en otra hoja llamada "comparacion_benford"
    
    print(f" Excel generado: {excel_file}")
    
    # Generar gráfica y guardar PNG
    png_file = RESULTS_DIR / f"benford_{profile}.png"
    # Crear la gráfica y el eje
    fig, ax = plt.subplots(figsize=(10, 6))
    # Configurar la gráfica
    bar_width = 0.35
    # Crear barras para los datos reales 
    ax.bar(digitos - bar_width/2,
           comparacion["Frecuencia_Real_%"],
           width=bar_width,
           label="Datos Reales (%)",
           alpha=0.85,
           color='#1f77b4')
    # Crear línea para la Ley de Benford
    ax.plot(digitos,
            comparacion["Benford_%"],
            marker="o",
            linewidth=2,
            label="Ley de Benford (%)",
            color='#ff7f0e')
    # Configurar etiquetas y título
    ax.set_title(f"Ley de Benford - @{profile}", fontsize=14, fontweight='bold')    #Establecer el título de la gráfica
    ax.set_xlabel("Primer dígito", fontsize=12)    #Establecer la etiqueta del eje x
    ax.set_ylabel("Frecuencia (%)", fontsize=12)   #Establecer la etiqueta del eje y
    ax.set_xticks(digitos)                          #Establecer las marcas del eje x
    ax.grid(alpha=0.3, linestyle='--')              #Configurar la cuadrícula
    ax.legend(fontsize=10)                          #Mostrar la leyenda de la gráfica
    
    plt.tight_layout()#Ajustar el diseño para que no se solapen los elementos
    fig.savefig(png_file, dpi=300, bbox_inches="tight")#Guardar la gráfica como archivo PNG
    plt.close()#Cerrar la figura para liberar memoria
    
    print(f" Gráfica generada: {png_file}")
    print("=" * 60 + "\n")
    
    return {
        'excel': excel_file,
        'png': png_file,
        'comparacion': comparacion
    }

