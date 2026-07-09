import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.server import (
    ROLE_SECRETS,
    ROLE_SECRET_KEYS,
    UserRole,
    app,
    get_current_user_role,
    require_role,
)
from config.privilege_keys import SYSTEM_3D_VIEW_PRIVILEGE_KEY


class AuthenticationKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_all_configured_privilege_keys_authenticate_to_expected_role(self):
        for role in (UserRole.USER, UserRole.SYSTEM, UserRole.ADMIN):
            with self.subTest(role=role.value):
                self.assertGreaterEqual(len(ROLE_SECRET_KEYS[role]), 3)
                for key in ROLE_SECRET_KEYS[role]:
                    self.assertEqual(get_current_user_role(key), role)

    def test_3d_view_system_key_authenticates_as_system_when_configured(self):
        if not SYSTEM_3D_VIEW_PRIVILEGE_KEY:
            self.skipTest("MULTIUAV_3D_VIEW_SYSTEM_KEY is not configured")

        self.assertIn(SYSTEM_3D_VIEW_PRIVILEGE_KEY, ROLE_SECRET_KEYS[UserRole.SYSTEM])
        self.assertEqual(
            get_current_user_role(SYSTEM_3D_VIEW_PRIVILEGE_KEY),
            UserRole.SYSTEM,
        )

    def test_role_secrets_keep_first_key_compatibility(self):
        for role, keys in ROLE_SECRET_KEYS.items():
            with self.subTest(role=role.value):
                self.assertEqual(ROLE_SECRETS[role], keys[0])

    def test_existing_agent_authentication_and_omitted_key_behavior_remain(self):
        self.assertEqual(get_current_user_role(None), UserRole.AGENT)
        self.assertEqual(
            get_current_user_role(ROLE_SECRETS[UserRole.AGENT]),
            UserRole.AGENT,
        )

        self.assertEqual(self.client.get("/version").status_code, 200)
        agent_headers = {"X-API-Key": ROLE_SECRETS[UserRole.AGENT]}
        self.assertEqual(self.client.get("/version", headers=agent_headers).status_code, 200)

    def test_invalid_key_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user_role("invalid-api-key")

        self.assertEqual(context.exception.status_code, 401)

        response = self.client.get("/version", headers={"X-API-Key": "invalid-api-key"})
        self.assertEqual(response.status_code, 401)

    def test_role_hierarchy_still_inherits_permissions(self):
        request = SimpleNamespace(state=SimpleNamespace())

        self.assertEqual(
            require_role(UserRole.USER)(request, current_role=UserRole.USER),
            UserRole.USER,
        )
        self.assertEqual(
            require_role(UserRole.USER)(request, current_role=UserRole.SYSTEM),
            UserRole.SYSTEM,
        )
        self.assertEqual(
            require_role(UserRole.SYSTEM)(request, current_role=UserRole.ADMIN),
            UserRole.ADMIN,
        )

        with self.assertRaises(HTTPException) as context:
            require_role(UserRole.SYSTEM)(request, current_role=UserRole.USER)

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
