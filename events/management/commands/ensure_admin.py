from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from events.models import UserProfile


class Command(BaseCommand):
    help = 'Create default admin user (Admin/Admin) if no superuser exists'

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('Superuser already exists — skipping.')
            return

        user = User.objects.create_superuser(
            username='Admin',
            email='',
            password='Admin',
        )
        UserProfile.objects.create(user=user, must_change_password=True)
        self.stdout.write(self.style.SUCCESS(
            'Created default admin (Admin/Admin) — password change required on first login.'
        ))
