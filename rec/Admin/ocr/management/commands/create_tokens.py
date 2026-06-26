from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = '为所有用户创建或更新Token'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='指定用户名，如果未提供则为所有用户创建token',
        )

    def handle(self, *args, **options):
        username = options.get('username')

        if username:
            users = User.objects.filter(username=username)
        else:
            users = User.objects.all()

        for user in users:
            token, created = Token.objects.get_or_create(user=user)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'为用户 {user.username} 创建token: {token.key}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'用户 {user.username} 的token已存在: {token.key}')
                )
