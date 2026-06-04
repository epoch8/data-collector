from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Устарело: конфиг проектов теперь только в Git (см. specs/git-backed-projects.md)."

    def handle(self, *args, **options):
        self.stderr.write(
            "load_projects_from_assets отключён: создайте проект в /ui/projects/new/ с Git-репозиторием."
        )
