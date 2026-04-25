import os
import httpx
import ipaddress
import socket
from urllib.parse import urlparse
from helpers.tool import Tool, Response
from helpers.print_style import PrintStyle
from helpers.network import is_loopback_address

class GodMode(Tool):
    """
    Handles the 'God Mode' (Creator Override) challenge-response flow.
    Allows the Creator to take control of the agent after 2FA verification.
    """

    async def execute(self, action: str, password: str = None, pin: str = None):
        tenant_id = os.environ.get("TENANT_ID")
        sysadmin_url = os.environ.get("SYSADMIN_API_URL")
        sysadmin_api_key = os.environ.get("SYSADMIN_API_KEY", "").strip()

        if not tenant_id or not sysadmin_url:
            return Response(message="Error: System environment not configured for God Mode. Missing TENANT_ID or SYSADMIN_API_URL.", break_loop=True)
        if not self._is_allowed_sysadmin_url(sysadmin_url):
            return Response(
                message="Error: SYSADMIN_API_URL must be loopback/private HTTPS (or explicit local HTTP) for God Mode.",
                break_loop=True,
            )

        if action == "init":
            return await self._init_challenge(sysadmin_url, tenant_id, sysadmin_api_key)
        elif action == "verify":
            if not password or not pin:
                return Response(message="Error: Both Master Password and Session PIN are required for verification.", break_loop=False)
            return await self._verify_challenge(sysadmin_url, tenant_id, password, pin, sysadmin_api_key)
        else:
            return Response(message=f"Error: Unknown action '{action}'. Use 'init' or 'verify'.", break_loop=False)

    def _is_allowed_sysadmin_url(self, base_url: str) -> bool:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        allowed_hosts = {
            host.strip().lower()
            for host in os.environ.get("SYSADMIN_API_ALLOWED_HOSTS", "").split(",")
            if host.strip()
        }
        hostname = parsed.hostname.lower()
        if hostname in allowed_hosts:
            return True
        # The service token must only be sent to local/private control-plane hosts.
        if is_loopback_address(hostname):
            return True
        try:
            infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror:
            return False
        for _family, _type, _proto, _canonname, sockaddr in infos:
            ip = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
            if not (ip.is_private or ip.is_loopback):
                return False
        return True

    def _headers(self, api_key: str) -> dict[str, str]:
        headers = {}
        if api_key:
            headers["X-API-KEY"] = api_key
        return headers

    async def _init_challenge(self, base_url: str, tenant_id: str, api_key: str):
        url = f"{base_url}/auth/init-challenge"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params={"tenant_id": tenant_id},
                    timeout=10.0,
                    headers=self._headers(api_key),
                )
                if response.status_code == 200:
                    PrintStyle.standard("God Mode challenge initiated successfully.")
                    return Response(
                        message="Challenge initiated. I have sent a notification to the Master Control Plane. "
                                "Please provide the Master Password and the 4-digit Session PIN shown in the dashboard.",
                        break_loop=False
                    )
                else:
                    return Response(message=f"Failed to initiate challenge: {response.text}", break_loop=True)
        except Exception as e:
            return Response(message=f"Error connecting to SysAdmin: {str(e)}", break_loop=True)

    async def _verify_challenge(self, base_url: str, tenant_id: str, password: str, pin: str, api_key: str):
        url = f"{base_url}/auth/verify-challenge"
        payload = {
            "tenant_id": tenant_id,
            "password": password,
            "pin": pin
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=10.0,
                    headers=self._headers(api_key),
                )
                data = response.json()
                if response.status_code == 200 and data.get("ok"):
                    PrintStyle.standard("God Mode access GRANTED.")
                    return Response(
                        message="ACCESS GRANTED. Welcome back, Creator. I am now under your direct command. "
                                "Authentication cleared. How may I serve you?",
                        break_loop=False
                    )
                else:
                    return Response(message=f"ACCESS DENIED: {data.get('message', 'Unknown error')}", break_loop=False)
        except Exception as e:
            return Response(message=f"Error connecting to SysAdmin: {str(e)}", break_loop=True)
