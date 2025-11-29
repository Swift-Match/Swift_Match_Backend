from django.contrib.auth.signals import user_logged_in
from django.utils import timezone


def set_first_login(sender, request, user, **kwargs):
    if not user.first_login:
        user.first_login = timezone.now()
        user.save()


user_logged_in.connect(set_first_login)
