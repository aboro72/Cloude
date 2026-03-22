from django.contrib.auth.models import User
from django.db.models import Q
from django.template.loader import render_to_string


class PeopleMenuProvider:
    label = 'Personen'
    icon = 'bi-people-fill'
    url = '/core/apps/people/'
    priority = 40


class PeoplePageProvider:
    slug = 'people'
    title = 'Mitarbeiterverzeichnis'

    def render(self, request):
        q = request.GET.get('q', '').strip()
        dept = request.GET.get('dept', '').strip()

        qs = User.objects.filter(is_active=True).select_related('profile').order_by(
            'first_name', 'last_name', 'username'
        )

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(profile__job_title__icontains=q) |
                Q(profile__department__icontains=q)
            )

        if dept:
            qs = qs.filter(profile__department__iexact=dept)

        # Alle Abteilungen für Filter-Dropdown
        departments = (
            User.objects.filter(is_active=True, profile__department__gt='')
            .values_list('profile__department', flat=True)
            .distinct()
            .order_by('profile__department')
        )

        return render_to_string(
            'people_directory/directory.html',
            {
                'people': qs,
                'query': q,
                'dept': dept,
                'departments': departments,
                'request': request,
            },
        )
