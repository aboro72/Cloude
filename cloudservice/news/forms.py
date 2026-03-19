from django import forms

from news.models import NewsArticle


class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = [
            'title',
            'category',
            'tags',
            'summary',
            'content',
            'cover_image',
            'is_published',
            'is_featured',
            'is_pinned',
            'publish_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'z.B. Projekt, Ankündigung, Release (kommagetrennt)',
            }),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 14,
                'id': 'id_news_content_editor',
            }),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'publish_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.publish_at:
            self.initial['publish_at'] = self.instance.publish_at.strftime('%Y-%m-%dT%H:%M')
