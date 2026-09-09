import unittest

from backend.app.password_utils import validate_password_for_bcrypt


class PasswordValidationTests(unittest.TestCase):
    def test_accepts_password_matching_frontend_rules(self):
        password = "Valid@123"

        normalized, error = validate_password_for_bcrypt(password)

        self.assertEqual(normalized, password)
        self.assertIsNone(error)

    def test_rejects_password_longer_than_bcrypt_byte_limit(self):
        normalized, error = validate_password_for_bcrypt("é" * 37)

        self.assertEqual(normalized, "")
        self.assertEqual(error, "Password is too long for secure storage.")

    def test_reports_each_complexity_requirement(self):
        cases = {
            "Short1!": "Password must be 8 to 12 characters long.",
            "lowercase1!": "Password must include at least one uppercase letter.",
            "UPPERCASE1!": "Password must include at least one lowercase letter.",
            "NoNumbers!": "Password must include at least one number.",
            "NoSpecial1": "Password must include at least one special character.",
        }

        for password, expected_error in cases.items():
            with self.subTest(password=password):
                normalized, error = validate_password_for_bcrypt(password)
                self.assertEqual(normalized, password)
                self.assertEqual(error, expected_error)


if __name__ == "__main__":
    unittest.main()
