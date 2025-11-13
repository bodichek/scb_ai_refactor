from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from intercom.models import Thread, Message
from accounts.permissions import is_coach
from coaching.models import Coach, UserCoachAssignment


class Command(BaseCommand):
    help = "Seed intercom demo data"

    def handle(self, *args, **kwargs):
        U = get_user_model()
        # pick a coach user
        coach_user = None
        for u in U.objects.all():
            if is_coach(u):
                coach_user = u
                break
        if not coach_user:
            coach = Coach.objects.first()
            if coach:
                coach_user = coach.user

        client = U.objects.exclude(id=getattr(coach_user, 'id', None)).first()

        if not (coach_user and client):
            self.stdout.write(self.style.WARNING("Need at least 1 coach and 1 client"))
            return

        # ensure assignment exists
        coach_obj = Coach.objects.filter(user=coach_user).first()
        if coach_obj:
            UserCoachAssignment.objects.get_or_create(coach=coach_obj, client=client)

        t = Thread.for_pair(client, coach_user)
        Message.objects.create(thread=t, sender=client, body="Dobrý den, mám dotaz…")
        Message.objects.create(thread=t, sender=coach_user, body="Dobrý den, jak vám mohu pomoct?")
        self.stdout.write(self.style.SUCCESS("Seed done"))

