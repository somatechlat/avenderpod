from __future__ import annotations

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from tenants.models import Tenant, CatalogItem, TenantConfig, TenantUsage


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
