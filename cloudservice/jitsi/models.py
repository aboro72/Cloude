import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import Company


class Meeting(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_RUNNING = 'running'
    STATUS_ENDED = 'ended'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Geplant'),
        (STATUS_RUNNING, 'Läuft'),
        (STATUS_ENDED, 'Beendet'),
        (STATUS_CANCELLED, 'Abgesagt'),
    ]

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='meetings'
    )
    title = models.CharField(max_length=200, verbose_name='Titel')
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    organizer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='organized_meetings',
        verbose_name='Organisator'
    )
    invitees = models.ManyToManyField(
        User, blank=True, related_name='invited_meetings', verbose_name='Eingeladene'
    )

    scheduled_start = models.DateTimeField(
        null=True, blank=True, verbose_name='Geplanter Start'
    )
    scheduled_end = models.DateTimeField(
        null=True, blank=True, verbose_name='Geplantes Ende'
    )

    # Room name is only set when the meeting actually starts
    room_name = models.SlugField(max_length=80, blank=True, verbose_name='Raumname')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED,
        verbose_name='Status', db_index=True
    )

    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Gestartet am')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='Beendet am')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Meeting'
        verbose_name_plural = 'Meetings'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def is_running(self):
        return self.status == self.STATUS_RUNNING

    def can_be_started_by(self, user):
        return self.status == self.STATUS_PLANNED and (
            self.organizer == user or user.is_superuser
        )

    def can_be_ended_by(self, user):
        return self.status == self.STATUS_RUNNING and (
            self.organizer == user or user.is_superuser
        )

    def can_be_cancelled_by(self, user):
        return self.status == self.STATUS_PLANNED and (
            self.organizer == user or user.is_superuser
        )

    def start(self):
        if not self.room_name:
            base = slugify(self.title)[:40] or 'meeting'
            self.room_name = f"{base}-{uuid.uuid4().hex[:6]}"
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['room_name', 'status', 'started_at', 'updated_at'])

    def end(self):
        self.status = self.STATUS_ENDED
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'ended_at', 'updated_at'])

    def cancel(self):
        self.status = self.STATUS_CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    @property
    def duration_display(self):
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            minutes = int(delta.total_seconds() // 60)
            if minutes < 60:
                return f"{minutes} Min."
            return f"{minutes // 60}h {minutes % 60}min"
        return None
