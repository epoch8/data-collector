"""Пересохранить SSH-ключи в БД с нормализацией LF (после фикса libcrypto на Windows)."""

from django.core.management.base import BaseCommand

from api.git_credential_crypto import decrypt_private_key, encrypt_private_key
from api.models import GitCredential
from api.project_git import GitProjectError, normalize_private_key, public_key_from_private


class Command(BaseCommand):
    help = "Нормализовать приватные ключи в GitCredential (CRLF → LF)."

    def handle(self, *args, **options):
        for cred in GitCredential.objects.all():
            try:
                raw = decrypt_private_key(cred.private_key_encrypted)
                norm = normalize_private_key(raw)
                cred.private_key_encrypted = encrypt_private_key(norm)
                cred.public_key = public_key_from_private(norm)
                cred.save(update_fields=["private_key_encrypted", "public_key"])
                self.stdout.write(self.style.SUCCESS(f"OK credential #{cred.pk}"))
            except GitProjectError as e:
                self.stderr.write(f"credential #{cred.pk}: {e.message}")
            except Exception as e:
                self.stderr.write(f"credential #{cred.pk}: {e}")
