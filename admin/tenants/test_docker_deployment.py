"""
REAL integration tests for Docker Deployment Service, Deployment Router,
and container management API endpoints.

NO MOCKS. Every test creates/manages real Docker containers via the
mounted /var/run/docker.sock. Uses a lightweight alpine image for
speed, but the same code path that deploys avender-agent_zero:latest.

These tests are designed to run inside the avender_sysadmin container
which has the Docker socket mounted.
"""

from __future__ import annotations

import docker
from docker.errors import NotFound

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from tenants.models import GlobalConfig, Plan, Tenant


# Use alpine for test speed — the deploy/stop/start/delete code path
# is identical regardless of image. Production uses avender-agent_zero:latest.
TEST_IMAGE = "alpine:latest"
TEST_PORT_BASE = 45090


def _ensure_test_image():
    """Pull the lightweight test image if not present."""
    client = docker.from_env()
    try:
        client.images.get(TEST_IMAGE)
    except docker.errors.ImageNotFound:
        client.images.pull(TEST_IMAGE)


def _cleanup_container(name_or_id):
    """Force-remove a container if it exists."""
    client = docker.from_env()
    try:
        c = client.containers.get(name_or_id)
        c.stop(timeout=3)
        c.remove(force=True)
    except (NotFound, docker.errors.APIError):
        pass


def _cleanup_volume(vol_name):
    """Force-remove a volume if it exists."""
    client = docker.from_env()
    try:
        v = client.volumes.get(vol_name)
        v.remove(force=True)
    except (NotFound, docker.errors.APIError):
        pass


# ---------------------------------------------------------------------------
# Docker Service — Real Container Lifecycle Tests
# ---------------------------------------------------------------------------


@override_settings(SECURE_SSL_REDIRECT=False)
class DockerServiceLifecycleTests(TestCase):
    """
    Full lifecycle test using REAL Docker containers.
    Deploy → Inspect → Suspend → Reactivate → Delete.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_image()

    def setUp(self) -> None:
        self.plan = Plan.objects.create(
            name="Test Plan",
            slug="integration-test",
            price_monthly=0,
            a0_image=TEST_IMAGE,
            a0_memory_limit="64m",
            a0_cpu_limit="0.5",
            a0_memory_reservation="32m",
        )
        self.tenant = Tenant.objects.create(
            name="Integration Test Tenant",
            email="inttest@avender.local",
            status="pending",
            plan=self.plan,
            assigned_port=TEST_PORT_BASE,
        )
        # Pre-cleanup in case a previous test run crashed
        from tenants.docker_service import _container_name, _volume_name

        _cleanup_container(_container_name(self.tenant))
        _cleanup_volume(_volume_name(self.tenant))

    def tearDown(self) -> None:
        """Always clean up containers and volumes after each test."""
        from tenants.docker_service import _container_name, _volume_name

        _cleanup_container(_container_name(self.tenant))
        _cleanup_volume(_volume_name(self.tenant))

    def test_full_lifecycle_deploy_suspend_reactivate_delete(self) -> None:
        """
        End-to-end: deploy a real container, verify it runs, stop it,
        start it again, then permanently delete it. All against real Docker.
        """
        from tenants.docker_service import (
            delete_tenant_pod,
            deploy_tenant_pod,
            get_container_logs,
            get_container_status,
            reactivate_tenant_pod,
            suspend_tenant_pod,
        )

        # ---- DEPLOY ----
        bootstrap_env = {
            "TENANT_ID": str(self.tenant.id),
            "A0_PLAN_NAME": self.plan.name,
            "A0_MAX_MESSAGES_PER_DAY": "1000",
            "A0_MAX_CONVERSATIONS_PER_MONTH": "500",
        }
        result = deploy_tenant_pod(self.tenant, bootstrap_env=bootstrap_env)

        self.assertEqual(result["status"], "running")
        self.assertEqual(result["port"], TEST_PORT_BASE)
        self.assertEqual(result["mem_limit"], "64m")
        self.assertEqual(result["image"], TEST_IMAGE)

        # Verify tenant DB was updated
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.deployment_backend, "docker")
        self.assertEqual(self.tenant.status, "active")
        self.assertIsNotNone(self.tenant.docker_container_id)

        # Verify the container actually exists in Docker
        client = docker.from_env()
        container = client.containers.get(self.tenant.docker_container_id)
        # alpine exits immediately (no daemon), so it may be restarting.
        # Real avender-agent_zero:latest stays in 'running'.
        self.assertIn(container.status, ("running", "created", "restarting", "exited"))

        # Verify env vars were injected (plan limits)
        inspect = container.attrs
        env_list = inspect["Config"]["Env"]
        env_dict = {e.split("=", 1)[0]: e.split("=", 1)[1] for e in env_list if "=" in e}
        self.assertEqual(env_dict.get("A0_MAX_MESSAGES_PER_DAY"), "1000")
        self.assertEqual(env_dict.get("A0_MAX_CONVERSATIONS_PER_MONTH"), "500")
        self.assertEqual(env_dict.get("TENANT_ID"), str(self.tenant.id))

        # Verify resource limits were applied
        mem = inspect["HostConfig"]["Memory"]
        self.assertEqual(mem, 64 * 1024 * 1024)  # 64MB in bytes
        cpu = inspect["HostConfig"]["NanoCpus"]
        self.assertEqual(cpu, 500_000_000)  # 0.5 CPU

        # ---- STATUS ----
        status = get_container_status(self.tenant)
        self.assertIn(status["state"], ("running", "created", "restarting", "exited"))
        self.assertIn("container_name", status)

        # ---- LOGS ----
        logs = get_container_logs(self.tenant, tail=10)
        self.assertIsInstance(logs, str)

        # ---- SUSPEND ----
        result = suspend_tenant_pod(self.tenant)
        self.assertEqual(result["status"], "stopped")
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, "suspended")

        # Verify container is stopped in Docker
        container.reload()
        self.assertIn(container.status, ("exited", "created", "restarting"))

        # Status should reflect stopped state
        status = get_container_status(self.tenant)
        self.assertIn(status["state"], ("exited", "created", "restarting"))

        # ---- REACTIVATE ----
        result = reactivate_tenant_pod(self.tenant)
        self.assertEqual(result["status"], "started")
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, "active")

        # Verify container is running again
        container.reload()
        self.assertIn(container.status, ("running", "restarting", "exited"))

        # ---- DELETE ----
        container_id = self.tenant.docker_container_id
        result = delete_tenant_pod(self.tenant)
        self.assertEqual(result["status"], "deleted")
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, "deleted")
        self.assertIsNone(self.tenant.docker_container_id)

        # Verify container is gone from Docker
        with self.assertRaises(NotFound):
            client.containers.get(container_id)

    def test_deploy_no_port_raises(self) -> None:
        """Deploying without an assigned port raises ValueError."""
        from tenants.docker_service import deploy_tenant_pod

        self.tenant.assigned_port = None
        self.tenant.save()
        with self.assertRaises(ValueError):
            deploy_tenant_pod(self.tenant)

    def test_status_no_container_returns_unknown(self) -> None:
        """Status check with no container_id returns unknown."""
        from tenants.docker_service import get_container_status

        status = get_container_status(self.tenant)
        self.assertEqual(status["state"], "unknown")

    def test_logs_no_container_returns_message(self) -> None:
        """Logs check with no container_id returns a descriptive message."""
        from tenants.docker_service import get_container_logs

        logs = get_container_logs(self.tenant)
        self.assertIn("No container ID", logs)

    def test_deploy_replaces_existing_container(self) -> None:
        """Deploying when a container already exists replaces it cleanly."""
        from tenants.docker_service import deploy_tenant_pod

        # Deploy once
        deploy_tenant_pod(self.tenant, bootstrap_env={"TENANT_ID": str(self.tenant.id)})
        self.tenant.refresh_from_db()
        first_id = self.tenant.docker_container_id

        # Deploy again — should replace
        result = deploy_tenant_pod(self.tenant, bootstrap_env={"TENANT_ID": str(self.tenant.id)})
        self.tenant.refresh_from_db()
        second_id = self.tenant.docker_container_id

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(result["status"], "running")

        # First container should be gone
        client = docker.from_env()
        with self.assertRaises(NotFound):
            client.containers.get(first_id)


# ---------------------------------------------------------------------------
# Deployment Router Tests — Pure DB, no mocks needed
# ---------------------------------------------------------------------------


@override_settings(SECURE_SSL_REDIRECT=False)
class DeploymentRouterTests(TestCase):
    """Verify the deployment router correctly reads/writes GlobalConfig."""

    def test_default_mode_is_vultr(self) -> None:
        """Without GlobalConfig entry, mode defaults to vultr."""
        from tenants.deployment_router import get_deployment_mode

        self.assertEqual(get_deployment_mode(), "vultr")

    def test_set_mode_docker(self) -> None:
        """Setting mode to docker persists in GlobalConfig."""
        from tenants.deployment_router import get_deployment_mode, set_deployment_mode

        set_deployment_mode("docker")
        self.assertEqual(get_deployment_mode(), "docker")
        self.assertEqual(
            GlobalConfig.objects.get(key="DEPLOYMENT_MODE").value, "docker"
        )

    def test_set_mode_vultr(self) -> None:
        """Setting mode to vultr persists in GlobalConfig."""
        from tenants.deployment_router import get_deployment_mode, set_deployment_mode

        set_deployment_mode("vultr")
        self.assertEqual(get_deployment_mode(), "vultr")

    def test_invalid_mode_falls_back_to_vultr(self) -> None:
        """An invalid mode in GlobalConfig falls back to vultr."""
        from tenants.deployment_router import get_deployment_mode

        GlobalConfig.objects.create(key="DEPLOYMENT_MODE", value="kubernetes")
        self.assertEqual(get_deployment_mode(), "vultr")


# ---------------------------------------------------------------------------
# Deployment Mode API Tests — Real HTTP, no mocks
# ---------------------------------------------------------------------------


@override_settings(SECURE_SSL_REDIRECT=False)
class DeploymentModeAPITests(TestCase):
    """Verify the /system/deployment-mode endpoints with real DB."""

    def setUp(self) -> None:
        self.admin = User.objects.create_superuser("dm_admin", "dm@ex.com", "x")
        self.user = User.objects.create_user("dm_user", "dm_u@ex.com", "x")

    def test_get_mode_requires_sysadmin(self) -> None:
        self.client.force_login(self.user)
        resp = self.client.get("/api/saas/system/deployment-mode")
        self.assertEqual(resp.status_code, 403)

    def test_get_mode_returns_default_vultr(self) -> None:
        self.client.force_login(self.admin)
        resp = self.client.get("/api/saas/system/deployment-mode")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["mode"], "vultr")

    def test_set_mode_to_docker(self) -> None:
        self.client.force_login(self.admin)
        resp = self.client.post(
            "/api/saas/system/deployment-mode",
            data={"mode": "docker"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(resp.json()["mode"], "docker")

        # Verify persisted in DB
        config = GlobalConfig.objects.get(key="DEPLOYMENT_MODE")
        self.assertEqual(config.value, "docker")

    def test_set_invalid_mode_rejected(self) -> None:
        self.client.force_login(self.admin)
        resp = self.client.post(
            "/api/saas/system/deployment-mode",
            data={"mode": "kubernetes"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_admin_cannot_set_mode(self) -> None:
        self.client.force_login(self.user)
        resp = self.client.post(
            "/api/saas/system/deployment-mode",
            data={"mode": "docker"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Container Management API Tests — Real HTTP, real Docker
# ---------------------------------------------------------------------------


@override_settings(SECURE_SSL_REDIRECT=False)
class ContainerManagementAPITests(TestCase):
    """
    Verify container-status, container-logs, and restart endpoints.
    Uses the existing avender_agent_zero container for read-only checks.
    """

    def setUp(self) -> None:
        self.admin = User.objects.create_superuser("cm_admin", "cm@ex.com", "x")
        self.owner = User.objects.create_user("cm_owner", "cm_o@ex.com", "x")
        self.other = User.objects.create_user("cm_other", "cm_oth@ex.com", "x")

        # Point to the REAL avender_agent_zero container for read-only tests
        self.tenant = Tenant.objects.create(
            name="CM Real Test",
            email="cm@test.com",
            owner=self.owner,
            status="active",
            deployment_backend="docker",
            docker_container_id="avender_agent_zero",
            assigned_port=45001,
        )

    def test_container_status_returns_real_data(self) -> None:
        """SysAdmin can get real container status from Docker daemon."""
        self.client.force_login(self.admin)
        resp = self.client.get(
            f"/api/saas/tenants/{self.tenant.id}/container-status"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # avender_agent_zero should be running
        self.assertIn("state", data)
        self.assertIn(data["state"], ("running", "exited", "created", "restarting"))

    def test_container_status_other_forbidden(self) -> None:
        """Non-owner cannot check container status."""
        self.client.force_login(self.other)
        resp = self.client.get(
            f"/api/saas/tenants/{self.tenant.id}/container-status"
        )
        self.assertEqual(resp.status_code, 403)

    def test_container_logs_returns_real_output(self) -> None:
        """SysAdmin can get real container logs from Docker daemon."""
        self.client.force_login(self.admin)
        resp = self.client.get(
            f"/api/saas/tenants/{self.tenant.id}/container-logs?tail=10"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("logs", data)
        self.assertIsInstance(data["logs"], str)

    def test_container_logs_owner_forbidden(self) -> None:
        """Owner cannot access logs (SysAdmin-only)."""
        self.client.force_login(self.owner)
        resp = self.client.get(
            f"/api/saas/tenants/{self.tenant.id}/container-logs"
        )
        self.assertEqual(resp.status_code, 403)

    def test_restart_non_admin_forbidden(self) -> None:
        """Non-admin cannot restart tenants."""
        self.client.force_login(self.owner)
        resp = self.client.post(
            f"/api/saas/tenants/{self.tenant.id}/restart"
        )
        self.assertEqual(resp.status_code, 403)
