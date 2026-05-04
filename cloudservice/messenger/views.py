"""
Views for the Messenger app.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from accounts.models import Company
from messenger.models import ChatRoom, ChatMembership, ChatMessage, ChatInvite


def _get_company_or_403(request, workspace_key):
    company = get_object_or_404(Company, workspace_key=workspace_key)
    profile = getattr(request.user, 'profile', None)
    is_member = (
        request.user.is_superuser
        or (profile and profile.company == company)
        or ChatMembership.objects.filter(
            room__company=company, user=request.user
        ).exists()
    )
    if not is_member:
        return company, False
    return company, True


@login_required
def messenger_home(request, workspace_key):
    """Messenger overview: channels + DMs for this company workspace."""
    company = get_object_or_404(Company, workspace_key=workspace_key)

    # All rooms this user is a member of that belong to this company
    memberships = (
        ChatMembership.objects
        .filter(user=request.user, room__company=company, room__is_archived=False)
        .select_related('room')
        .order_by('-room__updated_at')
    )

    channels = []
    directs = []
    for m in memberships:
        if m.room.room_type in ('channel', 'group'):
            channels.append((m.room, m))
        else:
            directs.append((m.room, m))

    # Public channels user hasn't joined yet
    joined_ids = [m.room_id for m in memberships]
    open_channels = (
        ChatRoom.objects
        .filter(company=company, room_type='channel', is_private=False, is_archived=False)
        .exclude(pk__in=joined_ids)
    )

    return render(request, 'messenger/messenger.html', {
        'company': company,
        'channels': channels,
        'directs': directs,
        'open_channels': open_channels,
        'active_room': None,
        'messages_list': [],
    })


@login_required
def room_view(request, workspace_key, room_slug):
    """Main chat view for a specific room."""
    company = get_object_or_404(Company, workspace_key=workspace_key)
    room = get_object_or_404(ChatRoom, company=company, slug=room_slug)

    # Must be a member
    membership = ChatMembership.objects.filter(room=room, user=request.user).first()
    if not membership:
        # Auto-join public channels
        if room.room_type == 'channel' and not room.is_private:
            membership = ChatMembership.objects.create(
                room=room, user=request.user, role='member'
            )
        else:
            messages.error(request, 'Kein Zugriff auf diesen Kanal.')
            return redirect('messenger:home', workspace_key=workspace_key)

    # Mark as read
    membership.mark_read()

    # Load last 60 messages
    msgs = (
        ChatMessage.objects
        .filter(room=room)
        .select_related('author', 'reply_to', 'reply_to__author', 'storage_file')
        .order_by('-created_at')[:60]
    )
    msgs = list(reversed(msgs))

    # Sidebar data
    memberships_sidebar = (
        ChatMembership.objects
        .filter(user=request.user, room__company=company, room__is_archived=False)
        .select_related('room')
        .order_by('-room__updated_at')
    )
    channels = []
    directs = []
    for m in memberships_sidebar:
        if m.room.room_type in ('channel', 'group'):
            channels.append((m.room, m))
        else:
            directs.append((m.room, m))

    open_channels = (
        ChatRoom.objects
        .filter(company=company, room_type='channel', is_private=False, is_archived=False)
        .exclude(pk__in=[m.room_id for m in memberships_sidebar])
    )

    room_members = room.memberships.select_related('user').all()

    return render(request, 'messenger/messenger.html', {
        'company': company,
        'channels': channels,
        'directs': directs,
        'open_channels': open_channels,
        'active_room': room,
        'messages_list': msgs,
        'membership': membership,
        'room_members': room_members,
    })


@login_required
def create_channel(request, workspace_key):
    """Create a new channel in this company workspace."""
    company = get_object_or_404(Company, workspace_key=workspace_key)
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_superuser and not (profile and profile.company == company):
        messages.error(request, 'Kein Zugriff.')
        return redirect('messenger:home', workspace_key=workspace_key)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_private = request.POST.get('is_private') == 'on'

        if not name:
            messages.error(request, 'Name ist erforderlich.')
        else:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while ChatRoom.objects.filter(company=company, slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            room = ChatRoom.objects.create(
                company=company,
                name=name,
                slug=slug,
                description=description,
                is_private=is_private,
                room_type='channel',
                created_by=request.user,
            )
            ChatMembership.objects.create(room=room, user=request.user, role='owner')

            # System message
            ChatMessage.objects.create(
                room=room,
                author=None,
                message_type='system',
                content=f'Kanal #{name} wurde von {request.user.get_full_name() or request.user.username} erstellt.',
            )
            return redirect('messenger:room', workspace_key=workspace_key, room_slug=room.slug)

    return render(request, 'messenger/create_channel.html', {'company': company})


@login_required
def direct_message(request, workspace_key, username):
    """Open or create a direct-message thread with another user."""
    company = get_object_or_404(Company, workspace_key=workspace_key)
    other = get_object_or_404(User, username=username)

    if other == request.user:
        return redirect('messenger:home', workspace_key=workspace_key)

    # Find existing DM room between these two users in this company
    existing = (
        ChatRoom.objects
        .filter(company=company, room_type='direct')
        .filter(memberships__user=request.user)
        .filter(memberships__user=other)
        .first()
    )
    if existing:
        return redirect('messenger:room', workspace_key=workspace_key, room_slug=existing.slug)

    # Create new DM room
    slug = f'dm-{min(request.user.pk, other.pk)}-{max(request.user.pk, other.pk)}'
    room = ChatRoom.objects.create(
        company=company,
        name=f'{request.user.username} & {other.username}',
        slug=slug,
        room_type='direct',
        is_private=True,
        created_by=request.user,
    )
    ChatMembership.objects.create(room=room, user=request.user, role='owner')
    ChatMembership.objects.create(room=room, user=other, role='member')

    return redirect('messenger:room', workspace_key=workspace_key, room_slug=room.slug)


@login_required
def invite_create(request, workspace_key, room_slug):
    """Generate an invite link for a room."""
    company = get_object_or_404(Company, workspace_key=workspace_key)
    room = get_object_or_404(ChatRoom, company=company, slug=room_slug)

    membership = ChatMembership.objects.filter(room=room, user=request.user).first()
    if not membership or membership.role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Kein Zugriff.'}, status=403)

    if request.method == 'POST':
        from datetime import timedelta
        data = json.loads(request.body or '{}')
        max_uses = int(data.get('max_uses', 1))
        days = int(data.get('days', 7))
        email = data.get('email', '').strip()

        invite = ChatInvite.objects.create(
            room=room,
            invited_by=request.user,
            invited_email=email,
            max_uses=max_uses,
            expires_at=timezone.now() + timedelta(days=days) if days > 0 else None,
        )
        invite_url = request.build_absolute_uri(
            f'/messenger/invite/{invite.token}/'
        )
        return JsonResponse({'invite_url': invite_url, 'token': str(invite.token)})

    return JsonResponse({'error': 'POST required.'}, status=405)


@login_required
def invite_accept(request, token):
    """Accept a chat invite — works cross-company."""
    invite = get_object_or_404(ChatInvite, token=token)

    if not invite.is_valid():
        messages.error(request, 'Diese Einladung ist abgelaufen oder nicht mehr gültig.')
        return redirect('home')

    room = invite.room
    company = room.company

    membership, created = ChatMembership.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={'role': 'member'},
    )
    if created:
        invite.use_count += 1
        invite.save(update_fields=['use_count'])
        # Add guest company link if from different company
        profile = getattr(request.user, 'profile', None)
        if profile and profile.company and profile.company != company:
            room.guest_companies.add(profile.company)
        ChatMessage.objects.create(
            room=room,
            author=None,
            message_type='system',
            content=f'{request.user.get_full_name() or request.user.username} ist dem Kanal beigetreten.',
        )

    return redirect('messenger:room', workspace_key=company.workspace_key, room_slug=room.slug)


# ── AJAX endpoints ─────────────────────────────────────────────────────────

@login_required
def messages_load(request, room_id):
    """Load older messages (pagination via ?before=<message_id>)."""
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not ChatMembership.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'Forbidden'}, status=403)

    before_id = request.GET.get('before')
    qs = ChatMessage.objects.filter(room=room).select_related('author', 'reply_to__author')
    if before_id:
        qs = qs.filter(pk__lt=before_id)
    qs = qs.order_by('-created_at')[:30]

    data = []
    for msg in reversed(list(qs)):
        data.append({
            'id': msg.pk,
            'author': msg.author.get_full_name() or msg.author.username if msg.author else 'System',
            'author_id': msg.author_id,
            'content': msg.content,
            'message_type': msg.message_type,
            'is_deleted': msg.is_deleted,
            'created_at': msg.created_at.isoformat(),
            'reactions': msg.reactions,
            'reply_to_id': msg.reply_to_id,
            'reply_preview': msg.reply_to.content[:60] if msg.reply_to else None,
        })
    return JsonResponse({'messages': data})


@login_required
@require_POST
def room_join(request, workspace_key, room_slug):
    """Join a public channel."""
    company = get_object_or_404(Company, workspace_key=workspace_key)
    room = get_object_or_404(ChatRoom, company=company, slug=room_slug)

    if room.is_private:
        return JsonResponse({'error': 'Private channel.'}, status=403)

    ChatMembership.objects.get_or_create(room=room, user=request.user, defaults={'role': 'member'})
    return redirect('messenger:room', workspace_key=workspace_key, room_slug=room_slug)
