import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from news.forms import NewsArticleForm
from news.models import Comment, NewsArticle, Reaction


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class PublishedArticlesMixin:
    def get_queryset(self):
        return NewsArticle.objects.filter(
            is_published=True,
        ).filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())
        ).select_related('author', 'category')


class NewsListView(LoginRequiredMixin, PublishedArticlesMixin, ListView):
    template_name = 'news/news_list.html'
    context_object_name = 'articles'
    paginate_by = 9

    def get_queryset(self):
        qs = super().get_queryset()
        category_slug = self.request.GET.get('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    def get_context_data(self, **kwargs):
        from news.models import NewsCategory
        context = super().get_context_data(**kwargs)
        context['categories'] = NewsCategory.objects.all()
        context['active_category'] = self.request.GET.get('category', '')
        return context


class NewsDetailView(LoginRequiredMixin, DetailView):
    template_name = 'news/news_detail.html'
    context_object_name = 'article'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        if self.request.user.is_staff:
            return NewsArticle.objects.select_related('author', 'category')
        return NewsArticle.objects.filter(
            is_published=True,
        ).filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())
        ).select_related('author', 'category')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.increment_view_count()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = self.object
        ct = ContentType.objects.get_for_model(NewsArticle)

        comments = Comment.objects.filter(
            content_type=ct,
            object_id=article.pk,
            parent__isnull=True,
            is_deleted=False,
        ).select_related('author').prefetch_related('replies__author')
        context['comments'] = comments

        reactions = Reaction.objects.filter(content_type=ct, object_id=article.pk)
        context['reaction_like_count'] = reactions.filter(reaction='like').count()
        context['reaction_heart_count'] = reactions.filter(reaction='heart').count()

        user_reaction = None
        if self.request.user.is_authenticated:
            try:
                user_reaction = Reaction.objects.get(
                    content_type=ct,
                    object_id=article.pk,
                    user=self.request.user,
                ).reaction
            except Reaction.DoesNotExist:
                pass
        context['user_reaction'] = user_reaction
        return context


class NewsCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    template_name = 'news/news_form.html'
    model = NewsArticle
    form_class = NewsArticleForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('news:news_detail', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_mode'] = 'create'
        return context


class NewsUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    template_name = 'news/news_form.html'
    model = NewsArticle
    form_class = NewsArticleForm
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        return reverse_lazy('news:news_detail', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_mode'] = 'edit'
        return context


class NewsDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = NewsArticle
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('news:news_list')
    template_name = 'news/news_confirm_delete.html'


class AddCommentView(LoginRequiredMixin, View):
    """AJAX POST: add a comment to any content type."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (ValueError, KeyError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        app_label = data.get('app_label')
        model_name = data.get('model')
        object_id = data.get('object_id')
        body = (data.get('body') or '').strip()
        parent_id = data.get('parent_id')

        if not all([app_label, model_name, object_id, body]):
            return JsonResponse({'error': 'Missing fields'}, status=400)

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid content type'}, status=400)

        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)

        comment = Comment.objects.create(
            content_type=ct,
            object_id=object_id,
            author=request.user,
            body=body,
            parent=parent,
        )

        return JsonResponse({
            'id': comment.pk,
            'author': request.user.get_full_name() or request.user.username,
            'body': comment.body,
            'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
            'parent_id': parent_id,
        })


class ToggleReactionView(LoginRequiredMixin, View):
    """AJAX POST: toggle reaction on any content type."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (ValueError, KeyError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        app_label = data.get('app_label')
        model_name = data.get('model')
        object_id = data.get('object_id')
        reaction_type = data.get('reaction')

        if reaction_type not in ('like', 'heart'):
            return JsonResponse({'error': 'Invalid reaction'}, status=400)

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid content type'}, status=400)

        existing = Reaction.objects.filter(
            content_type=ct,
            object_id=object_id,
            user=request.user,
        ).first()

        if existing:
            if existing.reaction == reaction_type:
                existing.delete()
                active = False
            else:
                existing.reaction = reaction_type
                existing.save()
                active = True
        else:
            Reaction.objects.create(
                content_type=ct,
                object_id=object_id,
                user=request.user,
                reaction=reaction_type,
            )
            active = True

        like_count = Reaction.objects.filter(content_type=ct, object_id=object_id, reaction='like').count()
        heart_count = Reaction.objects.filter(content_type=ct, object_id=object_id, reaction='heart').count()

        return JsonResponse({
            'active': active,
            'reaction': reaction_type,
            'like_count': like_count,
            'heart_count': heart_count,
        })
