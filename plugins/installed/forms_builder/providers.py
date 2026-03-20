from django.template.loader import render_to_string


class FormsMenuProvider:
    label = 'Formulare'
    icon = 'bi-ui-checks'
    url = '/core/apps/forms/'
    priority = 60


class FormsPageProvider:
    slug = 'forms'
    title = 'Formulare'

    def render(self, request):
        from forms_builder.models import Form

        if request.user.is_staff:
            # Staff sieht alle Formulare + kann neue erstellen
            forms = Form.objects.all().select_related('created_by')
        else:
            # Normale User sehen nur aktive Formulare
            forms = Form.objects.filter(is_active=True).select_related('created_by')

        return render_to_string(
            'forms_builder/overview.html',
            {'forms': forms, 'request': request},
        )
