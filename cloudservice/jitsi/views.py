import time
import uuid
import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Company
from .models import Meeting


JITSI_URL = getattr(settings, 'JITSI_URL', 'https://meet.aborosoft.com')
TOKEN_TTL = 3600


def _build_token(user, room):
    now = int(time.time())
    payload = {
        "context": {
            "user": {
                "id": str(user.pk),
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "affiliation": "owner" if user.is_staff else "member",
            }
        },
        "aud": "jitsi",
        "iss": settings.JITSI_APP_ID,
        "sub": "meet.aborosoft.com",
        "room": room or "*",
        "exp": now + TOKEN_TTL,
        "nbf": now - 5,
    }
    return jwt.encode(payload, settings.JITSI_APP_SECRET, algorithm="HS256")


def _get_company(request):
    profile = getattr(request.user, 'profile', None)
    if profile and profile.company:
        return profile.company
    if request.user.is_superuser:
        return Company.objects.first()
    return None


@login_required
def meetings(request):
    company = _get_company(request)
    if not company:
        return render(request, 'jitsi/meetings.html', {'no_company': True})

    base_qs = Meeting.objects.filter(company=company).filter(
        Q(organizer=request.user) | Q(invitees=request.user)
    ).distinct().prefetch_related('invitees').select_related('organizer')

    running = list(base_qs.filter(status=Meeting.STATUS_RUNNING).order_by('-started_at'))
    planned = list(base_qs.filter(status=Meeting.STATUS_PLANNED).order_by('scheduled_start', 'created_at'))
    past = list(
        base_qs.filter(status__in=[Meeting.STATUS_ENDED, Meeting.STATUS_CANCELLED])
        .order_by('-ended_at', '-started_at', '-created_at')[:30]
    )

    company_users = (
        User.objects.filter(is_active=True, profile__company=company)
        .exclude(pk=request.user.pk)
        .select_related('profile')
        .order_by('first_name', 'last_name', 'username')
    )

    return render(request, 'jitsi/meetings.html', {
        'company': company,
        'running': running,
        'planned': planned,
        'past': past,
        'company_users': company_users,
        'now': timezone.now(),
    })


@login_required
@require_POST
def schedule(request):
    company = _get_company(request)
    if not company:
        messages.error(request, 'Kein Firmen-Workspace gefunden.')
        return redirect('jitsi:meetings')

    title = request.POST.get('title', '').strip()
    if not title:
        messages.error(request, 'Titel ist erforderlich.')
        return redirect('jitsi:meetings')

    description = request.POST.get('description', '').strip()

    scheduled_start = None
    scheduled_end = None
    raw_start = request.POST.get('scheduled_start', '').strip()
    raw_end = request.POST.get('scheduled_end', '').strip()
    if raw_start:
        try:
            from django.utils.dateparse import parse_datetime
            scheduled_start = timezone.make_aware(
                parse_datetime(raw_start),
                timezone.get_current_timezone()
            )
        except Exception:
            pass
    if raw_end:
        try:
            from django.utils.dateparse import parse_datetime
            scheduled_end = timezone.make_aware(
                parse_datetime(raw_end),
                timezone.get_current_timezone()
            )
        except Exception:
            pass

    meeting = Meeting.objects.create(
        company=company,
        title=title,
        description=description,
        organizer=request.user,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=Meeting.STATUS_PLANNED,
    )

    invitee_ids = request.POST.getlist('invitees')
    if invitee_ids:
        valid_invitees = User.objects.filter(
            pk__in=invitee_ids,
            is_active=True,
            profile__company=company,
        )
        meeting.invitees.set(valid_invitees)

    messages.success(request, f'Meeting „{title}" wurde geplant.')
    return redirect('jitsi:meetings')


def _mysite_url():
    try:
        from django.urls import reverse
        return reverse('core:plugin_app', kwargs={'slug': 'mysite'})
    except Exception:
        return '/'


@login_required
def start_meeting(request, pk):
    company = _get_company(request)
    meeting = get_object_or_404(Meeting, pk=pk, company=company)

    if not meeting.can_be_started_by(request.user):
        messages.error(request, 'Du kannst dieses Meeting nicht starten.')
        return redirect('jitsi:meetings')

    meeting.start()
    return redirect('jitsi:meeting_room', pk=meeting.pk)


@login_required
def join_meeting(request, pk):
    company = _get_company(request)
    meeting = get_object_or_404(Meeting, pk=pk, company=company)

    if meeting.status != Meeting.STATUS_RUNNING:
        messages.warning(request, 'Dieses Meeting läuft gerade nicht.')
        return redirect('jitsi:meetings')

    is_participant = (
        meeting.organizer == request.user
        or meeting.invitees.filter(pk=request.user.pk).exists()
        or request.user.is_superuser
    )
    if not is_participant:
        messages.error(request, 'Du bist nicht für dieses Meeting eingeladen.')
        return redirect('jitsi:meetings')

    return redirect('jitsi:meeting_room', pk=meeting.pk)


@login_required
def meeting_room(request, pk):
    company = _get_company(request)
    meeting = get_object_or_404(Meeting, pk=pk, company=company)

    if meeting.status != Meeting.STATUS_RUNNING:
        messages.warning(request, 'Dieses Meeting läuft gerade nicht.')
        return redirect('jitsi:meetings')

    is_participant = (
        meeting.organizer == request.user
        or meeting.invitees.filter(pk=request.user.pk).exists()
        or request.user.is_superuser
    )
    if not is_participant:
        messages.error(request, 'Du bist nicht für dieses Meeting eingeladen.')
        return redirect('jitsi:meetings')

    token = _build_token(request.user, meeting.room_name)
    return render(request, 'jitsi/meeting_room.html', {
        'meeting': meeting,
        'jitsi_domain': JITSI_URL.replace('https://', '').replace('http://', '').rstrip('/'),
        'jitsi_token': token,
        'return_url': _mysite_url(),
        'display_name': request.user.get_full_name() or request.user.username,
    })


@login_required
@require_POST
def end_meeting(request, pk):
    company = _get_company(request)
    meeting = get_object_or_404(Meeting, pk=pk, company=company)

    if not meeting.can_be_ended_by(request.user):
        messages.error(request, 'Du kannst dieses Meeting nicht beenden.')
    else:
        meeting.end()
        messages.success(request, f'Meeting „{meeting.title}" wurde beendet.')

    return redirect('jitsi:meetings')


@login_required
@require_POST
def cancel_meeting(request, pk):
    company = _get_company(request)
    meeting = get_object_or_404(Meeting, pk=pk, company=company)

    if not meeting.can_be_cancelled_by(request.user):
        messages.error(request, 'Du kannst dieses Meeting nicht absagen.')
    else:
        meeting.cancel()
        messages.success(request, f'Meeting „{meeting.title}" wurde abgesagt.')

    return redirect('jitsi:meetings')


@login_required
def join(request, room=None):
    if not room:
        room = request.GET.get('room', '').strip() or str(uuid.uuid4())[:8]
    room = ''.join(c for c in room if c.isalnum() or c in '-_')[:64] or str(uuid.uuid4())[:8]
    token = _build_token(request.user, room)
    return redirect(f"{JITSI_URL}/{room}?jwt={token}")


@login_required
def token_api(request):
    room = request.GET.get('room', '*')
    token = _build_token(request.user, room)
    return JsonResponse({'token': token, 'url': f"{JITSI_URL}/{room}?jwt={token}"})
