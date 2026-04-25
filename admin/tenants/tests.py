from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from tenants.models import GlobalConfig, Tenant, Plan, VaultRecord
from tenants.vault_service import provision_tenant_secrets, build_tenant_bootstrap_env


class GodModeAuthTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user("owner", password="x")
        self.other = User.objects.create_user("other", password="x")
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "x")
        self.tenant = Tenant.objects.create(
            name="Tenant A",
            email="tenant-a@example.com",
            owner=self.owner,
            status="active",
        )
        GlobalConfig.objects.create(key="MASTER_CREATOR_PASSWORD", value="master-secret")

    def test_init_challenge_owner_allowed(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.post(f"/api/saas/auth/init-challenge?tenant_id={self.tenant.id}")
        self.assertEqual(response.status_code, 200)

        self.tenant.refresh_from_db()
        self.assertIsNotNone(self.tenant.creator_session_pin)
        self.assertIsNotNone(self.tenant.pin_expires_at)

    def test_init_challenge_other_user_forbidden(self) -> None:
        self.client.force_login(self.other)
        response = self.client.post(f"/api/saas/auth/init-challenge?tenant_id={self.tenant.id}")
        self.assertEqual(response.status_code, 403)

    def test_init_challenge_service_api_key_allowed(self) -> None:
        os.environ["SYSADMIN_API_KEY"] = "s" * 32
        try:
            response = self.client.post(
                f"/api/saas/auth/init-challenge?tenant_id={self.tenant.id}",
                **{"HTTP_X_API_KEY": "s" * 32},
            )
            self.assertEqual(response.status_code, 200)
        finally:
            os.environ.pop("SYSADMIN_API_KEY", None)

    def test_verify_challenge_requires_superuser_or_service(self) -> None:
        self.tenant.creator_session_pin = "1234"
        self.tenant.pin_expires_at = timezone.now() + timedelta(minutes=5)
        self.tenant.save(update_fields=["creator_session_pin", "pin_expires_at"])

        self.client.force_login(self.owner)
        response = self.client.post(
            "/api/saas/auth/verify-challenge",
            data={"tenant_id": str(self.tenant.id), "password": "master-secret", "pin": "1234"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_verify_challenge_superuser_success(self) -> None:
        self.tenant.creator_session_pin = "1234"
        self.tenant.pin_expires_at = timezone.now() + timedelta(minutes=5)
        self.tenant.save(update_fields=["creator_session_pin", "pin_expires_at"])

        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/saas/auth/verify-challenge",
            data={"tenant_id": str(self.tenant.id), "password": "master-secret", "pin": "1234"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))

    def test_pending_challenges_requires_superuser_or_service(self) -> None:
        self.tenant.creator_session_pin = "1234"
        self.tenant.pin_expires_at = timezone.now() + timedelta(minutes=5)
        self.tenant.save(update_fields=["creator_session_pin", "pin_expires_at"])

        self.client.force_login(self.owner)
        response = self.client.get("/api/saas/auth/pending-challenges")
        self.assertEqual(response.status_code, 403)


class VaultProvisioningTests(TestCase):
    def setUp(self) -> None:
        self.admin = User.objects.create_superuser("admin2", "admin2@example.com", "x")
        self.plan = Plan.objects.create(name="Basic", price_monthly=10, max_conversations=100, max_numbers=1)
        self.tenant = Tenant.objects.create(
            name="Tenant Vault",
            email="tenant-vault@example.com",
            owner=self.admin,
            plan=self.plan,
            status="pending",
        )

    def test_provision_tenant_secrets_writes_vault_and_records_path(self) -> None:
        os.environ["VAULT_ADDR"] = "http://vault:8200"
        os.environ["VAULT_TOKEN"] = "root-token"
        os.environ["VAULT_KV_MOUNT"] = "secret"
        try:
            mock_response = MagicMock(status_code=200, text="ok")
            with patch("tenants.vault_service.requests.post", return_value=mock_response) as post_mock:
                bundle = provision_tenant_secrets(self.tenant)

            self.assertIn("AVENDER_SETUP_TOKEN", bundle)
            self.assertIn("MCP_SERVER_TOKEN", bundle)
            self.assertEqual(len(bundle["AVENDER_SETUP_TOKEN"]), 64)
            self.assertEqual(len(bundle["MCP_SERVER_TOKEN"]), 64)
            self.assertTrue(
                VaultRecord.objects.filter(
                    tenant=self.tenant,
                    vault_path=f"secret/avender/tenants/{self.tenant.id}",
                ).exists()
            )
            post_mock.assert_called_once()
        finally:
            os.environ.pop("VAULT_ADDR", None)
            os.environ.pop("VAULT_TOKEN", None)
            os.environ.pop("VAULT_KV_MOUNT", None)

    def test_build_tenant_bootstrap_env_requires_strong_sysadmin_key(self) -> None:
        os.environ["SYSADMIN_API_URL"] = "https://sysadmin.example.com/api/saas"
        os.environ["SYSADMIN_API_KEY"] = "short"
        try:
            with self.assertRaises(EnvironmentError):
                build_tenant_bootstrap_env(
                    self.tenant,
                    {"AVENDER_SETUP_TOKEN": "a", "MCP_SERVER_TOKEN": "b"},
                )
        finally:
            os.environ.pop("SYSADMIN_API_URL", None)
            os.environ.pop("SYSADMIN_API_KEY", None)

    def test_create_tenant_calls_vault_before_deploy(self) -> None:
        os.environ["SYSADMIN_API_KEY"] = "x" * 32
        os.environ["SYSADMIN_API_URL"] = "https://sysadmin.example.com/api/saas"
        self.client.force_login(self.admin)
        try:
            with patch(
                "tenants.api.provision_tenant_secrets",
                return_value={"AVENDER_SETUP_TOKEN": "a", "MCP_SERVER_TOKEN": "b"},
            ) as prov_mock:
                with patch("tenants.api.build_tenant_bootstrap_env", return_value={"TENANT_ID": "id"}) as env_mock:
                    with patch("tenants.api.deploy_tenant_pod", return_value={"instance": {"id": "abc"}}) as deploy_mock:
                        response = self.client.post(
                            "/api/saas/tenants",
                            data={"name": "New Tenant", "email": "new-tenant@example.com", "plan_name": "Basic"},
                            content_type="application/json",
                        )
            self.assertEqual(response.status_code, 200)
            prov_mock.assert_called_once()
            env_mock.assert_called_once()
            deploy_mock.assert_called_once()
        finally:
            os.environ.pop("SYSADMIN_API_KEY", None)
            os.environ.pop("SYSADMIN_API_URL", None)
