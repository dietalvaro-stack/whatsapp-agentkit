# agent/tools.py — Herramientas del agente Soporte Dietalvaro
# Generado por AgentKit

"""
Herramientas específicas del negocio de @dietalvaro.
Funciones de apoyo para responder dudas sobre servicios, suplementos y marcas.
"""

import os
import yaml
import logging

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención del negocio."""
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "Lunes a domingo de 7:30 a 19:00"),
        "esta_abierto": True,
    }


def obtener_servicios() -> dict:
    """Retorna los servicios disponibles con sus precios."""
    info = cargar_info_negocio()
    return info.get("servicios", {
        "asesoria_puntual": {
            "precio": "200€",
            "descripcion": "Auditoría profunda del caso y hoja de ruta inmediata"
        },
        "programa_completo": {
            "precio": "600€",
            "descripcion": "Acompañamiento integral durante un año entero"
        }
    })


def buscar_marca(nombre_marca: str) -> dict | None:
    """
    Busca información de una marca colaboradora por nombre.

    Args:
        nombre_marca: Nombre de la marca (ej: "AdaptoHeal", "BeLevels")

    Returns:
        Diccionario con nombre, codigo y enlace, o None si no se encuentra
    """
    info = cargar_info_negocio()
    marcas = info.get("marcas_colaboradoras", [])

    nombre_busqueda = nombre_marca.lower()
    for marca in marcas:
        if nombre_busqueda in marca.get("nombre", "").lower():
            return marca

    return None


def obtener_todas_marcas() -> list[dict]:
    """Retorna la lista completa de marcas colaboradoras con sus códigos."""
    info = cargar_info_negocio()
    return info.get("marcas_colaboradoras", [])


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en los archivos de conocimiento."
