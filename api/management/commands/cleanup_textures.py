from django.core.management.base import BaseCommand
from api.models import purge_expired_textures


class Command(BaseCommand):
    help = "Deletes temporary textures older than 24 hours (rows + files)."

    def handle(self, *args, **options):
        count = purge_expired_textures()
        self.stdout.write(self.style.SUCCESS(f"Purged {count} expired texture(s)."))