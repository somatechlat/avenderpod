from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Permission

from tenants.models import Tenant, Plan, InteractionRecord, VaultRecord


@override_settings(SECURE_SSL_REDIRECT=False)
class SysAdminAPITests(TestCase):
    def setUp(self) -> None:
        self.admin = User.objects.create_superuser("sysadmin", "sysadmin@example.com", "x")
        self.staff = User.objects.create_user("staff", "staff@example.com", "x", is_staff=True)
        self.user = User.objects.create_user("user", "user@example.com", "x")
        
        # Give staff plan view permission but not add
        perm_view = Permission.objects.get(codename="view_plan")
        self.staff.user_permissions.add(perm_view)

        self.plan = Plan.objects.create(name="Base", price_monthly=10)
        self.tenant = Tenant.objects.create(
            name="API Tenant", email="api@example.com", owner=self.user, plan=self.plan
        )

    def test_list_plans_requires_permission(self) -> None:
        self.client.force_login(self.user)
        resp = self.client.get("/api/saas/plans")
        self.assertEqual(resp.status_code, 403)
        
        self.client.force_login(self.staff)
        resp = self.client.get("/api/saas/plans")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_create_plan_requires_add_permission(self) -> None:
        self.client.force_login(self.staff)  # Has view, not add
        resp = self.client.post(
            "/api/saas/plans", 
            data={"name": "New Plan", "slug": "new-plan", "price_monthly": 50}, 
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)
        
        self.client.force_login(self.admin)
        resp = self.client.post(
            "/api/saas/plans", 
            data={"name": "New Plan", "slug": "new-plan", "price_monthly": 50}, 
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "New Plan")

    def test_update_plan_requires_change_permission(self) -> None:
        self.client.force_login(self.admin)
        resp = self.client.patch(
            f"/api/saas/plans/{self.plan.id}", 
            data={"price_monthly": 99}, 
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price_monthly, 99)

    def test_list_vault_records_god_mode_only(self) -> None:
        VaultRecord.objects.create(tenant=self.tenant, vault_path="secret/test")
        
        self.client.force_login(self.staff) # Not superuser
        resp = self.client.get("/api/saas/vault")
        self.assertEqual(resp.status_code, 403)
        
        self.client.force_login(self.admin)
        resp = self.client.get("/api/saas/vault")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["vault_path"], "secret/test")

    def test_list_interactions_god_mode_only(self) -> None:
        InteractionRecord.objects.create(
            tenant=self.tenant, customer_wa_id="+123", archetype="test", status="completed"
        )
        
        self.client.force_login(self.user)
        resp = self.client.get("/api/saas/interactions")
        self.assertEqual(resp.status_code, 403)
        
        self.client.force_login(self.admin)
        resp = self.client.get("/api/saas/interactions")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["customer_wa_id"], "+123")

    def test_suspend_tenant_calls_vultr_service(self) -> None:
        # Give staff suspend perm
        perm = Permission.objects.get(codename="suspend_tenant")
        self.staff.user_permissions.add(perm)
        
        self.client.force_login(self.staff)
        
        with patch("tenants.api.suspend_tenant_pod") as mock_suspend:
            mock_suspend.return_value = {"status": "halted"}
            resp = self.client.post(f"/api/saas/tenants/{self.tenant.id}/suspend")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["ok"])
            mock_suspend.assert_called_once_with(self.tenant)

    def test_reactivate_tenant_calls_vultr_service(self) -> None:
        perm = Permission.objects.get(codename="reactivate_tenant")
        self.staff.user_permissions.add(perm)
        
        self.client.force_login(self.staff)
        
        with patch("tenants.api.reactivate_tenant_pod") as mock_reactivate:
            mock_reactivate.return_value = {"status": "started"}
            resp = self.client.post(f"/api/saas/tenants/{self.tenant.id}/reactivate")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["ok"])
            mock_reactivate.assert_called_once_with(self.tenant)
