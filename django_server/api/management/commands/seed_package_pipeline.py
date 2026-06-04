"""Заполнить project SQLite и depth blobs для пакета из datapipe_test."""

from django.core.management.base import BaseCommand

from api.models import PackageSession
from api.project_pipeline_seed import seed_package_pipeline


class Command(BaseCommand):
    help = "Сид pipeline-заглушек (GT + inference + .npy) для завершённого пакета."

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument("package_id")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать существующие строки и depth blobs",
        )

    def handle(self, *args, **options):
        session = PackageSession.objects.filter(
            project__project_id=options["project_id"],
            package_id=options["package_id"],
        ).select_related("project").first()
        if not session:
            self.stderr.write(self.style.ERROR("Package session not found"))
            return
        if session.phase != PackageSession.Phase.COMPLETED:
            self.stderr.write(
                self.style.WARNING(
                    f"Phase is {session.phase}; seeding anyway for local dev",
                ),
            )
        stats = seed_package_pipeline(session, force=options["force"])
        self.stdout.write(self.style.SUCCESS(str(stats)))
