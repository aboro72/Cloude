import json
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Form(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Titel'))
    description = models.TextField(blank=True, verbose_name=_('Beschreibung'))
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='created_forms', verbose_name=_('Erstellt von')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Aktiv'))
    allow_anonymous = models.BooleanField(default=False, verbose_name=_('Anonyme Einreichungen erlaubt'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Form')
        verbose_name_plural = _('Forms')

    def __str__(self):
        return self.title

    def submission_count(self):
        return self.submissions.count()


class FormField(models.Model):
    TYPE_TEXT = 'text'
    TYPE_TEXTAREA = 'textarea'
    TYPE_SELECT = 'select'
    TYPE_RADIO = 'radio'
    TYPE_CHECKBOX = 'checkbox'
    TYPE_DATE = 'date'
    TYPE_SCALE = 'scale'

    FIELD_TYPES = [
        (TYPE_TEXT,     _('Kurztext')),
        (TYPE_TEXTAREA, _('Langtext')),
        (TYPE_SELECT,   _('Dropdown')),
        (TYPE_RADIO,    _('Einfachauswahl')),
        (TYPE_CHECKBOX, _('Mehrfachauswahl')),
        (TYPE_DATE,     _('Datum')),
        (TYPE_SCALE,    _('Skala (1–5)')),
    ]

    FIELD_ICONS = {
        TYPE_TEXT:     'bi-input-cursor-text',
        TYPE_TEXTAREA: 'bi-card-text',
        TYPE_SELECT:   'bi-menu-button-wide',
        TYPE_RADIO:    'bi-record-circle',
        TYPE_CHECKBOX: 'bi-check2-square',
        TYPE_DATE:     'bi-calendar',
        TYPE_SCALE:    'bi-sliders',
    }

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=255, verbose_name=_('Beschriftung'))
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name=_('Typ'))
    # Für Select/Radio/Checkbox: JSON-Liste von Optionen
    choices_json = models.TextField(blank=True, default='[]', verbose_name=_('Optionen (JSON)'))
    placeholder = models.CharField(max_length=255, blank=True, verbose_name=_('Platzhalter'))
    required = models.BooleanField(default=False, verbose_name=_('Pflichtfeld'))
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Form Field')

    def __str__(self):
        return f'{self.form.title} – {self.label}'

    def get_choices(self):
        try:
            return json.loads(self.choices_json)
        except (ValueError, TypeError):
            return []

    def set_choices(self, choices_list):
        self.choices_json = json.dumps(choices_list, ensure_ascii=False)

    @property
    def icon(self):
        return self.FIELD_ICONS.get(self.field_type, 'bi-question')

    @property
    def has_choices(self):
        return self.field_type in (self.TYPE_SELECT, self.TYPE_RADIO, self.TYPE_CHECKBOX)


class FormSubmission(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='form_submissions'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = _('Form Submission')

    def __str__(self):
        who = self.submitted_by.username if self.submitted_by else 'Anonym'
        return f'{self.form.title} – {who} – {self.submitted_at:%d.%m.%Y}'


class FormAnswer(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='answers')
    field = models.ForeignKey(FormField, on_delete=models.SET_NULL, null=True, related_name='answers')
    field_label = models.CharField(max_length=255)  # Snapshot des Labels zum Zeitpunkt der Einreichung
    value = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Form Answer')

    def __str__(self):
        return f'{self.field_label}: {self.value[:50]}'
