"""
Management command: register_dev_tenant

Registers the existing avender_agent_zero Docker container as a tenant
in the SysAdmin database. This makes it visible in the dashboard for
development and testing.

Only runs when DJANGO_DEBUG=true or --force is passed.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from tenants.models import GlobalConfig, Plan, Tenant


DEV_TENANT_EMAIL = "dev@avender.local"
DEV_CONTAINER_NAME = "avender_agent_zero"
DEV_PORT = 45001


class Command(BaseCommand):
    help = "Register the local avender_agent_zero as a development tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force registration even if DJANGO_DEBUG is not set.",
        )

    def handle(self, *args, **options):
        import os

        debug = os.environ.get("DJANGO_DEBUG", "").lower() in ("true", "1", "yes")
        if not debug and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping dev tenant registration (DJANGO_DEBUG is not set). "
                    "Use --force to override."
                )
            )
            return

        # Check if dev tenant already exists
        existing = Tenant.objects.filter(email=DEV_TENANT_EMAIL).first()
        if existing:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ⏭  Dev tenant '{existing.name}' already registered "
                    f"(port {existing.assigned_port})"
                )
            )
            # Ensure deployment mode is set to docker in dev
            GlobalConfig.objects.update_or_create(
                key="DEPLOYMENT_MODE",
                defaults={
                    "value": "docker",
                    "description": "Active deployment backend",
                },
            )
            return

        # Get the admin superuser as the owner
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stderr.write(
                self.style.ERROR(
                    "No superuser found. Run createsuperuser first."
                )
            )
            return

        # Get the free plan (or any available plan)
        plan = (
            Plan.objects.filter(slug="free", is_active=True).first()
            or Plan.objects.filter(is_active=True).first()
        )
        if not plan:
            self.stderr.write(
                self.style.ERROR(
                    "No active plan found. Run seed_plans first."
                )
            )
            return

        # Create the dev tenant
        tenant = Tenant.objects.create(
            name="Dev Agent Zero",
            email=DEV_TENANT_EMAIL,
            owner_full_name="SysAdmin (Development)",
            owner_phone_e164="+0000000000",
            owner=admin_user,
            plan=plan,
            status="active",
            assigned_port=DEV_PORT,
            deployment_backend="docker",
            docker_container_id=DEV_CONTAINER_NAME,
        )

        # Set deployment mode to docker for dev
        GlobalConfig.objects.update_or_create(
            key="DEPLOYMENT_MODE",
            defaults={
                "value": "docker",
                "description": "Active deployment backend",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅ Dev tenant '{tenant.name}' registered "
                f"(port {DEV_PORT}, container: {DEV_CONTAINER_NAME})"
            )
        )
