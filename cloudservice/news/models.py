from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
import re


class NewsCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    slug = models.SlugField(unique=True, verbose_name=_('Slug'))
    color = models.CharField(max_length=7, default='#667eea', verbose_name=_('Color'))
    icon = models.CharField(max_length=50, default='bi-tag', verbose_name=_('Icon'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Order'))

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('News Category')
        verbose_name_plural = _('News Categories')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class NewsArticle(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('Title'))
    slug = models.SlugField(unique=True, max_length=191, verbose_name=_('Slug'))
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
        verbose_name=_('Category'),
    )
    tags = models.CharField(max_length=255, blank=True, verbose_name=_('Tags'))
    summary = models.TextField(blank=True, verbose_name=_('Summary'))
    content = models.TextField(blank=True, verbose_name=_('Content'))
    cover_image = models.ImageField(
        upload_to='news/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_('Cover image'),
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='news_articles_authored',
        verbose_name=_('Author'),
    )
    is_published = models.BooleanField(default=False, verbose_name=_('Is published'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Is featured'))
    is_pinned = models.BooleanField(default=False, verbose_name=_('Is pinned'))
    publish_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Publish at'))
    view_count = models.PositiveIntegerField(default=0, verbose_name=_('View count'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    comments = GenericRelation('news.Comment', content_type_field='content_type', object_id_field='object_id')
    reactions = GenericRelation('news.Reaction', content_type_field='content_type', object_id_field='object_id')

    class Meta:
        ordering = ['-is_pinned', '-publish_at', '-created_at']
        verbose_name = _('News Article')
        verbose_name_plural = _('News Articles')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            max_length = self._meta.get_field('slug').max_length
            base = slugify(self.title)[:max_length]
            slug = base
            n = 1
            while NewsArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix = f'-{n}'
                slug = f'{base[:max_length - len(suffix)]}{suffix}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_tags_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def increment_view_count(self):
        NewsArticle.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)
        self.refresh_from_db(fields=['view_count'])


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_('Content type'))
    object_id = models.PositiveIntegerField(verbose_name=_('Object ID'))
    content_object = GenericForeignKey('content_type', 'object_id')

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='news_comments',
        verbose_name=_('Author'),
    )
    body = models.TextField(verbose_name=_('Body'))
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Parent'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    is_deleted = models.BooleanField(default=False, verbose_name=_('Is deleted'))

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return f'Comment by {self.author.username} on {self.content_type} #{self.object_id}'


class Reaction(models.Model):
    REACTION_CHOICES = [
        ('like', '👍 Like'),
        ('heart', '❤️ Heart'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_('Content type'))
    object_id = models.PositiveIntegerField(verbose_name=_('Object ID'))
    content_object = GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='news_reactions',
        verbose_name=_('User'),
    )
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES, verbose_name=_('Reaction'))

    class Meta:
        unique_together = [('content_type', 'object_id', 'user')]
        verbose_name = _('Reaction')
        verbose_name_plural = _('Reactions')

    def __str__(self):
        return f'{self.user.username}: {self.reaction}'
