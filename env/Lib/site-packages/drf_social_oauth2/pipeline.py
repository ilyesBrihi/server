from threading import Thread
from random import randint
from time import time

from social_core.pipeline.partial import partial

from django.core.mail import send_mail
from django.utils import timezone
from drf_social_oauth2.models import MultiFactorAuth


@partial
def multi_factor_auth(strategy, details, user=None, is_new=False, *args, **kwargs):
    """
    At this stage, only cases with email granted permission will be taken into account.
    That means when setting up your Social Application, you need to grant email permissions
    so that your token can read the user's email.
    """
    # at this stage, I am working on a case where only new users are going to receive
    # the 2-factor email. This will, obviously, be extended.

    if not user:
        if 'email' not in details:
            raise Exception('Missing email for 2-factor auth')

        code = randint(100000, 999999)
        multi_factor_auth = MultiFactorAuth(
            code=code,
            backend=kwargs['backend'].data['backend'],
            client_id=kwargs['backend'].data['client_id'],
            client_secret=kwargs['backend'].data['client_secret'],
            token=kwargs['backend'].data['token'],
            expires=timezone.now() + timezone.timedelta(minutes=30)
        )
        multi_factor_auth.save()

        email_thread = Thread(
            target=send_mail, args=(
                "Your 2-factor authentication code",
                f"This is your 2-factor auth code {code}",
                "waglds@gmail.com",
                [details['email']]),
            kwargs={'fail_silently': False}
        )
        email_thread.start()

        strategy.redirect(f"/auth/multi-factor-auth?partial_token=token_here")
    else:
        print('User is already authenticated')

