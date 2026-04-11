from django import forms
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

from departments.models import Company, CompanyInvitation, Department


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'domain', 'allow_domain_signup', 'description', 'owner', 'admins', 'employee_limit', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'admins': forms.SelectMultiple(attrs={'size': 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'username')
        self.fields['admins'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'username')
        for name, field in self.fields.items():
            if name == 'admins':
                field.widget.attrs.setdefault('class', 'form-select')
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_employee_limit(self):
        value = self.cleaned_data['employee_limit']
        if value < 1:
            raise forms.ValidationError('Das Mitarbeiterlimit muss mindestens 1 sein.')
        return value

    def clean_domain(self):
        return (self.cleaned_data.get('domain') or '').strip().lower()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('allow_domain_signup') and not cleaned.get('domain'):
            self.add_error('domain', 'Fuer Domain-Registrierung muss eine Hauptdomain gesetzt sein.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit and instance.owner_id:
            instance.admins.add(instance.owner)
        return instance


class CompanyInvitationForm(forms.ModelForm):
    class Meta:
        model = CompanyInvitation
        fields = ['email', 'department', 'role', 'expires_at']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        self.company = company
        super().__init__(*args, **kwargs)
        self.fields['department'].required = False
        self.fields['expires_at'].initial = (timezone.localtime() + timedelta(days=14)).replace(second=0, microsecond=0)
        if company is not None:
            self.fields['department'].queryset = Department.objects.filter(company=company).order_by('name')
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_department(self):
        department = self.cleaned_data.get('department')
        if department and self.company and department.company_id != self.company.id:
            raise forms.ValidationError('Der Bereich gehoert nicht zu dieser Firma.')
        return department

    def clean_expires_at(self):
        expires_at = self.cleaned_data['expires_at']
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
        if expires_at <= timezone.now():
            raise forms.ValidationError('Die Einladung muss in der Zukunft ablaufen.')
        return expires_at
