from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Count

from accounts.permissions import is_coach, can_coach_access_client
from accounts.models import CompanyProfile
from coaching.models import Coach, UserCoachAssignment
from .models import Thread, Message, Notification

UserModel = settings.AUTH_USER_MODEL


def get_assigned_coach_for_client(user):
    """Vrátí kouče (auth.User) pro daného klienta.
    Používá existující UserCoachAssignment → Coach.user.
    """
    assignment = UserCoachAssignment.objects.filter(client=user).select_related("coach__user").first()
    if assignment and assignment.coach and assignment.coach.user:
        return assignment.coach.user
    # Fallback: CompanyProfile.assigned_coach
    profile = CompanyProfile.objects.filter(user=user).select_related("assigned_coach__user").first()
    if profile and profile.assigned_coach and profile.assigned_coach.user:
        return profile.assigned_coach.user
    return None


@login_required
def inbox(request):
    if not is_coach(request.user):
        raise Http404
    try:
        coach = Coach.objects.get(user=request.user)
    except Coach.DoesNotExist:
        raise Http404
    client_ids = UserCoachAssignment.objects.filter(coach=coach).values_list("client_id", flat=True)
    threads = Thread.objects.filter(coach=request.user, client_id__in=client_ids).annotate(count_messages=Count("messages"))
    return render(request, "intercom/inbox.html", {"threads": threads})


@login_required
def thread_view(request, client_id: int):
    # klient: otevře své vlákno s koučem
    # kouč: otevře vlákno s tímto klientem (pokud k němu patří)
    if is_coach(request.user):
        # ověř, že má kouč přístup k tomuto klientovi
        from django.contrib.auth.models import User
        client = get_object_or_404(User, id=client_id)
        if not can_coach_access_client(request.user, client):
            raise Http404
        thread = Thread.objects.filter(client_id=client_id, coach=request.user).first()
        if thread is None:
            # založ vlákno, pokud neexistuje a existuje přiřazení
            coach_user = request.user
            thread = Thread.for_pair(client=client, coach=coach_user)
    else:
        if request.user.id != client_id:
            raise Http404
        coach = get_assigned_coach_for_client(request.user)
        if coach is None:
            raise Http404
        thread = Thread.for_pair(client=request.user, coach=coach)

    # označ zprávy od protistrany jako přečtené
    Message.objects.filter(thread=thread).exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())

    messages_qs = thread.messages.select_related("sender").all()

    return render(request, "intercom/thread.html", {
        "thread": thread,
        "messages": messages_qs,
        "is_coach": is_coach(request.user),
    })


@login_required
@require_POST
def send_message(request, client_id: int):
    body = (request.POST.get("body") or "").strip()
    if not body:
        return JsonResponse({"ok": False, "error": "Empty message"}, status=400)

    if is_coach(request.user):
        from django.contrib.auth.models import User
        client = get_object_or_404(User, id=client_id)
        if not can_coach_access_client(request.user, client):
            raise Http404
        thread = Thread.objects.filter(client_id=client_id, coach=request.user).first()
        if thread is None:
            thread = Thread.for_pair(client=client, coach=request.user)
    else:
        if request.user.id != client_id:
            raise Http404
        coach = get_assigned_coach_for_client(request.user)
        if coach is None:
            raise Http404
        thread = Thread.for_pair(client=request.user, coach=coach)

    msg = Message.objects.create(thread=thread, sender=request.user, body=body)

    if request.headers.get("HX-Request"):
        return render(request, "intercom/_message_item.html", {"m": msg})

    return redirect("intercom:thread", client_id=client_id)


@login_required
def unread_count(request):
    cnt = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread": cnt})


@login_required
@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})
