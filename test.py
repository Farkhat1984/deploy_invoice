import httpx
import logging
import asyncio
from typing import Optional, Dict

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class AuthTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def test_auth(self) -> Optional[Dict]:
        try:
            # Test health check first
            health_resp = await self.client.get("/health")
            logger.info(f"Health check response: {health_resp.status_code}")
            logger.info(f"Health check body: {health_resp.text}")

            # Test authentication
            auth_data = {
                "username": "admin",
                "password": "admin",
                "grant_type": "password"
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }

            logger.info("Attempting authentication...")
            auth_resp = await self.client.post(
                "/api/v1/auth/token",
                data=auth_data,
                headers=headers
            )

            logger.info(f"Auth Response Status: {auth_resp.status_code}")
            logger.info(f"Auth Response Headers: {dict(auth_resp.headers)}")
            logger.info(f"Auth Response Body: {auth_resp.text}")

            return auth_resp.json() if auth_resp.status_code == 200 else None

        except Exception as e:
            logger.error(f"Error during authentication test: {str(e)}")
            return None

    async def close(self):
        await self.client.aclose()


async def main():
    tester = AuthTester()
    try:
        await tester.test_auth()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())