import csv
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from forms_builder.models import Form, FormAnswer, FormField, FormSubmission


def _staff_required(request):
    return request.user.is_authenticated and request.user.is_staff


# ── Übersicht ──────────────────────────────────────────────────────────────

@login_required
def form_create(request):
    if not request.user.is_staff:
        raise Http404
    if request.method == 'POST':
        title = request.POST.get('title', '').strip() or 'Neues Formular'
        desc = request.POST.get('description', '')
        allow_anon = bool(request.POST.get('allow_anonymous'))
        form = Form.objects.create(title=title, description=desc,
                                   created_by=request.user, allow_anonymous=allow_anon)
        return redirect('forms_builder:form_build', form_id=form.pk)
    return render(request, 'forms_builder/form_create.html', {})


@login_required
def form_toggle(request, form_id):
    if not request.user.is_staff:
        raise Http404
    form = get_object_or_404(Form, pk=form_id)
    form.is_active = not form.is_active
    form.save(update_fields=['is_active'])
    return redirect('forms_builder:form_build', form_id=form.pk)


@login_required
def form_delete(request, form_id):
    if not request.user.is_staff:
        raise Http404
    form = get_object_or_404(Form, pk=form_id, created_by=request.user)
    form.delete()
    return redirect('/core/apps/forms/')


# ── Builder ────────────────────────────────────────────────────────────────

@login_required
def form_build(request, form_id):
    if not request.user.is_staff:
        raise Http404
    form = get_object_or_404(Form, pk=form_id)
    fields = form.fields.order_by('order')
    return render(request, 'forms_builder/builder.html', {
        'form': form,
        'fields': fields,
        'field_types': FormField.FIELD_TYPES,
        'field_icons': FormField.FIELD_ICONS,
    })


@login_required
@require_POST
def field_add(request, form_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    form = get_object_or_404(Form, pk=form_id)
    field_type = request.POST.get('field_type', FormField.TYPE_TEXT)
    label = request.POST.get('label', '').strip() or 'Neue Frage'
    order = form.fields.count()
    field = FormField.objects.create(form=form, label=label, field_type=field_type, order=order)
    return JsonResponse({
        'id': field.pk,
        'label': field.label,
        'field_type': field.field_type,
        'icon': field.icon,
        'required': field.required,
        'has_choices': field.has_choices,
        'choices': field.get_choices(),
    })


@login_required
@require_POST
def field_update(request, field_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    field = get_object_or_404(FormField, pk=field_id)
    field.label = request.POST.get('label', field.label).strip() or field.label
    field.placeholder = request.POST.get('placeholder', field.placeholder)
    field.required = request.POST.get('required') == '1'
    choices_raw = request.POST.get('choices', '')
    if field.has_choices and choices_raw:
        choices = [c.strip() for c in choices_raw.split('\n') if c.strip()]
        field.set_choices(choices)
    field.save()
    return JsonResponse({'ok': True, 'label': field.label})


@login_required
@require_POST
def field_delete(request, field_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    field = get_object_or_404(FormField, pk=field_id)
    field.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def field_reorder(request, form_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    data = json.loads(request.body)
    for item in data.get('order', []):
        FormField.objects.filter(pk=item['id'], form_id=form_id).update(order=item['order'])
    return JsonResponse({'ok': True})


# ── Ausfüllen ──────────────────────────────────────────────────────────────

@login_required
def form_fill(request, form_id):
    form = get_object_or_404(Form, pk=form_id, is_active=True)
    fields = form.fields.order_by('order')

    if request.method == 'POST':
        submission = FormSubmission.objects.create(
            form=form,
            submitted_by=request.user if request.user.is_authenticated else None,
        )
        for field in fields:
            raw = request.POST.getlist(f'field_{field.pk}')
            value = ', '.join(raw) if raw else ''
            FormAnswer.objects.create(
                submission=submission,
                field=field,
                field_label=field.label,
                value=value,
            )
        return render(request, 'forms_builder/thank_you.html', {'form': form})

    return render(request, 'forms_builder/fill.html', {'form': form, 'fields': fields})


# ── Ergebnisse ─────────────────────────────────────────────────────────────

@login_required
def form_results(request, form_id):
    if not request.user.is_staff:
        raise Http404
    form = get_object_or_404(Form, pk=form_id)
    fields = list(form.fields.order_by('order'))
    submissions = form.submissions.prefetch_related('answers', 'submitted_by').order_by('-submitted_at')

    # Antworten als Dict aufbereiten: {submission_id: {field_id: value}}
    rows = []
    for sub in submissions:
        answer_map = {a.field_id: a.value for a in sub.answers.all() if a.field_id}
        rows.append({
            'submission': sub,
            'values': [answer_map.get(f.pk, '') for f in fields],
        })

    return render(request, 'forms_builder/results.html', {
        'form': form,
        'fields': fields,
        'rows': rows,
    })


@login_required
def form_export_csv(request, form_id):
    if not request.user.is_staff:
        raise Http404
    form = get_object_or_404(Form, pk=form_id)
    fields = list(form.fields.order_by('order'))
    submissions = form.submissions.prefetch_related('answers', 'submitted_by').order_by('-submitted_at')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="form_{form_id}_ergebnisse.csv"'
    response.write('\ufeff')  # UTF-8 BOM für Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Eingereicht von', 'Datum'] + [f.label for f in fields])

    for sub in submissions:
        answer_map = {a.field_id: a.value for a in sub.answers.all() if a.field_id}
        who = sub.submitted_by.get_full_name() or sub.submitted_by.username if sub.submitted_by else 'Anonym'
        writer.writerow(
            [who, sub.submitted_at.strftime('%d.%m.%Y %H:%M')] +
            [answer_map.get(f.pk, '') for f in fields]
        )

    return response
