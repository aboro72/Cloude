"""
Django admin interface for plugin management.

Allows administrators to upload, activate, deactivate, and manage plugins.
"""

import json
from pathlib import Path
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, reverse
from django.contrib import messages
from django.utils.html import format_html, mark_safe
from django.template.response import TemplateResponse

from plugins.models import Plugin, PluginLog
from plugins.loader import PluginLoader
import logging

logger = logging.getLogger(__name__)


@admin.register(Plugin)
class PluginAdmin(admin.ModelAdmin):
    """Admin interface for managing plugins"""

    list_display = [
        'name_display',
        'version',
        'status_badge',
        'enabled_badge',
        'uploaded_at',
        'action_buttons',
    ]

    list_filter = ['status', 'enabled', 'uploaded_at']
    search_fields = ['name', 'slug', 'author', 'description']

    readonly_fields = [
        'id',
        'status',
        'module_name',
        'extracted_path',
        'error_message',
        'manifest_display',
        'uploaded_at',
        'activated_at',
        'updated_at',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'slug', 'version', 'author', 'description')
        }),
        ('Files & Paths', {
            'fields': ('zip_file', 'extracted_path'),
            'classes': ('collapse',)
        }),
        ('Status & Configuration', {
            'fields': ('status', 'enabled', 'module_name', 'position'),
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',),
            'description': 'Shows error details if plugin failed to load'
        }),
        ('Technical Details', {
            'fields': ('manifest_display',),
            'classes': ('collapse',),
            'description': 'Plugin manifest data from plugin.json'
        }),
        ('Metadata', {
            'fields': ('uploaded_at', 'activated_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


    def name_display(self, obj):
        """Display plugin name with icon"""
        return format_html(
            '📦 <strong>{}</strong>',
            obj.name
        )
    name_display.short_description = 'Plugin'

    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'active': '#28a745',
            'inactive': '#6c757d',
            'error': '#dc3545',
        }
        icons = {
            'active': '✅',
            'inactive': '⭕',
            'error': '❌',
        }

        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '❓')

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def enabled_badge(self, obj):
        """Display enabled/disabled status"""
        if obj.enabled:
            return mark_safe('🟢 <strong>Enabled</strong>')
        else:
            return mark_safe('⭕ <strong>Disabled</strong>')
    enabled_badge.short_description = 'Enabled'

    def action_buttons(self, obj):
        """Display action buttons"""
        if obj.status == 'error':
            return mark_safe(
                '<span style="color: #dc3545;">⚠️ Error - Check details</span>'
            )

        if obj.enabled:
            return format_html(
                '<a class="button" style="background-color: #dc3545; color: white;" '
                'href="{}?id={}">🔴 Deactivate</a>',
                reverse('admin:plugin_deactivate'),
                obj.id
            )
        else:
            return format_html(
                '<a class="button" style="background-color: #28a745; color: white;" '
                'href="{}?id={}">🟢 Activate</a>',
                reverse('admin:plugin_activate'),
                obj.id
            )
    action_buttons.short_description = 'Actions'

    def manifest_display(self, obj):
        """Display manifest as formatted JSON"""
        import json
        manifest_json = json.dumps(obj.manifest, indent=2)
        return format_html(
            '<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; '
            'max-height: 300px; overflow-y: auto;">{}</pre>',
            manifest_json
        )
    manifest_display.short_description = 'Manifest'

    def get_urls(self):
        """Add custom admin URLs for plugin actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'activate/',
                self.admin_site.admin_view(self.activate_plugin_view),
                name='plugin_activate'
            ),
            path(
                'deactivate/',
                self.admin_site.admin_view(self.deactivate_plugin_view),
                name='plugin_deactivate'
            ),
            path(
                'upload/',
                self.admin_site.admin_view(self.upload_plugin_view),
                name='plugin_upload'
            ),
        ]
        return custom_urls + urls

    def activate_plugin_view(self, request):
        """Handle plugin activation"""
        plugin_id = request.GET.get('id')

        if not plugin_id:
            messages.error(request, 'No plugin specified')
            return redirect('admin:plugins_plugin_changelist')

        try:
            loader = PluginLoader()
            loader.load_plugin(plugin_id)
            messages.success(request, '✅ Plugin activated successfully')
            logger.info(f"Admin {request.user.username} activated plugin {plugin_id}")

        except Exception as e:
            messages.error(request, f'❌ Activation failed: {str(e)}')
            logger.error(f"Plugin activation failed: {e}")

        return redirect('admin:plugins_plugin_changelist')

    def deactivate_plugin_view(self, request):
        """Handle plugin deactivation"""
        plugin_id = request.GET.get('id')

        if not plugin_id:
            messages.error(request, 'No plugin specified')
            return redirect('admin:plugins_plugin_changelist')

        try:
            loader = PluginLoader()
            loader.unload_plugin(plugin_id)
            messages.success(request, '✅ Plugin deactivated successfully')
            logger.info(f"Admin {request.user.username} deactivated plugin {plugin_id}")

        except Exception as e:
            messages.error(request, f'❌ Deactivation failed: {str(e)}')
            logger.error(f"Plugin deactivation failed: {e}")

        return redirect('admin:plugins_plugin_changelist')

    def upload_plugin_view(self, request):
        """Handle plugin ZIP upload"""
        if request.method == 'POST':
            return self._process_plugin_upload(request)

        # GET request - show upload form
        context = self.admin_site.each_context(request)
        context['title'] = 'Upload Plugin'
        return TemplateResponse(request, 'admin/plugins/upload.html', context)

    def _process_plugin_upload(self, request):
        """Process plugin upload and create plugin record"""
        zip_file = request.FILES.get('zip_file')

        if not zip_file:
            messages.error(request, '❌ No file selected')
            return redirect('admin:plugin_upload')

        loader = PluginLoader()

        try:
            # Save uploaded file temporarily
            temp_path = Path('/tmp') / zip_file.name
            with open(temp_path, 'wb+') as f:
                for chunk in zip_file.chunks():
                    f.write(chunk)

            logger.info(f"Uploaded plugin ZIP: {zip_file.name}")

            # Validate ZIP
            manifest = loader.validate_zip(temp_path)
            logger.info(f"ZIP validation passed: {manifest['name']}")

            # Create plugin record
            plugin = Plugin.objects.create(
                name=manifest['name'],
                slug=manifest['slug'],
                version=manifest['version'],
                author=manifest.get('author', 'Unknown'),
                description=manifest.get('description', ''),
                zip_file=zip_file,
                manifest=manifest,
                installed_by=request.user,
                status='inactive'
            )

            logger.info(f"Created plugin record: {plugin.id}")

            # Extract plugin
            extract_dir = loader.extract_plugin(str(plugin.id), temp_path)
            plugin.extracted_path = str(extract_dir)
            plugin.save()

            # Log the action
            PluginLog.objects.create(
                plugin=plugin,
                action='uploaded',
                user=request.user,
                message=f"Plugin uploaded by {request.user.username}"
            )

            messages.success(
                request,
                f'✅ Plugin "{plugin.name}" uploaded successfully. '
                f'Click "Activate" to enable it.'
            )
            logger.info(f"Admin {request.user.username} uploaded plugin {plugin.name}")

            # Redirect to plugin edit page
            return redirect('admin:plugins_plugin_change', plugin.id)

        except ValueError as e:
            messages.error(request, f'❌ Invalid plugin: {str(e)}')
            logger.error(f"Plugin upload validation failed: {e}")
            return redirect('admin:plugin_upload')

        except Exception as e:
            messages.error(request, f'❌ Upload failed: {str(e)}')
            logger.error(f"Plugin upload failed: {e}")
            return redirect('admin:plugin_upload')


@admin.register(PluginLog)
class PluginLogAdmin(admin.ModelAdmin):
    """Admin interface for viewing plugin operation logs"""

    list_display = ['plugin_link', 'action_badge', 'user', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['plugin__name', 'message']

    readonly_fields = ['plugin', 'action', 'user', 'message', 'created_at']

    fieldsets = (
        ('Action Information', {
            'fields': ('plugin', 'action', 'user', 'created_at'),
        }),
        ('Details', {
            'fields': ('message',),
        }),
    )

    def plugin_link(self, obj):
        """Display plugin name as link to plugin details"""
        url = reverse('admin:plugins_plugin_change', args=[obj.plugin.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.plugin.name
        )
    plugin_link.short_description = 'Plugin'

    def action_badge(self, obj):
        """Display action with icon"""
        icons = {
            'uploaded': '📤',
            'activated': '🟢',
            'deactivated': '⭕',
            'error': '❌',
        }

        colors = {
            'uploaded': '#007bff',
            'activated': '#28a745',
            'deactivated': '#6c757d',
            'error': '#dc3545',
        }

        icon = icons.get(obj.action, '❓')
        color = colors.get(obj.action, '#6c757d')

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'
