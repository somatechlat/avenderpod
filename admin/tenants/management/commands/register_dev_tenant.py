"""
Management command: register_dev_tenant

Registers the existing avenderpod_dev Docker container as a tenant
in the SysAdmin database. This makes it visible in the dashboard for
development and testing.

Only runs when DJANGO_DEBUG=true or --force is passed.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from tenants.models import GlobalConfig, Plan, Tenant
from tenants.pod_registry import register_pod_deployment


DEV_TENANT_EMAIL = "dev@avender.local"
DEV_CONTAINER_NAME = "avenderpod_dev"
DEV_PORT = 45001


class Command(BaseCommand):
    help = "Register the local avenderpod_dev as a development tenant."

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
            try:
                import docker

                container = docker.from_env().containers.get(DEV_CONTAINER_NAME)
                register_pod_deployment(
                    tenant=existing,
                    pod_name=DEV_CONTAINER_NAME,
                    backend="docker",
                    provider_resource_id=container.id,
                    avender_container_id=container.id,
                    image_tag=container.image.tags[0] if container.image.tags else "",
                    assigned_port=existing.assigned_port,
                    private_url=f"http://127.0.0.1:{existing.assigned_port}",
                    deployment_config={},
                    lifecycle_state="active" if container.status == "running" else "unknown",
                    provider_health_state="healthy" if container.status == "running" else "unhealthy",
                    tenant_vault_state="not_configured",
                    is_development=True,
                )
            except Exception:
                existing.status = "pending"
                existing.save(update_fields=["status"])
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

        try:
            import docker

            container = docker.from_env().containers.get(DEV_CONTAINER_NAME)
            container_id = container.id
            container_status = container.status
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"Cannot register dev tenant because Docker container "
                    f"'{DEV_CONTAINER_NAME}' was not found: {exc}"
                )
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
            name="Dev Avender Pod",
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
        register_pod_deployment(
            tenant=tenant,
            pod_name=DEV_CONTAINER_NAME,
            backend="docker",
            provider_resource_id=container_id,
            avender_container_id=container_id,
            image_tag=container.image.tags[0] if container.image.tags else "",
            assigned_port=DEV_PORT,
            private_url=f"http://127.0.0.1:{DEV_PORT}",
            deployment_config={},
            lifecycle_state="active" if container_status == "running" else "unknown",
            provider_health_state="healthy" if container_status == "running" else "unhealthy",
            tenant_vault_state="not_configured",
            is_development=True,
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
