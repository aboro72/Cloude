"""
Views for Storage app.
File and folder management UI views.
"""

from django.views.generic import ListView, DetailView, CreateView, DeleteView, TemplateView, FormView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import FileResponse, JsonResponse, Http404, HttpResponse
from django.db.models import Q, Sum
from django.core.files.base import ContentFile, File
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django import forms
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

from core.models import StorageFile, StorageFolder
import logging
import mimetypes
import os
from urllib.parse import quote

logger = logging.getLogger(__name__)

COLLABORA_EXTENSIONS = {
    'doc', 'docx', 'odt', 'xls', 'xlsx', 'ods', 'ppt', 'pptx', 'odp',
    'csv', 'txt', 'rtf',
}


def get_remaining_quota_bytes(user):
    """Return the remaining quota in bytes for the given user."""
    return user.profile.get_storage_remaining()


def get_or_create_root_folder(user):
    """Return the user's existing root folder, creating one if needed."""
    root_folder = StorageFolder.objects.filter(owner=user, parent=None).first()
    if root_folder:
        return root_folder

    return StorageFolder.objects.create(
        owner=user,
        parent=None,
        name='Root',
        description='Root folder',
    )


def ensure_quota_available(user, incoming_size):
    """Raise ValueError if the incoming upload would exceed the user's quota."""
    remaining_bytes = get_remaining_quota_bytes(user)
    if incoming_size > remaining_bytes:
        remaining_mb = remaining_bytes / (1024 * 1024)
        required_mb = incoming_size / (1024 * 1024)
        raise ValueError(
            f'Speicherlimit erreicht. Frei: {remaining_mb:.2f} MB, benoetigt: {required_mb:.2f} MB.'
        )


def supports_collabora(file_obj):
    extension = os.path.splitext(file_obj.name)[1].lstrip('.').lower()
    return extension in COLLABORA_EXTENSIONS


def build_collabora_token(user, file_obj):
    return signing.dumps(
        {
            'user_id': user.id,
            'file_id': file_obj.id,
            'can_write': True,
        },
        salt='collabora-wopi',
    )


def parse_collabora_token(token, file_id):
    payload = signing.loads(
        token,
        salt='collabora-wopi',
        max_age=settings.COLLABORA_ACCESS_TOKEN_TTL,
    )
    if payload.get('file_id') != file_id:
        raise signing.BadSignature('File mismatch')
    return payload


def get_wopi_lock_key(file_id):
    return f'collabora:wopi-lock:{file_id}'


@method_decorator(never_cache, name='dispatch')
class FileListView(LoginRequiredMixin, ListView):
    """List files in root folder"""
    template_name = 'storage/file_list.html'
    context_object_name = 'files'
    paginate_by = 20

    def get_queryset(self):
        """Get root folder files (excluding trashed)"""
        user = self.request.user
        try:
            root_folder = get_or_create_root_folder(user)
            if root_folder:
                return StorageFile.objects.filter(folder=root_folder, is_trashed=False)
        except:
            pass
        return StorageFile.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        root_folder = get_or_create_root_folder(self.request.user)
        context['current_folder'] = None
        context['subfolders'] = (
            root_folder.subfolders.all()
            if root_folder else StorageFolder.objects.none()
        )
        context['move_targets'] = StorageFolder.objects.filter(owner=self.request.user)
        return context


@method_decorator(never_cache, name='dispatch')
class FolderView(LoginRequiredMixin, TemplateView):
    """View folder contents"""
    template_name = 'storage/file_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        folder = get_object_or_404(
            StorageFolder,
            id=kwargs.get('folder_id'),
            owner=self.request.user
        )
        context['folder'] = folder
        context['current_folder'] = folder
        context['subfolders'] = folder.subfolders.all()
        context['files'] = folder.files.filter(is_trashed=False)
        context['move_targets'] = StorageFolder.objects.filter(owner=self.request.user).exclude(id=folder.id)
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

        # Debug: Log file info
        logger.info(f"[FileDetailView] File: {file_obj.name}")
        logger.info(f"[FileDetailView] MIME: {file_obj.mime_type}")
        logger.info(f"[FileDetailView] Has file: {bool(file_obj.file)}")
        if file_obj.file:
            logger.info(f"[FileDetailView] File URL: {file_obj.file.url}")
            logger.info(f"[FileDetailView] File path: {file_obj.file.path}")

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
        image_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
            'image/svg+xml', 'image/bmp', 'image/tiff', 'image/x-icon'
        ]
        video_types = [
            'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime',
            'video/x-msvideo', 'video/x-matroska', 'video/mpeg'
        ]
        audio_types = [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg',
            'audio/webm', 'audio/flac', 'audio/aac'
        ]
        text_types = ['text/plain', 'text/html', 'text/css', 'application/json', 'text/csv']

        # Check by extension if MIME type detection failed
        file_ext = file_obj.name.lower().split('.')[-1] if '.' in file_obj.name else ''
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'tiff', 'ico']
        video_extensions = ['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'mpeg', 'mpg']
        audio_extensions = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']

        # Initialize preview variables
        is_image_by_mime = file_obj.mime_type in image_types if file_obj.mime_type else False
        is_image_by_ext = file_ext in image_extensions
        context['is_image'] = is_image_by_mime or is_image_by_ext

        is_video_by_mime = file_obj.mime_type in video_types if file_obj.mime_type else False
        is_video_by_ext = file_ext in video_extensions
        context['is_video'] = is_video_by_mime or is_video_by_ext

        is_audio_by_mime = file_obj.mime_type in audio_types if file_obj.mime_type else False
        is_audio_by_ext = file_ext in audio_extensions
        context['is_audio'] = is_audio_by_mime or is_audio_by_ext

        context['is_pdf'] = file_obj.mime_type == 'application/pdf' or file_ext == 'pdf'
        context['is_text'] = file_obj.mime_type in text_types if file_obj.mime_type else False
        context['is_word'] = file_obj.mime_type in word_types if file_obj.mime_type else False
        context['is_excel'] = file_obj.mime_type in excel_types if file_obj.mime_type else False
        context['is_ppt'] = file_obj.mime_type in ppt_types if file_obj.mime_type else False

        # Add file URL to context for debugging
        context['file_url'] = file_obj.file.url if file_obj.file else None
        context['has_file'] = bool(file_obj.file)
        context['plugin_preview'] = False
        context['plugin_preview_html'] = ''

        # Plugin positioning
        context['plugins_left'] = []
        context['plugins_center'] = []
        context['plugins_right'] = []
        context['single_plugin_preview'] = ''

        # Check for active plugins (.plug files)
        # These can be positioned on left, center, or right
        try:
            from plugins.models import Plugin

            active_plugins = Plugin.objects.filter(enabled=True, status='active')
            from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER
            handlers = hook_registry.get_handlers(FILE_PREVIEW_PROVIDER)

            for plugin in active_plugins:
                try:
                    matching_handler = next(
                        (
                            handler for handler in handlers
                            if plugin.module_name and handler.__module__.startswith(f'{plugin.module_name}.')
                        ),
                        None,
                    )

                    if matching_handler:
                        provider = matching_handler()
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
        all_plugins = context['plugins_left'] + context['plugins_center'] + context['plugins_right']
        if len(all_plugins) == 1:
            context['single_plugin_preview'] = all_plugins[0]['html']

        standard_previewable = any([
            context['is_image'], context['is_video'], context['is_audio'],
            context['is_pdf'], context['is_text'],
            context['is_word'], context['is_excel'], context['is_ppt']
        ])
        has_plugins = any([context['plugins_left'], context['plugins_center'], context['plugins_right']])
        context['can_preview'] = standard_previewable or has_plugins

        return context


class CollaboraOfficeView(LoginRequiredMixin, View):
    """Redirect authenticated users into the Collabora editor for a file."""

    def get(self, request, file_id, *args, **kwargs):
        file_obj = get_object_or_404(StorageFile, id=file_id, owner=request.user)
        if not supports_collabora(file_obj):
            raise Http404("File type is not supported by Collabora")

        token = build_collabora_token(request.user, file_obj)
        wopi_src = quote(
            f"{settings.CLOUDSERVICE_EXTERNAL_URL.rstrip('/')}{reverse('storage:wopi_file', kwargs={'file_id': file_obj.id})}",
            safe='',
        )
        collabora_url = (
            f"{settings.COLLABORA_BASE_URL.rstrip('/')}/browser/dist/cool.html"
            f"?WOPISrc={wopi_src}&access_token={quote(token, safe='')}&lang=de"
        )
        return redirect(collabora_url)


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
            root_folder = get_or_create_root_folder(self.request.user)

            filename = form.cleaned_data['filename']
            content = form.cleaned_data.get('content', '')

            # Create file content
            file_content = ContentFile(content.encode('utf-8'))
            ensure_quota_available(self.request.user, file_content.size)

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
                root_folder = get_or_create_root_folder(request.user)

                # Get uploaded file
                uploaded_file = request.FILES['file']
                ensure_quota_available(request.user, uploaded_file.size)

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


class ChunkUploadView(LoginRequiredMixin, CreateView):
    """Chunked file upload endpoint for large files (bypasses Cloudflare 100MB limit)"""

    def post(self, request, *args, **kwargs):
        upload_id = request.POST.get('upload_id')
        chunk_index = request.POST.get('chunk_index')
        total_chunks = request.POST.get('total_chunks')
        filename = request.POST.get('filename')
        total_size = request.POST.get('total_size')
        folder_id = request.POST.get('folder_id')
        chunk_file = request.FILES.get('chunk')

        if not all([upload_id, total_chunks, filename, chunk_file]) or chunk_index is None:
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)

        try:
            chunk_index = int(chunk_index)
            total_chunks = int(total_chunks)
            total_size = int(total_size) if total_size is not None else None

            if total_size is not None:
                ensure_quota_available(request.user, total_size)

            # Save chunk to temp directory
            tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp_chunks', upload_id)
            os.makedirs(tmp_dir, exist_ok=True)
            chunk_path = os.path.join(tmp_dir, f'chunk_{chunk_index:06d}')

            with open(chunk_path, 'wb') as f:
                for data in chunk_file.chunks():
                    f.write(data)

            # Check if all chunks are present
            received = len([
                name for name in os.listdir(tmp_dir)
                if name.startswith('chunk_')
            ])

            if received < total_chunks:
                return JsonResponse({
                    'success': True,
                    'complete': False,
                    'received': received,
                    'total': total_chunks
                })

            # All chunks received — assemble directly into MEDIA_ROOT (no double-copy)
            import shutil
            from django.utils import timezone
            from django.db.models import Model as DjangoModel

            target_folder = None
            if folder_id:
                target_folder = StorageFolder.objects.filter(
                    id=folder_id,
                    owner=request.user,
                ).first()
            if target_folder is None:
                target_folder = get_or_create_root_folder(request.user)

            # Build the target path matching upload_to='files/%Y/%m/%d/%H%M%S'
            now = timezone.now()
            upload_subdir = now.strftime('files/%Y/%m/%d/%H%M%S')
            media_dir = os.path.join(settings.MEDIA_ROOT, upload_subdir)
            os.makedirs(media_dir, exist_ok=True)
            final_path = os.path.join(media_dir, filename)

            # Concatenate chunks in order using a large buffer for speed
            with open(final_path, 'wb') as outfile:
                for i in range(total_chunks):
                    part = os.path.join(tmp_dir, f'chunk_{i:06d}')
                    with open(part, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile, length=8 * 1024 * 1024)

            file_size = os.path.getsize(final_path)
            ensure_quota_available(request.user, file_size)
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Create StorageFile pointing to the assembled file without re-reading it
            # Use DjangoModel.save() to bypass the custom save() which would re-hash the file
            storage_file = StorageFile(
                owner=request.user,
                folder=target_folder,
                name=filename,
                size=file_size,
                mime_type=mime_type,
                file_hash=f'chunked-{upload_id[:32]}',  # skip slow SHA256 for large files
            )
            storage_file.file.name = f'{upload_subdir}/{filename}'
            DjangoModel.save(storage_file)  # bypass custom save() — hash already set

            # Clean up temp dir in background so we can respond immediately
            import threading
            threading.Thread(
                target=shutil.rmtree, args=(tmp_dir,), kwargs={'ignore_errors': True}
            ).start()

            logger.info(f"Chunked upload complete: {filename} ({file_size} bytes) by {request.user.username}")

            return JsonResponse({
                'success': True,
                'complete': True,
                'file_id': storage_file.id,
                'file_name': storage_file.name,
                'file_size': storage_file.size,
            })

        except Exception as e:
            if 'tmp_dir' in locals():
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.error(f"Chunk upload error: {e}", exc_info=True)
            status_code = 400 if isinstance(e, ValueError) else 500
            return JsonResponse({'success': False, 'error': str(e)}, status=status_code)


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


class FilePreviewView(LoginRequiredMixin, View):
    """Serve files inline for authenticated previews."""

    def get(self, request, file_id, *args, **kwargs):
        file_obj = get_object_or_404(StorageFile, id=file_id, owner=request.user)

        if not file_obj.file or not file_obj.file.name:
            raise Http404("No file attached")

        if not file_obj.file.storage.exists(file_obj.file.name):
            raise Http404("Stored file is missing")

        content_type = file_obj.mime_type or mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream'
        range_header = request.headers.get('Range')
        file_handle = file_obj.file.open('rb')
        file_size = file_obj.file.size

        if range_header:
            start_str, end_str = range_header.removeprefix('bytes=').split('-', 1)
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)

            if start > end or start >= file_size:
                file_handle.close()
                response = HttpResponse(status=416)
                response['Content-Range'] = f'bytes */{file_size}'
                return response

            file_handle.seek(start)
            response = HttpResponse(
                file_handle.read(end - start + 1),
                status=206,
                content_type=content_type,
            )
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Content-Length'] = str(end - start + 1)
        else:
            response = FileResponse(
                file_handle,
                as_attachment=False,
                content_type=content_type,
            )
            response['Content-Length'] = str(file_size)

        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'inline; filename="{file_obj.name}"'
        return response


@method_decorator(csrf_exempt, name='dispatch')
class WopiFileView(View):
    """WOPI file metadata and lock endpoint for Collabora."""

    def get_file(self, file_id):
        file_id = int(file_id)
        return get_object_or_404(StorageFile, id=file_id)

    def get_payload(self, request, file_id):
        file_id = int(file_id)
        token = request.GET.get('access_token') or request.POST.get('access_token')
        if not token:
            raise Http404("Missing access token")
        return parse_collabora_token(token, file_id)

    def get(self, request, file_id, *args, **kwargs):
        file_obj = self.get_file(file_id)
        payload = self.get_payload(request, file_id)

        return JsonResponse({
            'BaseFileName': file_obj.name,
            'OwnerId': str(file_obj.owner_id),
            'Size': file_obj.size,
            'UserId': str(payload['user_id']),
            'UserFriendlyName': file_obj.owner.username,
            'Version': str(file_obj.updated_at.timestamp()),
            'UserCanWrite': bool(payload.get('can_write')),
            'SupportsUpdate': True,
            'SupportsLocks': True,
        })

    def post(self, request, file_id, *args, **kwargs):
        self.get_payload(request, file_id)
        lock_key = get_wopi_lock_key(file_id)
        override = request.headers.get('X-WOPI-Override', '').upper()
        requested_lock = request.headers.get('X-WOPI-Lock', '')
        current_lock = cache.get(lock_key)

        if override == 'LOCK':
            if current_lock and current_lock != requested_lock:
                response = HttpResponse(status=409)
                response['X-WOPI-Lock'] = current_lock
                return response
            cache.set(lock_key, requested_lock, timeout=settings.COLLABORA_ACCESS_TOKEN_TTL)
            return HttpResponse(status=200)

        if override == 'REFRESH_LOCK':
            if current_lock != requested_lock:
                response = HttpResponse(status=409)
                response['X-WOPI-Lock'] = current_lock or ''
                return response
            cache.set(lock_key, requested_lock, timeout=settings.COLLABORA_ACCESS_TOKEN_TTL)
            return HttpResponse(status=200)

        if override == 'UNLOCK':
            if current_lock != requested_lock:
                response = HttpResponse(status=409)
                response['X-WOPI-Lock'] = current_lock or ''
                return response
            cache.delete(lock_key)
            return HttpResponse(status=200)

        if override == 'GET_LOCK':
            response = HttpResponse(status=200)
            response['X-WOPI-Lock'] = current_lock or ''
            return response

        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name='dispatch')
class WopiFileContentsView(View):
    """WOPI file contents endpoint for Collabora."""

    def get_file(self, file_id):
        file_id = int(file_id)
        return get_object_or_404(StorageFile, id=file_id)

    def get_payload(self, request, file_id):
        file_id = int(file_id)
        token = request.GET.get('access_token') or request.POST.get('access_token')
        if not token:
            raise Http404("Missing access token")
        return parse_collabora_token(token, file_id)

    def get(self, request, file_id, *args, **kwargs):
        file_obj = self.get_file(file_id)
        self.get_payload(request, file_id)
        return FileResponse(file_obj.file.open('rb'), as_attachment=False, content_type=file_obj.mime_type or 'application/octet-stream')

    def post(self, request, file_id, *args, **kwargs):
        file_obj = self.get_file(file_id)
        payload = self.get_payload(request, file_id)
        if not payload.get('can_write'):
            return HttpResponse(status=403)

        override = request.headers.get('X-WOPI-Override', '').upper()
        if override != 'PUT':
            return HttpResponse(status=200)

        uploaded_content = request.body
        file_obj.file.save(file_obj.name, ContentFile(uploaded_content), save=False)
        file_obj.file_hash = ''
        file_obj.save()
        return HttpResponse(status=200)


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

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'folder_id': new_folder.id, 'folder_name': new_folder.name})

        return JsonResponse({'success': True})


class FileDeleteView(LoginRequiredMixin, DetailView):
    """Move file to trash (soft delete)"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user, is_trashed=False)

    def post(self, request, *args, **kwargs):
        file_obj = self.get_object()
        file_obj.move_to_trash()

        logger.info(f"File moved to trash: {file_obj.name} by {request.user.username}")

        from django.contrib import messages
        messages.success(request, f'Datei "{file_obj.name}" in den Papierkorb verschoben.')

        return redirect('storage:file_list')

    def get(self, request, *args, **kwargs):
        # Also handle GET requests (from direct link clicks)
        return self.post(request, *args, **kwargs)


class FolderCreateView(LoginRequiredMixin, CreateView):
    """Create folder"""
    model = StorageFolder
    fields = ['name', 'description']

    def form_valid(self, form):
        # Get or create root folder
        root_folder = get_or_create_root_folder(self.request.user)

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

    def post(self, request, *args, **kwargs):
        folder = self.get_object()

        if folder.parent is None:
            message = 'Der Root-Ordner kann nicht gelöscht werden.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': message}, status=400)

            from django.contrib import messages
            messages.error(request, message)
            return redirect('storage:file_list')

        folder_name = folder.name
        folder.delete()

        from django.contrib import messages
        messages.success(request, f'Ordner "{folder_name}" gelöscht.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Ordner "{folder_name}" gelöscht.'})

        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


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
    """View trash/bin - shows trashed files"""
    template_name = 'storage/trash.html'
    context_object_name = 'trash_items'

    def get_queryset(self):
        """Get trashed files for current user"""
        return StorageFile.objects.filter(
            owner=self.request.user,
            is_trashed=True
        ).order_by('-trashed_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate total size of trashed files
        total_size = sum(f.size for f in context['trash_items'])
        context['total_size'] = total_size
        context['total_count'] = context['trash_items'].count()
        return context


class RestoreFromTrashView(LoginRequiredMixin, DetailView):
    """Restore file from trash"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user, is_trashed=True)

    def post(self, request, *args, **kwargs):
        file_obj = self.get_object()
        file_obj.restore_from_trash()

        logger.info(f"File restored from trash: {file_obj.name} by {request.user.username}")

        from django.contrib import messages
        messages.success(request, f'Datei "{file_obj.name}" wiederhergestellt.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Datei "{file_obj.name}" wiederhergestellt.'})

        return redirect('storage:trash')

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class PermanentlyDeleteView(LoginRequiredMixin, DetailView):
    """Permanently delete file from trash"""
    model = StorageFile
    pk_url_kwarg = 'file_id'

    def get_queryset(self):
        return StorageFile.objects.filter(owner=self.request.user, is_trashed=True)

    def post(self, request, *args, **kwargs):
        file_obj = self.get_object()
        file_name = file_obj.name

        file_obj.permanent_delete()

        logger.info(f"File permanently deleted: {file_name} by {request.user.username}")

        from django.contrib import messages
        messages.success(request, f'Datei "{file_name}" endgültig gelöscht.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Datei "{file_name}" endgültig gelöscht.'})

        return redirect('storage:trash')

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class EmptyTrashView(LoginRequiredMixin, TemplateView):
    """Empty entire trash"""

    def post(self, request, *args, **kwargs):
        trashed_files = StorageFile.objects.filter(owner=request.user, is_trashed=True)
        count = trashed_files.count()

        for file_obj in trashed_files:
            file_obj.permanent_delete()

        logger.info(f"Trash emptied: {count} files by {request.user.username}")

        from django.contrib import messages
        messages.success(request, f'{count} Datei(en) endgültig gelöscht.')

        return redirect('storage:trash')


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
