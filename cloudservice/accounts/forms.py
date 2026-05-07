from django import forms
from django.contrib.auth.models import User
from django.utils.text import slugify

from accounts.models import Company, UserProfile


class RegisterForm(forms.ModelForm):
    company_name = forms.CharField(
        max_length=180,
        label='Firma',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Firmenname'}),
    )
    workspace_type = forms.ChoiceField(
        label='Workspace-Typ',
        choices=Company.WORKSPACE_TYPE_CHOICES,
        initial='directory',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    workspace_key = forms.CharField(
        max_length=63,
        label='Verzeichnis / Subdomain',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. acme'}),
        help_text='Wird als eigenes Firmen-Verzeichnis oder als Subdomain-Kennung verwendet.',
    )
    password = forms.CharField(
        label='Passwort',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Passwort'}),
        help_text='Mindestens 8 Zeichen.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def clean_company_name(self):
        company_name = self.cleaned_data['company_name'].strip()
        if not company_name:
            raise forms.ValidationError('Bitte geben Sie einen Firmennamen an.')
        if Company.objects.filter(name__iexact=company_name).exists():
            raise forms.ValidationError('Diese Firma ist bereits registriert.')
        return company_name

    def clean_workspace_key(self):
        workspace_key = slugify(self.cleaned_data['workspace_key']).replace('_', '-')
        if not workspace_key:
            raise forms.ValidationError('Bitte geben Sie eine gueltige Workspace-Kennung an.')
        if Company.objects.filter(workspace_key=workspace_key).exists():
            raise forms.ValidationError('Diese Workspace-Kennung ist bereits vergeben.')
        return workspace_key

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) < 8:
            raise forms.ValidationError('Das Passwort muss mindestens 8 Zeichen lang sein.')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile = user.profile
            profile.company = Company.objects.create(
                name=self.cleaned_data['company_name'],
                workspace_type=self.cleaned_data['workspace_type'],
                workspace_key=self.cleaned_data['workspace_key'],
            )
            profile.save(update_fields=['company'])
        return user


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
