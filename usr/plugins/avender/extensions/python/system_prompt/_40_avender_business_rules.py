"""Injects business rules dynamically from the tenant's onboarding config into the system prompt."""
import json
from typing import Any

from helpers.extension import Extension
from usr.plugins.avender.helpers.db import get_tenant_config


class AvenderBusinessRules(Extension):
    async def execute(self, system_prompt: list[str], **kwargs):
        if not self.agent:
            return
            
        agent_profile = getattr(self.agent.config, "agent_profile", "")
        if agent_profile != "avender_sales":
            return

        archetype = get_tenant_config("archetype") or "retail"
        trade_name = get_tenant_config("tradeName") or "Negocio"
        policies = get_tenant_config("policies") or "No hay políticas adicionales."
        hours = get_tenant_config("hours") or "24/7"
        delivery_rules = get_tenant_config("deliveryRules") or "No definido."
        agent_name = get_tenant_config("agentName") or "Asistente"
        tone = get_tenant_config("tone") or "friendly"
        
        # Build payment methods
        methods = []
        # JSON strings from Alpine might be literally 'true' or 'false'
        if str(get_tenant_config("payTransfer")).lower() == "true": 
            methods.append("Transferencia Bancaria")
        if str(get_tenant_config("payCash")).lower() == "true": 
            methods.append("Efectivo")
        if str(get_tenant_config("payLink")).lower() == "true": 
            methods.append(f"Link de Pago ({get_tenant_config('paymentUrl')})")
            
        methods_str = ", ".join(methods) if methods else "Acordar con el vendedor"
        
        use_slang_val = str(get_tenant_config("useSlang")).lower() == "true"
        slang_directive = "Puedes usar modismos locales moderadamente." if use_slang_val else "Mantén un lenguaje profesional sin modismos locales."

        rules = (
            f"\n\n[REGLAS DEL NEGOCIO - ¡A VENDER!]\n"
            f"Eres el asistente virtual oficial de '{trade_name}'. Tu nombre es {agent_name}.\n"
            f"Arquetipo de Industria: {archetype.upper()}\n"
            f"Tono de conversación: {tone.upper()}. {slang_directive}\n"
            f"Horarios de Atención: {hours}\n"
            f"Reglas de Delivery / Cobertura: {delivery_rules}\n"
            f"Políticas Internas (Estrictas): {policies}\n"
            f"Métodos de Pago Aceptados: {methods_str}\n\n"
            f"INSTRUCCIÓN CRÍTICA: SIEMPRE respeta estas políticas, horarios y métodos de pago. "
            f"Si el cliente pide algo fuera de tus capacidades o que rompe las políticas, "
            f"explica amablemente que no es posible y ofrece una alternativa válida dentro de tus reglas."
        )
        system_prompt.append(rules)
