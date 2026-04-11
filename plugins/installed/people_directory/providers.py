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
        company = getattr(getattr(request.user, 'profile', None), 'company', None)

        qs = User.objects.filter(is_active=True).select_related('profile').order_by(
            'first_name', 'last_name', 'username'
        )
        if company:
            qs = qs.filter(profile__company=company)

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(profile__job_title__icontains=q) |
                Q(profile__department_ref__name__icontains=q) |
                Q(profile__department__icontains=q) |
                Q(profile__company__name__icontains=q)
            )

        if dept:
            qs = qs.filter(
                Q(profile__department_ref__name__iexact=dept) |
                Q(profile__department__iexact=dept)
            )

        departments = (
            qs.exclude(profile__department_ref__name__isnull=True)
            .exclude(profile__department_ref__name__exact='')
            .values_list('profile__department_ref__name', flat=True)
            .distinct()
            .order_by('profile__department_ref__name')
        )

        return render_to_string(
            'people_directory/directory.html',
            {
                'people': qs,
                'query': q,
                'dept': dept,
                'departments': departments,
                'company': company,
                'company_can_manage': company.user_can_manage(request.user) if company else False,
                'company_invite_url': f'/departments/firmen/{company.slug}/verwaltung/#einladungen' if company and company.user_can_manage(request.user) else '',
                'request': request,
            },
        )
