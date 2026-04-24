from django.core.management.base import BaseCommand

from api.firebase_user_sync import sync_collector_users_from_firebase


class Command(BaseCommand):
    help = "Импорт пользователей из Firebase Authentication в модель CollectorUser (для cron)."

    def handle(self, *args, **options):
        r = sync_collector_users_from_firebase()
        self.stdout.write(
            self.style.SUCCESS(
                f"Firebase: всего {r.total_firebase}, создано {r.created}, "
                f"обновлён email {r.updated_email}, без изменений {r.unchanged}."
            )
        )
