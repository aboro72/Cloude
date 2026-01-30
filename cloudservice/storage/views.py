"""
Views for Storage app.
File and folder management UI views.
"""

from django.views.generic import ListView, DetailView, CreateView, DeleteView, TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import FileResponse, JsonResponse
from django.db.models import Q, Sum
from django.core.files.base import ContentFile
from django import forms

from core.models import StorageFile, StorageFolder
import logging
import mimetypes

logger = logging.getLogger(__name__)


class FileListView(LoginRequiredMixin, ListView):
    """List files in root folder"""
    template_name = 'storage/file_list.html'
    context_object_name = 'files'
    paginate_by = 20

    def get_queryset(self):
        """Get root folder files"""
        user = self.request.user
        try:
            root_folder = StorageFolder.objects.filter(
                owner=user,
                parent=None
            ).first()
            if root_folder:
                return StorageFile.objects.filter(folder=root_folder)
        except:
            pass
        return StorageFile.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_folder'] = None
        return context


class FolderView(LoginRequiredMixin, TemplateView):
    """View folder contents"""
    template_name = 'storage/folder_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        folder = get_object_or_404(
            StorageFolder,
            id=kwargs.get('folder_id'),
            owner=self.request.user
        )
        context['folder'] = folder
        context['subfolders'] = folder.subfolders.all()
        context['files'] = folder.files.all()
        return context


class FileDetailView(LoginRequiredMixin, DetailView):
    """File detail view with preview"""
    template_name = 'storage/file_detail.html'
    model = StorageFile
    context_object_name = 'file'
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        file_obj = self.object

        # Determine MIME types
        word_types = [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
            'application/msword'  # .doc
        ]
        excel_types = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel'  # .xls
        ]
        ppt_types = [
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
            'application/vnd.ms-powerpoint'  # .ppt
        ]
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        text_types = ['text/plain', 'text/html', 'text/css', 'application/json', 'text/csv']

        # Initialize preview variables
        context['is_image'] = file_obj.mime_type in image_types
        context['is_pdf'] = file_obj.mime_type == 'application/pdf'
        context['is_text'] = file_obj.mime_type in text_types
        context['is_word'] = file_obj.mime_type in word_types
        context['is_excel'] = file_obj.mime_type in excel_types
        context['is_ppt'] = file_obj.mime_type in ppt_types
        context['plugin_preview'] = False
        context['plugin_preview_html'] = ''

        # Plugin positioning
        context['plugins_left'] = []
        context['plugins_center'] = []
        context['plugins_right'] = []

        # Check for active plugins (.plug files)
        # These can be positioned on left, center, or right
        try:
            from plugins.models import Plugin

            active_plugins = Plugin.objects.filter(enabled=True, status='active')

            for plugin in active_plugins:
                try:
                    # Load plugin preview for .plug files
                    from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER

                    handlers = hook_registry.get_handlers(
                        FILE_PREVIEW_PROVIDER,
                        plugin_type='file_preview'
                    )

                    if handlers:
                        provider = handlers[0]()
                        if provider.can_preview(file_obj):
                            plugin_html = provider.get_preview_html(file_obj)
                            plugin_data = {
                                'name': plugin.name,
                                'html': plugin_html,
                                'position': plugin.position
                            }

                            # Add to appropriate position list
                            if plugin.position == 'left':
                                context['plugins_left'].append(plugin_data)
                            elif plugin.position == 'center':
                                context['plugins_center'].append(plugin_data)
                            elif plugin.position == 'right':
                                context['plugins_right'].append(plugin_data)

                            logger.info(f"[FileDetailView] ✅ Plugin '{plugin.name}' added to {plugin.position}")
                except Exception as e:
                    logger.error(f"[FileDetailView] Error processing plugin {plugin.name}: {e}", exc_info=True)
        except Exception as e:
            logger.warning(f"[FileDetailView] Could not load plugins: {e}")

        # Determine if we can preview this file (standard types OR plugins)
        standard_previewable = any([context['is_image'], context['is_pdf'], context['is_text'],
                                    context['is_word'], context['is_excel'], context['is_ppt']])
        has_plugins = any([context['plugins_left'], context['plugins_center'], context['plugins_right']])
        context['can_preview'] = standard_previewable or has_plugins

        return context


class CreateFileForm(forms.Form):
    """Form for creating new files"""
    filename = forms.CharField(
        max_length=255,
        label='Dateiname',
        help_text='z.B. test.txt, notes.md, clock.clock'
    )
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 5}),
        label='Inhalt (optional)',
        help_text='Leer lassen für leere Datei'
    )


class CreateFileView(LoginRequiredMixin, FormView):
    """Create new file (empty or with content)"""
    template_name = 'storage/create_file.html'
    form_class = CreateFileForm
    success_url = reverse_lazy('storage:file_list')

    def form_valid(self, form):
        """Create file with content"""
        try:
            # Get or create root folder
            root_folder, _ = StorageFolder.objects.get_or_create(
                owner=self.request.user,
                parent=None,
                defaults={'name': 'Root', 'description': 'Root folder'}
            )

            filename = form.cleaned_data['filename']
            content = form.cleaned_data.get('content', '')

            # Create file content
            file_content = ContentFile(content.encode('utf-8'))

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Create storage file
            storage_file = StorageFile(
                owner=self.request.user,
                folder=root_folder,
                name=filename,
                size=file_content.size,
                mime_type=mime_type
            )
            storage_file.file.save(filename, file_content)
            storage_file.save()

            logger.info(f"File created: {filename} by {self.request.user.username}")

            from django.contrib import messages
            messages.success(self.request, f'✅ Datei "{filename}" erstellt')

            return super().form_valid(form)

        except Exception as e:
            logger.error(f"Error creating file: {e}")
            from django.contrib import messages
            messages.error(self.request, f'❌ Fehler beim Erstellen: {e}')
            return redirect('storage:file_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Neue Datei erstellen'
        return context


class FileUploadView(LoginRequiredMixin, CreateView):
    """File upload view - AJAX/API endpoint"""
    model = StorageFile
    fields = ['file', 'name', 'description']

    def post(self, request, *args, **kwargs):
        """Handle file upload"""
        if request.FILES.get('file'):
            try:
                # Get or create root folder
                root_folder, _ = StorageFolder.objects.get_or_create(
                    owner=request.user,
                    parent=None,
                    defaults={'name': 'Root', 'description': 'Root folder'}
                )

                # Get uploaded file
                uploaded_file = request.FILES['file']

                # Create file object
                storage_file = StorageFile(
                    owner=request.user,
                    folder=root_folder,
                    file=uploaded_file,
                    name=request.POST.get('name', uploaded_file.name),
                    size=uploaded_file.size,
                    mime_type=uploaded_file.content_type or 'application/octet-stream'
                )
                storage_file.save()

                logger.info(f"File uploaded: {storage_file.name} by {request.user.username}")

                return JsonResponse({
                    'success': True,
                    'file_id': storage_file.id,
                    'file_name': storage_file.name,
                    'file_size': storage_file.size,
                    'message': f'Datei {uploaded_file.name} erfolgreich hochgeladen'
                })
            except Exception as e:
                logger.error(f"Upload error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)

        return JsonResponse({
            'success': False,
            'error': 'Keine Datei bereitgestellt'
        }, status=400)

    def get_success_url(self):
        return reverse_lazy('storage:file_list')


class FileDownloadView(LoginRequiredMixin, DetailView):
    """Download file"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user)

    def get(self, request, *args, **kwargs):
        file_obj = self.get_object()
        file_obj.increment_download_count()

        response = FileResponse(
            file_obj.file.open('rb'),
            as_attachment=True
        )
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
        return response


class FileRenameView(LoginRequiredMixin, DetailView):
    """Rename file"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user)

    def post(self, request, *args, **kwargs):
        file_obj = self.get_object()
        new_name = request.POST.get('name')

        if new_name:
            file_obj.name = new_name
            file_obj.save()

        return redirect('storage:file_detail', file_id=file_obj.id)


class FileMoveView(LoginRequiredMixin, DetailView):
    """Move file to folder"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user)

    def post(self, request, *args, **kwargs):
        file_obj = self.get_object()
        new_folder_id = request.POST.get('folder_id')

        new_folder = get_object_or_404(
            StorageFolder,
            id=new_folder_id,
            owner=request.user
        )

        file_obj.folder = new_folder
        file_obj.save()

        return JsonResponse({'success': True})


class FileDeleteView(LoginRequiredMixin, DeleteView):
    """Delete file"""
    model = StorageFile
    pk_url_kwarg = 'file_id'
    success_url = reverse_lazy('storage:file_list')

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user)


class FolderCreateView(LoginRequiredMixin, CreateView):
    """Create folder"""
    model = StorageFolder
    fields = ['name', 'description']

    def form_valid(self, form):
        # Get or create root folder
        root_folder, _ = StorageFolder.objects.get_or_create(
            owner=self.request.user,
            parent=None,
            defaults={'name': 'Root', 'description': 'Root folder'}
        )

        form.instance.owner = self.request.user
        form.instance.parent = root_folder

        response = super().form_valid(form)

        # Return JSON response for AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'folder_id': self.object.id,
                'folder_name': self.object.name,
                'message': f'Ordner {self.object.name} erstellt'
            })

        return response

    def get_success_url(self):
        return reverse_lazy('storage:file_list')


class FolderDeleteView(LoginRequiredMixin, DeleteView):
    """Delete folder"""
    model = StorageFolder
    pk_url_kwarg = 'folder_id'
    success_url = reverse_lazy('storage:file_list')

    def get_queryset(self):
        return StorageFolder.objects.filter(owner=self.request.user)


class FileVersionsView(LoginRequiredMixin, ListView):
    """View file versions"""
    template_name = 'storage/file_versions.html'
    context_object_name = 'versions'

    def get_queryset(self):
        from core.models import FileVersion
        file_id = self.kwargs.get('file_id')
        return FileVersion.objects.filter(file_id=file_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        file_id = self.kwargs.get('file_id')
        context['file'] = get_object_or_404(
            StorageFile,
            id=file_id,
            owner=self.request.user
        )
        return context


class RestoreVersionView(LoginRequiredMixin, DetailView):
    """Restore file version"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def post(self, request, *args, **kwargs):
        from core.models import FileVersion
        file_obj = self.get_object()
        version_id = request.POST.get('version_id')

        version = get_object_or_404(
            FileVersion,
            id=version_id,
            file=file_obj
        )

        # Create new version with restored content
        new_version_number = file_obj.version_count + 1

        FileVersion.objects.create(
            file=file_obj,
            version_number=new_version_number,
            file_data=version.file_data,
            file_hash=version.file_hash,
            size=version.size,
            change_description=f"Restored from version {version.version_number}",
            is_current=True
        )

        file_obj.version_count = new_version_number
        file_obj.save()

        return redirect('storage:file_detail', pk=file_obj.id)


class TrashView(LoginRequiredMixin, ListView):
    """View trash/bin"""
    template_name = 'storage/trash.html'
    context_object_name = 'trash_items'

    def get_queryset(self):
        from storage.models import TrashBin
        return TrashBin.objects.filter(user=self.request.user)


class RestoreFromTrashView(LoginRequiredMixin, DetailView):
    """Restore item from trash"""
    pk_url_kwarg = 'trash_id'

    def get_queryset(self):
        from storage.models import TrashBin
        return TrashBin.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        from storage.models import TrashBin
        trash_item = get_object_or_404(TrashBin, id=self.kwargs.get('trash_id'), user=request.user)
        # Implementation for restoring from trash
        trash_item.delete()
        return JsonResponse({'success': True})


class PermanentlyDeleteView(LoginRequiredMixin, DetailView):
    """Permanently delete from trash"""
    pk_url_kwarg = 'trash_id'

    def get_queryset(self):
        from storage.models import TrashBin
        return TrashBin.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        from storage.models import TrashBin
        trash_item = get_object_or_404(TrashBin, id=self.kwargs.get('trash_id'), user=request.user)
        # Permanently delete the file
        if trash_item.file:
            trash_item.file.file.delete()
        trash_item.delete()
        return JsonResponse({'success': True})


class SearchView(LoginRequiredMixin, ListView):
    """Search files and folders"""
    template_name = 'storage/search.html'
    context_object_name = 'results'

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        return StorageFile.objects.filter(
            owner=self.request.user,
            name__icontains=query
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class StorageStatsView(LoginRequiredMixin, TemplateView):
    """View storage statistics"""
    template_name = 'storage/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile

        # File counts
        all_files = StorageFile.objects.filter(owner=self.request.user)
        context['total_files'] = all_files.count()
        context['total_folders'] = StorageFolder.objects.filter(
            owner=self.request.user
        ).count()

        # Storage info
        storage_used_bytes = profile.get_storage_used()
        storage_used_mb = storage_used_bytes / (1024 * 1024)
        storage_used_gb = storage_used_mb / 1024
        storage_quota_bytes = profile.storage_quota
        storage_quota_gb = storage_quota_bytes / (1024 * 1024 * 1024)
        storage_remaining_bytes = storage_quota_bytes - storage_used_bytes
        storage_remaining_gb = storage_remaining_bytes / (1024 * 1024 * 1024)

        context['storage_used_gb'] = round(storage_used_gb, 2)
        context['storage_quota_gb'] = round(storage_quota_gb, 2)
        context['storage_remaining_gb'] = max(0, round(storage_remaining_gb, 2))
        context['storage_percentage'] = profile.get_storage_used_percentage()

        # Download counts
        context['total_downloads'] = all_files.aggregate(
            total=Sum('download_count')
        )['total'] or 0

        # Last updated
        latest_file = all_files.order_by('-updated_at').first()
        context['last_updated'] = latest_file.updated_at.strftime('%d.%m.%Y %H:%M') if latest_file else 'Nie'

        # File type distribution
        file_types = {}
        total_size = storage_used_bytes if storage_used_bytes > 0 else 1

        for file_obj in all_files:
            ext = file_obj.name.split('.')[-1].upper() if '.' in file_obj.name else 'Andere'
            if ext not in file_types:
                file_types[ext] = {'count': 0, 'size': 0, 'percentage': 0}
            file_types[ext]['count'] += 1
            file_types[ext]['size'] += file_obj.size

        # Calculate percentages
        for ext in file_types:
            file_types[ext]['percentage'] = (file_types[ext]['size'] / total_size) * 100

        # Sort by size
        context['file_types'] = dict(sorted(
            file_types.items(),
            key=lambda x: x[1]['size'],
            reverse=True
        ))

        return context
