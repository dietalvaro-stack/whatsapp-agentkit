# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

"""
Servidor principal del agente de WhatsApp.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp (se configura en .env con WHATSAPP_PROVIDER)
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


def cargar_numeros_guardados() -> list[str]:
    """Lee los números de contactos guardados desde config/saved_contacts.json."""
    try:
        with open("config/saved_contacts.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("numeros_guardados", [])
    except FileNotFoundError:
        logger.warning("config/saved_contacts.json no encontrado")
        return []
    except json.JSONDecodeError:
        logger.error("Error al parsear config/saved_contacts.json")
        return []


def es_numero_guardado(telefono: str, numeros_guardados: list[str]) -> bool:
    """Verifica si un número está en la lista de contactos guardados."""
    # Normalizar el número (remover espacios, guiones, etc.)
    telefono_limpio = telefono.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    for numero_guardado in numeros_guardados:
        numero_guardado_limpio = numero_guardado.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if telefono_limpio.endswith(numero_guardado_limpio) or numero_guardado_limpio.endswith(telefono_limpio):
            return True

    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="Soporte Dietalvaro — WhatsApp AI Agent",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "service": "soporte-dietalvaro"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para Whapi)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via Whapi.cloud.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.
    SOLO responde a números que NO estén en la lista de contactos guardados.
    """
    try:
        # Cargar números guardados al inicio
        numeros_guardados = cargar_numeros_guardados()

        # Parsear webhook — el proveedor normaliza el formato
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            # Ignorar mensajes propios o vacíos
            if msg.es_propio or not msg.texto:
                continue

            # Verificar si el número está guardado
            if es_numero_guardado(msg.telefono, numeros_guardados):
                logger.info(f"Mensaje ignorado de número guardado: {msg.telefono}")
                continue

            logger.info(f"Mensaje de número desconocido {msg.telefono}: {msg.texto}")

            # Obtener historial ANTES de guardar el mensaje actual
            # (brain.py agrega el mensaje actual, evitando duplicados)
            historial = await obtener_historial(msg.telefono)

            # Generar respuesta con Claude
            respuesta = await generar_respuesta(msg.texto, historial)

            # Guardar mensaje del usuario Y respuesta del agente en memoria
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar respuesta por WhatsApp via Whapi.cloud
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
