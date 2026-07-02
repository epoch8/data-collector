"""Юнит-тесты шифрования SSH-ключей (api.git_credential_crypto)."""

from __future__ import annotations

from django.test import SimpleTestCase, override_settings

from api.git_credential_crypto import decrypt_private_key, encrypt_private_key

SAMPLE_KEY = (
    "-----BEGIN OPENSSH PRIVATE KEY-----\n"
    "b3BlbnNzaC1rZXktdjEAAAAA...fake...AAAA\n"
    "-----END OPENSSH PRIVATE KEY-----\n"
)


class GitCredentialCryptoTests(SimpleTestCase):
    def test_round_trip(self):
        token = encrypt_private_key(SAMPLE_KEY)
        self.assertEqual(decrypt_private_key(token), SAMPLE_KEY)

    def test_ciphertext_differs_from_plaintext(self):
        token = encrypt_private_key(SAMPLE_KEY)
        self.assertNotEqual(token, SAMPLE_KEY)
        self.assertNotIn(SAMPLE_KEY, token)

    def test_ciphertext_is_ascii(self):
        token = encrypt_private_key(SAMPLE_KEY)
        token.encode("ascii")  # не должно бросить исключение

    def test_nondeterministic_ciphertext(self):
        # Fernet добавляет случайный IV — два шифрования дают разный результат,
        # но оба расшифровываются в исходник.
        a = encrypt_private_key(SAMPLE_KEY)
        b = encrypt_private_key(SAMPLE_KEY)
        self.assertNotEqual(a, b)
        self.assertEqual(decrypt_private_key(a), decrypt_private_key(b))

    def test_empty_string_round_trip(self):
        token = encrypt_private_key("")
        self.assertEqual(decrypt_private_key(token), "")

    def test_unicode_round_trip(self):
        secret = "ключ-с-юникодом-🔑"
        self.assertEqual(decrypt_private_key(encrypt_private_key(secret)), secret)

    @override_settings(SECRET_KEY="a-completely-different-secret")
    def _encrypt_with_other_key(self) -> str:
        return encrypt_private_key(SAMPLE_KEY)

    def test_wrong_secret_cannot_decrypt(self):
        from cryptography.fernet import InvalidToken

        token = self._encrypt_with_other_key()
        # Текущий (дефолтный тестовый) SECRET_KEY не должен расшифровать чужой токен.
        with self.assertRaises(InvalidToken):
            decrypt_private_key(token)
