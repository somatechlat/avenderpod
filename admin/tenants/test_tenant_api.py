from __future__ import annotations

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from tenants.models import Tenant, CatalogItem, TenantConfig, TenantUsage, InteractionRecord


@override_settings(SECURE_SSL_REDIRECT=False)
class TenantOwnerAPITests(TestCase):
    def setUp(self) -> None:
        self.owner1 = User.objects.create_user("owner1", "o1@example.com", "x")
        self.owner2 = User.objects.create_user("owner2", "o2@example.com", "x")
        self.admin = User.objects.create_superuser("admin3", "admin3@example.com", "x")
        
        self.tenant1 = Tenant.objects.create(name="T1", email="t1@ex.com", owner=self.owner1)
        self.tenant2 = Tenant.objects.create(name="T2", email="t2@ex.com", owner=self.owner2)

    def test_list_catalog_isolation(self) -> None:
        CatalogItem.objects.create(tenant=self.tenant1, name="Pizza", price=10)
        CatalogItem.objects.create(tenant=self.tenant2, name="Burger", price=5)
        
        self.client.force_login(self.owner1)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant1.id}/catalog")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["name"], "Pizza")
        
        # Owner 1 cannot access Owner 2's catalog
        resp = self.client.get(f"/api/saas/tenants/{self.tenant2.id}/catalog")
        self.assertEqual(resp.status_code, 403)
        
        # Admin can access both
        self.client.force_login(self.admin)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant2.id}/catalog")
        self.assertEqual(resp.status_code, 200)

    def test_create_catalog_item(self) -> None:
        self.client.force_login(self.owner1)
        resp = self.client.post(
            f"/api/saas/tenants/{self.tenant1.id}/catalog",
            data={"name": "Soda", "price": 2.50, "description": "Drink"},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Soda")
        
        self.assertTrue(CatalogItem.objects.filter(tenant=self.tenant1, name="Soda").exists())

    def test_tenant_config_crud_isolation(self) -> None:
        TenantConfig.objects.create(tenant=self.tenant1, key="greeting", value="Hello T1")
        
        self.client.force_login(self.owner1)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant1.id}/config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("greeting"), "Hello T1")
        
        resp = self.client.post(
            f"/api/saas/tenants/{self.tenant1.id}/config",
            data={"key": "tone", "value": "formal"},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(resp.json()["value"], "formal")
        
        # Isolation check
        resp = self.client.post(
            f"/api/saas/tenants/{self.tenant2.id}/config",
            data={"key": "hack", "value": "yes"},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_usage_reporting_aggregation(self) -> None:
        self.client.force_login(self.owner1)
        
        # Report usage step 1
        resp = self.client.post(
            f"/api/saas/tenants/{self.tenant1.id}/usage/report",
            data={
                "conversations_used": 5,
                "messages_used": 20,
                "transcription_seconds_used": 120,
                "catalog_items_used": 0,
                "storage_bytes_used": 1024,
            },
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["messages_used"], 20)
        
        # Report usage step 2 (should accumulate)
        resp = self.client.post(
            f"/api/saas/tenants/{self.tenant1.id}/usage/report",
            data={
                "conversations_used": 2,
                "messages_used": 10,
                "transcription_seconds_used": 0,
                "catalog_items_used": 0,
                "storage_bytes_used": 0,
            },
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["messages_used"], 30)
        self.assertEqual(resp.json()["conversations_used"], 7)
        
        # Fetch usage
        resp = self.client.get(f"/api/saas/tenants/{self.tenant1.id}/usage")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["messages_used"], 30)

        # Isolation check
        resp = self.client.get(f"/api/saas/tenants/{self.tenant2.id}/usage")
        self.assertEqual(resp.status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False)
class TenantInteractionsAPITests(TestCase):
    """
    Verifies that GET /tenants/{id}/interactions enforces strict cross-tenant
    data isolation. Owners see only their own records; cross-tenant access is
    rejected with 403; SysAdmins see all.
    """

    def setUp(self) -> None:
        self.owner1 = User.objects.create_user("ia_owner1", "ia1@ex.com", "x")
        self.owner2 = User.objects.create_user("ia_owner2", "ia2@ex.com", "x")
        self.admin = User.objects.create_superuser("ia_admin", "ia_admin@ex.com", "x")

        self.tenant1 = Tenant.objects.create(name="IA-T1", email="ia1@ex.com", owner=self.owner1)
        self.tenant2 = Tenant.objects.create(name="IA-T2", email="ia2@ex.com", owner=self.owner2)

        # Seed one interaction per tenant
        self.record1 = InteractionRecord.objects.create(
            tenant=self.tenant1,
            customer_wa_id="+593979000001",
            archetype="buyer",
            status="completed",
        )
        self.record2 = InteractionRecord.objects.create(
            tenant=self.tenant2,
            customer_wa_id="+593979000002",
            archetype="support",
            status="pending",
        )

    def test_owner_sees_own_interactions(self) -> None:
        self.client.force_login(self.owner1)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant1.id}/interactions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["customer_wa_id"], "+593979000001")
        self.assertEqual(data[0]["archetype"], "buyer")

    def test_owner_cannot_see_other_tenant_interactions(self) -> None:
        """Cross-tenant isolation: owner1 must be blocked from tenant2's data."""
        self.client.force_login(self.owner1)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant2.id}/interactions")
        self.assertEqual(resp.status_code, 403)

    def test_sysadmin_can_see_any_tenant_interactions(self) -> None:
        self.client.force_login(self.admin)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant2.id}/interactions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["customer_wa_id"], "+593979000002")

    def test_unauthenticated_request_rejected(self) -> None:
        resp = self.client.get(f"/api/saas/tenants/{self.tenant1.id}/interactions")
        # Ninja returns 401 for unauthenticated requests
        self.assertIn(resp.status_code, [401, 403])


@override_settings(SECURE_SSL_REDIRECT=False)
class TenantListOwnerScopingTests(TestCase):
    """
    Verifies that GET /tenants returns only the requesting owner's tenants
    when not a superuser, but all tenants when a superuser.
    """

    def setUp(self) -> None:
        self.owner1 = User.objects.create_user("lt_owner1", "lt1@ex.com", "x")
        self.owner2 = User.objects.create_user("lt_owner2", "lt2@ex.com", "x")
        self.admin = User.objects.create_superuser("lt_admin", "lt_admin@ex.com", "x")

        self.tenant1 = Tenant.objects.create(name="LT-T1", email="lt1@ex.com", owner=self.owner1)
        self.tenant2 = Tenant.objects.create(name="LT-T2", email="lt2@ex.com", owner=self.owner2)

    def test_owner_sees_only_own_tenants(self) -> None:
        self.client.force_login(self.owner1)
        resp = self.client.get("/api/saas/tenants")
        self.assertEqual(resp.status_code, 200)
        names = [t["name"] for t in resp.json()]
        self.assertIn("LT-T1", names)
        self.assertNotIn("LT-T2", names)

    def test_sysadmin_sees_all_tenants(self) -> None:
        self.client.force_login(self.admin)
        resp = self.client.get("/api/saas/tenants")
        self.assertEqual(resp.status_code, 200)
        names = [t["name"] for t in resp.json()]
        self.assertIn("LT-T1", names)
        self.assertIn("LT-T2", names)

    def test_unauthenticated_tenant_list_rejected(self) -> None:
        resp = self.client.get("/api/saas/tenants")
        self.assertIn(resp.status_code, [401, 403])


@override_settings(SECURE_SSL_REDIRECT=False)
class TenantStatusEndpointTests(TestCase):
    """
    Verifies the GET /tenants/{id}/status endpoint under controlled conditions.
    The Vultr API call is mocked to keep tests cost-neutral and deterministic.
    """

    def setUp(self) -> None:
        self.admin = User.objects.create_superuser("st_admin", "st_admin@ex.com", "x")
        self.owner = User.objects.create_user("st_owner", "st_owner@ex.com", "x")
        self.other = User.objects.create_user("st_other", "st_other@ex.com", "x")

        self.tenant = Tenant.objects.create(
            name="ST-T1",
            email="st@ex.com",
            owner=self.owner,
            status="active",
            assigned_port=45001,
            vultr_instance_id="fake-instance-id",
        )

    def test_status_no_port_returns_unknown(self) -> None:
        """A tenant with no assigned_port returns unknown container status."""
        self.tenant.assigned_port = None
        self.tenant.save(update_fields=["assigned_port"])

        self.client.force_login(self.admin)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant.id}/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["container_status"], "unknown")
        self.assertFalse(data["stt_available"])

    def test_status_vultr_unreachable_returns_error(self) -> None:
        """When the Vultr API is unreachable, status falls back gracefully.

        We must patch get_vultr_api_key so _vultr_headers() can build its
        auth header without reading a real secret file.  Then we simulate a
        network timeout to confirm the view returns a 200 with a safe error
        status rather than propagating the exception.
        """
        from unittest.mock import patch, MagicMock
        import requests as req_lib

        self.client.force_login(self.admin)
        with patch(
            "tenants.vultr_service.get_vultr_api_key",
            return_value="fake-vultr-key-for-test",
        ), patch(
            "tenants.api.requests.get",
            side_effect=req_lib.RequestException("timeout"),
        ):
            resp = self.client.get(f"/api/saas/tenants/{self.tenant.id}/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(data["container_status"], ["error", "unknown"])

    def test_status_non_owner_forbidden(self) -> None:
        """A non-owner, non-admin user must be blocked from status endpoint."""
        self.client.force_login(self.other)
        resp = self.client.get(f"/api/saas/tenants/{self.tenant.id}/status")
        self.assertIn(resp.status_code, [401, 403])

