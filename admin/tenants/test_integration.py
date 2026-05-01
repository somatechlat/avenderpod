from __future__ import annotations

import os
import unittest
import requests

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from tenants.models import Tenant, Plan
from tenants.vultr_service import deploy_tenant_pod, delete_tenant_pod

# To run this live:
# docker exec -e VULTR_LIVE_TEST=1 avender_sysadmin python manage.py test tenants.test_integration

@unittest.skipUnless(os.environ.get("VULTR_LIVE_TEST"), "Live Vultr testing disabled unless VULTR_LIVE_TEST=1")
@override_settings(SECURE_SSL_REDIRECT=False)
class VultrLiveIntegrationTests(TestCase):
    def setUp(self) -> None:
        if not os.environ.get("VULTR_API_KEY"):
            self.skipTest("VULTR_API_KEY is not set.")
            
        self.owner = User.objects.create_user("liveowner", "live@ex.com", "x")
        self.plan = Plan.objects.create(name="Live Plan", price_monthly=0, vultr_plan="vc2-1c-1gb")
        self.tenant = Tenant.objects.create(
            name="Live Integration Tenant", 
            email="live@ex.com", 
            owner=self.owner, 
            plan=self.plan,
            status="pending"
        )
        
    def tearDown(self) -> None:
        # Emergency cleanup to prevent billing if test fails midway
        self.tenant.refresh_from_db()
        if self.tenant.vultr_instance_id:
            try:
                delete_tenant_pod(self.tenant)
            except Exception as e:
                print(f"Cleanup failed for tenant {self.tenant.id}: {e}")

    def test_live_provision_and_teardown(self) -> None:
        """
        Warning: This spins up a real VM on Vultr and then destroys it.
        It may take ~2 minutes to execute completely.
        """
        # 1. Provision
        bootstrap_env = {
            "AVENDER_SETUP_TOKEN": "live-test-token",
            "SYSADMIN_API_URL": "https://avender.store",
            "A0_MEMORY_LIMIT": "1g"
        }
        
        result = deploy_tenant_pod(self.tenant, bootstrap_env)
        self.assertIn("instance", result)
        self.assertIsNotNone(self.tenant.vultr_instance_id)
        self.assertEqual(self.tenant.status, "active")
        
        # 2. Wait for instance to become active and reachable
        # Note: We won't actually wait the full 2 mins for docker to install here
        # since that slows tests down too much, we just verify the API accepted it.
        # But we could poll the instance status from Vultr if needed.
        
        # 3. Teardown
        del_result = delete_tenant_pod(self.tenant)
        self.assertEqual(del_result["status"], "deleted")
        self.assertEqual(self.tenant.status, "deleted")
        self.assertEqual(self.tenant.vultr_instance_id, "")
