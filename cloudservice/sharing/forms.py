from django import forms

from sharing.models import TeamSiteNews


class TeamSiteNewsForm(forms.ModelForm):
    class Meta:
        model = TeamSiteNews
        fields = [
            'title',
            'category',
            'summary',
            'content',
            'cover_image',
            'is_pinned',
            'is_published',
            'publish_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. Projekt, HR, Release'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 12, 'id': 'id_content_editor'}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'publish_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.publish_at:
            self.initial['publish_at'] = self.instance.publish_at.strftime('%Y-%m-%dT%H:%M')

