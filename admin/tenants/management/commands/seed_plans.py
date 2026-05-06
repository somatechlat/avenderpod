"""
Idempotent management command to seed the canonical ¡A VENDER! SaaS plans.

Usage:
    python manage.py seed_plans          # Seed all 5 canonical plans
    python manage.py seed_plans --force  # Update existing plans to match spec

Plan data matches the assertions in ``AvenderPlanCatalogTests``.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from tenants.models import Plan

# ── Canonical Plan Definitions ────────────────────────────────────────────
PLANS: list[dict] = [
    {
        "slug": "free",
        "name": "Free",
        "price_monthly": Decimal("0.00"),
        "description": "Plan gratuito de prueba — ideal para conocer la plataforma.",
        "marketing_badge": "Prueba Gratis",
        "trial_days": 5,
        "trial_message_limit": 500,
        "max_conversations": 50,
        "max_numbers": 1,
        "max_messages_per_day": 200,
        "max_messages_per_minute": 20,
        "max_catalog_items": 50,
        "max_transcription_minutes": 30,
        "max_storage_mb": 256,
        "max_users": 1,
        "max_agent_contexts": 1,
        "support_level": "community",
        "allow_catalog_upload": True,
        "allow_voice_messages": False,
        "allow_human_handoff": False,
        "allow_creator_override": True,
        "allow_custom_domain": False,
        "allow_integrations": False,
        "allow_mobile_app": False,
        "allow_multichannel": False,
        "allow_outbound_reactivation": False,
        "allow_call_handling": False,
    },
    {
        "slug": "starter",
        "name": "Starter",
        "price_monthly": Decimal("25.00"),
        "description": "Para negocios que inician su automatización de ventas.",
        "marketing_badge": "Popular",
        "trial_days": 0,
        "trial_message_limit": 0,
        "max_conversations": 300,
        "max_numbers": 1,
        "max_messages_per_day": 1000,
        "max_messages_per_minute": 40,
        "max_catalog_items": 200,
        "max_transcription_minutes": 60,
        "max_storage_mb": 512,
        "max_users": 2,
        "max_agent_contexts": 1,
        "support_level": "standard",
        "allow_catalog_upload": True,
        "allow_voice_messages": True,
        "allow_human_handoff": True,
        "allow_creator_override": True,
        "allow_custom_domain": False,
        "allow_integrations": False,
        "allow_mobile_app": False,
        "allow_multichannel": False,
        "allow_outbound_reactivation": False,
        "allow_call_handling": False,
    },
    {
        "slug": "growth",
        "name": "Growth",
        "price_monthly": Decimal("55.00"),
        "description": "Multicanal y crecimiento acelerado con integraciones.",
        "marketing_badge": "Recomendado",
        "trial_days": 0,
        "trial_message_limit": 0,
        "max_conversations": 1000,
        "max_numbers": 3,
        "max_messages_per_day": 3000,
        "max_messages_per_minute": 60,
        "max_catalog_items": 500,
        "max_transcription_minutes": 120,
        "max_storage_mb": 1024,
        "max_users": 5,
        "max_agent_contexts": 2,
        "support_level": "priority",
        "allow_catalog_upload": True,
        "allow_voice_messages": True,
        "allow_human_handoff": True,
        "allow_creator_override": True,
        "allow_custom_domain": False,
        "allow_integrations": True,
        "allow_mobile_app": True,
        "allow_multichannel": True,
        "allow_outbound_reactivation": True,
        "allow_call_handling": False,
    },
    {
        "slug": "pro",
        "name": "Pro",
        "price_monthly": Decimal("120.00"),
        "description": "Capacidad completa con llamadas, dominio personalizado y más.",
        "marketing_badge": "Todo Incluido",
        "trial_days": 0,
        "trial_message_limit": 0,
        "max_conversations": 5000,
        "max_numbers": 5,
        "max_messages_per_day": 10000,
        "max_messages_per_minute": 120,
        "max_catalog_items": 2000,
        "max_transcription_minutes": 300,
        "max_storage_mb": 4096,
        "max_users": 10,
        "max_agent_contexts": 5,
        "support_level": "dedicated",
        "allow_catalog_upload": True,
        "allow_voice_messages": True,
        "allow_human_handoff": True,
        "allow_creator_override": True,
        "allow_custom_domain": True,
        "allow_integrations": True,
        "allow_mobile_app": True,
        "allow_multichannel": True,
        "allow_outbound_reactivation": True,
        "allow_call_handling": True,
    },
    {
        "slug": "enterprise",
        "name": "Enterprise",
        "price_monthly": Decimal("0.00"),
        "is_custom_priced": True,
        "description": "Solución empresarial a medida con SLA dedicado.",
        "marketing_badge": "Enterprise",
        "trial_days": 0,
        "trial_message_limit": 0,
        "max_conversations": 99999,
        "max_numbers": 20,
        "max_messages_per_day": 100000,
        "max_messages_per_minute": 300,
        "max_catalog_items": 50000,
        "max_transcription_minutes": 9999,
        "max_storage_mb": 51200,
        "max_users": 50,
        "max_agent_contexts": 20,
        "support_level": "enterprise",
        "vultr_plan": "vc2-4c-8gb",
        "a0_memory_limit": "6g",
        "a0_cpu_limit": "4.0",
        "a0_memory_reservation": "2g",
        "a0_cpu_reservation": "2.0",
        "allow_catalog_upload": True,
        "allow_voice_messages": True,
        "allow_human_handoff": True,
        "allow_creator_override": True,
        "allow_custom_domain": True,
        "allow_integrations": True,
        "allow_mobile_app": True,
        "allow_multichannel": True,
        "allow_outbound_reactivation": True,
        "allow_call_handling": True,
    },
]


class Command(BaseCommand):
    help = "Seed the canonical ¡A VENDER! SaaS plans (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update existing plans to match the canonical specification.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for plan_data in PLANS:
            slug = plan_data["slug"]
            existing = Plan.objects.filter(slug=slug).first()

            if existing and not force:
                skipped_count += 1
                self.stdout.write(f"  ⏭  {slug}: already exists (use --force to update)")
                continue

            if existing and force:
                for field, value in plan_data.items():
                    setattr(existing, field, value)
                existing.is_active = True
                existing.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"  ✏️  {slug}: updated to spec"))
            else:
                Plan.objects.create(**plan_data)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅  {slug}: created"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_count} created, "
                f"{updated_count} updated, {skipped_count} skipped."
            )
        )

        # ── Seed GlobalConfig (God Mode password) ────────────────────────
        self._seed_master_password()

    def _seed_master_password(self) -> None:
        """
        Ensure GlobalConfig contains a PBKDF2-hashed MASTER_CREATOR_PASSWORD.
        The raw password is read from the MASTER_CREATOR_PASSWORD env var or
        secret file. If neither exists, skip silently (non-blocking).
        """
        from django.contrib.auth.hashers import make_password

        from tenants.models import GlobalConfig
        from tenants.secret_values import read_secret

        raw_password = read_secret("MASTER_CREATOR_PASSWORD")
        if not raw_password:
            self.stdout.write(
                "  ⚠️  MASTER_CREATOR_PASSWORD not set — God Mode will not work "
                "until this secret is configured."
            )
            return

        existing = GlobalConfig.objects.filter(key="MASTER_CREATOR_PASSWORD").first()
        if existing:
            stored = str(existing.value)
            if stored.startswith(("pbkdf2_", "argon2", "bcrypt")):
                self.stdout.write("  ⏭  MASTER_CREATOR_PASSWORD: already hashed")
                return
            # Upgrade from plaintext → PBKDF2 hash
            existing.value = make_password(raw_password)
            existing.save(update_fields=["value"])
            self.stdout.write(
                self.style.WARNING(
                    "  ✏️  MASTER_CREATOR_PASSWORD: upgraded from plaintext to PBKDF2"
                )
            )
        else:
            GlobalConfig.objects.create(
                key="MASTER_CREATOR_PASSWORD",
                value=make_password(raw_password),
            )
            self.stdout.write(
                self.style.SUCCESS("  ✅  MASTER_CREATOR_PASSWORD: seeded (PBKDF2)")
            )
