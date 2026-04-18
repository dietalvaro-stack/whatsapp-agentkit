# agent/providers/whapi.py — Adaptador para Whapi.cloud
# Generado por AgentKit

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorWhapi(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando Whapi.cloud (REST API simple)."""

    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.url_envio = "https://gate.whapi.cloud/messages/text"

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload de Whapi.cloud."""
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"ERROR al parsear JSON: {e}")
            return []

        logger.info(f"DEBUG: Tipo de body: {type(body)}")
        logger.info(f"DEBUG: Contenido body: {body}")

        # Validar que body es un diccionario
        if not isinstance(body, dict):
            logger.error(f"ERROR: Body NO es dict, es {type(body).__name__}: {repr(body)}")
            return []

        mensajes = []
        messages_list = body.get("messages", [])
        logger.info(f"DEBUG: Messages encontrados: {len(messages_list)}")

        for msg in messages_list:
            # Extraer texto — puede ser diccionario o string según el cliente
            text_data = msg.get("text", {})
            if isinstance(text_data, dict):
                texto = text_data.get("body", "")
            elif isinstance(text_data, str):
                texto = text_data
            else:
                texto = ""

            # Intentar extraer el nombre del contacto (si está guardado en WhatsApp)
            nombre_contacto = ""
            contact_data = msg.get("contact", {})
            if isinstance(contact_data, dict):
                nombre_contacto = contact_data.get("name", "")
            elif isinstance(contact_data, str):
                nombre_contacto = contact_data

            mensajes.append(MensajeEntrante(
                telefono=msg.get("chat_id", ""),
                texto=texto,
                mensaje_id=msg.get("id", ""),
                es_propio=msg.get("from_me", False),
                nombre_contacto=nombre_contacto,
            ))
        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Whapi.cloud."""
        if not self.token:
            logger.warning("WHAPI_TOKEN no configurado — mensaje no enviado")
            return False
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self.url_envio,
                json={"to": telefono, "body": mensaje},
                headers=headers,
            )
            if r.status_code != 200:
                logger.error(f"Error Whapi: {r.status_code} — {r.text}")
            return r.status_code == 200
