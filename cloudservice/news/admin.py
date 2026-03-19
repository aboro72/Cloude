from django.contrib import admin

from news.models import Comment, NewsArticle, NewsCategory, Reaction


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color', 'icon', 'order']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'is_published', 'is_featured', 'is_pinned', 'view_count', 'created_at']
    list_filter = ['is_published', 'is_featured', 'is_pinned', 'category']
    search_fields = ['title', 'summary', 'tags']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author']
    date_hierarchy = 'created_at'
    readonly_fields = ['view_count', 'created_at', 'updated_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'content_type', 'object_id', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'content_type']
    search_fields = ['body', 'author__username']
    raw_id_fields = ['author', 'parent']


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'reaction', 'content_type', 'object_id']
    list_filter = ['reaction', 'content_type']
    raw_id_fields = ['user']
