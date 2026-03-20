from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class TaskBoard(models.Model):
    """Ein Board gehört entweder einer Person oder einer Team-Site."""
    title = models.CharField(max_length=120, verbose_name=_('Titel'))
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='task_boards', verbose_name=_('Besitzer')
    )
    # Optional: Team-Site (GroupShare)
    team_site = models.ForeignKey(
        'sharing.GroupShare',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='task_boards',
        verbose_name=_('Team-Site'),
    )
    color = models.CharField(max_length=7, default='#667eea', verbose_name=_('Farbe'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = _('Task Board')
        verbose_name_plural = _('Task Boards')

    def __str__(self):
        return self.title

    @property
    def is_team_board(self):
        return self.team_site_id is not None


class Task(models.Model):
    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_BLOCKED = 'blocked'

    STATUS_CHOICES = [
        (STATUS_TODO, _('Offen')),
        (STATUS_IN_PROGRESS, _('In Bearbeitung')),
        (STATUS_BLOCKED, _('Blockiert')),
        (STATUS_DONE, _('Erledigt')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('Niedrig')),
        ('normal', _('Normal')),
        ('high', _('Hoch')),
    ]

    board = models.ForeignKey(
        TaskBoard, on_delete=models.CASCADE,
        related_name='tasks', verbose_name=_('Board')
    )
    title = models.CharField(max_length=255, verbose_name=_('Titel'))
    description = models.TextField(blank=True, verbose_name=_('Beschreibung'))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_TODO, db_index=True, verbose_name=_('Status')
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES,
        default='normal', verbose_name=_('Priorität')
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_tasks',
        verbose_name=_('Zugewiesen an')
    )
    due_date = models.DateField(null=True, blank=True, verbose_name=_('Fällig am'))
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_('Reihenfolge'))
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_tasks', verbose_name=_('Erstellt von')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')

    def __str__(self):
        return self.title
