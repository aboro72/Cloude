from django import forms
from django.contrib.auth.models import User

from accounts.models import UserProfile
from departments.models import Company, CompanyInvitation


class RegisterForm(forms.ModelForm):
    company_mode = forms.ChoiceField(
        choices=[
            ('create', 'Neue Firma erstellen'),
            ('join', 'Bestehender Firma beitreten'),
        ],
        widget=forms.RadioSelect,
        initial='create',
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Firma waehlen',
    )
    invite_token = forms.CharField(required=False, max_length=64, widget=forms.HiddenInput())
    company_name = forms.CharField(required=False, max_length=150)
    company_domain = forms.CharField(required=False, max_length=255)
    company_allow_domain_signup = forms.BooleanField(required=False)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resolved_invitation = None
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('name')
        for name in ['username', 'email', 'first_name', 'last_name', 'password', 'company_name', 'company_domain', 'invite_token']:
            self.fields[name].widget.attrs.setdefault('class', 'form-control')
        self.fields['company'].widget.attrs.setdefault('class', 'form-select')
        self.fields['company_allow_domain_signup'].widget.attrs.setdefault('class', 'form-check-input')

    def clean_invite_token(self):
        return (self.cleaned_data.get('invite_token') or '').strip()

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Dieser Benutzername ist bereits vergeben.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Diese E-Mail-Adresse ist bereits registriert.')
        return email

    def clean_company_domain(self):
        return (self.cleaned_data.get('company_domain') or '').strip().lower()

    def _resolve_invitation(self, token):
        if not token:
            return None
        try:
            invitation = CompanyInvitation.objects.select_related('company', 'department').get(token=token)
        except CompanyInvitation.DoesNotExist:
            raise forms.ValidationError('Der Einladungslink ist ungueltig.')
        if not invitation.is_usable:
            raise forms.ValidationError('Diese Einladung ist nicht mehr gueltig.')
        return invitation

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('company_mode')
        company = cleaned.get('company')
        invite_token = cleaned.get('invite_token')
        company_name = (cleaned.get('company_name') or '').strip()
        email = (cleaned.get('email') or '').strip().lower()

        if mode == 'join':
            invitation = None
            if invite_token:
                try:
                    invitation = self._resolve_invitation(invite_token)
                except forms.ValidationError as exc:
                    self.add_error('invite_token', exc)
                else:
                    if email and not invitation.matches_email(email):
                        self.add_error('email', 'Diese E-Mail-Adresse passt nicht zur Einladung.')
                    elif not invitation.company.can_add_employee():
                        self.add_error('invite_token', f'Die Firma "{invitation.company.name}" hat bereits {invitation.company.employee_limit} Mitarbeiter.')
                    else:
                        cleaned['company'] = invitation.company
                        self.resolved_invitation = invitation

            if not self.errors and not invitation:
                if not company:
                    self.add_error('company', 'Bitte waehlen Sie eine bestehende Firma.')
                elif not company.can_add_employee():
                    self.add_error('company', f'Die Firma "{company.name}" hat bereits {company.employee_limit} Mitarbeiter.')
                elif not company.allow_domain_signup:
                    self.add_error('company', 'Der Firmenbeitritt ist nur per Einladung erlaubt.')
                elif not company.email_matches_domain(email):
                    self.add_error('email', 'Ihre E-Mail-Domain passt nicht zur Firmen-Domain.')
        else:
            if not company_name:
                self.add_error('company_name', 'Bitte geben Sie einen Firmennamen an.')
            elif Company.objects.filter(name__iexact=company_name).exists():
                self.add_error('company_name', 'Es existiert bereits eine Firma mit diesem Namen.')
            if cleaned.get('company_allow_domain_signup') and not cleaned.get('company_domain'):
                self.add_error('company_domain', 'Fuer Domain-Registrierung muss eine Firmen-Domain gesetzt sein.')

        return cleaned


class ProfileEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault('class', 'form-control')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'avatar', 'bio', 'website', 'language', 'timezone', 'theme',
                  'job_title', 'location', 'manager']


class AppearanceSettingsForm(forms.ModelForm):
    mysite_hero_style = forms.ChoiceField(
        required=False,
        choices=UserProfile.MYSITE_HERO_STYLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_mysite_hero_style'}),
    )
    primary_color = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
    )
    secondary_color = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
    )
    mysite_hero_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )
    mysite_hero_video = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = UserProfile
        fields = [
            'theme',
            'design_variant',
            'color_preset',
            'primary_color',
            'secondary_color',
            'mysite_hero_style',
            'mysite_hero_image',
            'mysite_hero_video',
        ]
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'design_variant': forms.Select(attrs={'class': 'form-select'}),
            'color_preset': forms.Select(attrs={'class': 'form-select', 'id': 'id_color_preset'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get('color_preset')
        hero_style = cleaned_data.get('mysite_hero_style') or getattr(self.instance, 'mysite_hero_style', 'gradient')
        cleaned_data['mysite_hero_style'] = hero_style
        if preset and preset != 'custom':
            preset_colors = UserProfile.get_color_preset_map().get(preset)
            if preset_colors:
                cleaned_data['primary_color'] = preset_colors['primary']
                cleaned_data['secondary_color'] = preset_colors['secondary']
        elif preset == 'custom':
            if not cleaned_data.get('primary_color'):
                self.add_error('primary_color', 'Bitte waehlen Sie eine Primaerfarbe.')
            if not cleaned_data.get('secondary_color'):
                self.add_error('secondary_color', 'Bitte waehlen Sie eine Sekundarfarbe.')

        if hero_style == 'image' and not (cleaned_data.get('mysite_hero_image') or getattr(self.instance, 'mysite_hero_image', None)):
            self.add_error('mysite_hero_image', 'Bitte laden Sie ein Hintergrundbild fuer MySite hoch.')
        if hero_style == 'video' and not (cleaned_data.get('mysite_hero_video') or getattr(self.instance, 'mysite_hero_video', None)):
            self.add_error('mysite_hero_video', 'Bitte laden Sie ein Hintergrundvideo fuer MySite hoch.')
        return cleaned_data
