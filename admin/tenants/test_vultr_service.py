from __future__ import annotations

import base64
import os
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth.models import User

from tenants.models import Tenant, Plan
from tenants.vultr_service import (
    deploy_tenant_pod,
    suspend_tenant_pod,
    reactivate_tenant_pod,
    delete_tenant_pod,
)


class VultrServiceMockTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user("vultrowner", password="x")
        self.plan = Plan.objects.create(
            name="Basic Vultr", price_monthly=10, max_conversations=100, max_numbers=1,
            vultr_plan="vc2-1c-1gb"
        )
        self.tenant = Tenant.objects.create(
            name="Vultr Tenant",
            email="vultr@example.com",
            owner=self.owner,
            plan=self.plan,
            status="pending",
        )

    def test_deploy_tenant_pod_success(self) -> None:
        with patch.dict(os.environ, {
            "VULTR_API_KEY": "fake-vultr-key",
        }):
            mock_resp = MagicMock()
            mock_resp.status_code = 202
            mock_resp.json.return_value = {"instance": {"id": "vultr-12345"}}
            
            with patch("tenants.vultr_service.requests.post", return_value=mock_resp) as mock_post:
                bootstrap_env = {"AVENDER_SETUP_TOKEN": "secret-abc", "SYSADMIN_API_URL": "http://localhost"}
                result = deploy_tenant_pod(self.tenant, bootstrap_env)
                
                self.assertEqual(result["instance"]["id"], "vultr-12345")
                self.tenant.refresh_from_db()
                self.assertEqual(self.tenant.vultr_instance_id, "vultr-12345")
                self.assertEqual(self.tenant.status, "active")
                self.assertIsNotNone(self.tenant.assigned_port)

                # Verify user_data contains encoded secrets
                mock_post.assert_called_once()
                payload = mock_post.call_args[1]["json"]
                self.assertIn("user_data", payload)
                
                # Decode base64 user_data
                user_data_decoded = base64.b64decode(payload["user_data"]).decode("utf-8")
                self.assertIn("AVENDER_SETUP_TOKEN", user_data_decoded)

    def test_deploy_tenant_pod_vultr_error(self) -> None:
        with patch.dict(os.environ, {"VULTR_API_KEY": "fake-vultr-key"}):
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = "Bad Request"
            
            with patch("tenants.vultr_service.requests.post", return_value=mock_resp):
                with self.assertRaises(RuntimeError) as ctx:
                    deploy_tenant_pod(self.tenant, {})
                self.assertIn("400", str(ctx.exception))
                
                self.tenant.refresh_from_db()
                self.assertEqual(self.tenant.status, "pending")

    def test_suspend_tenant_pod(self) -> None:
        self.tenant.vultr_instance_id = "vultr-xyz"
        self.tenant.save(update_fields=["vultr_instance_id"])
        
        with patch.dict(os.environ, {"VULTR_API_KEY": "fake-vultr-key"}):
            mock_resp = MagicMock()
            mock_resp.status_code = 204
            
            with patch("tenants.vultr_service.requests.post", return_value=mock_resp) as mock_post:
                result = suspend_tenant_pod(self.tenant)
                self.assertEqual(result["status"], "halted")
                
                self.tenant.refresh_from_db()
                self.assertEqual(self.tenant.status, "suspended")
                
                mock_post.assert_called_once()
                self.assertTrue(mock_post.call_args[0][0].endswith("/vultr-xyz/halt"))

    def test_reactivate_tenant_pod(self) -> None:
        self.tenant.vultr_instance_id = "vultr-xyz"
        self.tenant.status = "suspended"
        self.tenant.save(update_fields=["vultr_instance_id", "status"])
        
        with patch.dict(os.environ, {"VULTR_API_KEY": "fake-vultr-key"}):
            mock_resp = MagicMock()
            mock_resp.status_code = 204
            
            with patch("tenants.vultr_service.requests.post", return_value=mock_resp) as mock_post:
                result = reactivate_tenant_pod(self.tenant)
                self.assertEqual(result["status"], "started")
                
                self.tenant.refresh_from_db()
                self.assertEqual(self.tenant.status, "active")
                
                mock_post.assert_called_once()
                self.assertTrue(mock_post.call_args[0][0].endswith("/vultr-xyz/start"))

    def test_delete_tenant_pod(self) -> None:
        self.tenant.vultr_instance_id = "vultr-xyz"
        self.tenant.assigned_port = 45005
        self.tenant.status = "suspended"
        self.tenant.save()
        
        with patch.dict(os.environ, {"VULTR_API_KEY": "fake-vultr-key"}):
            mock_resp = MagicMock()
            mock_resp.status_code = 204
            
            with patch("tenants.vultr_service.requests.delete", return_value=mock_resp) as mock_del:
                result = delete_tenant_pod(self.tenant)
                self.assertEqual(result["status"], "deleted")
                
                self.tenant.refresh_from_db()
                self.assertEqual(self.tenant.status, "deleted")
                self.assertEqual(self.tenant.vultr_instance_id, "")
                self.assertIsNone(self.tenant.assigned_port)
                
                mock_del.assert_called_once()
                self.assertTrue(mock_del.call_args[0][0].endswith("/vultr-xyz"))
