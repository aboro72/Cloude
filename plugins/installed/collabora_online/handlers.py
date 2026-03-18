from plugins.preview import FilePreviewProvider


class CollaboraPreviewProvider(FilePreviewProvider):
    @property
    def supported_mime_types(self):
        return [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-powerpoint',
            'application/vnd.oasis.opendocument.text',
            'application/vnd.oasis.opendocument.spreadsheet',
            'application/vnd.oasis.opendocument.presentation',
            'text/plain',
            'text/csv',
            'application/rtf',
        ]

    def can_preview(self, file_obj) -> bool:
        extension = file_obj.name.rsplit('.', 1)[-1].lower() if '.' in file_obj.name else ''
        return extension in {'doc', 'docx', 'odt', 'xls', 'xlsx', 'ods', 'ppt', 'pptx', 'odp', 'csv', 'txt', 'rtf'}

    def get_preview_html(self, file_obj) -> str:
        return f'''
        <div class="collabora-preview">
            <style>
                .collabora-preview {{
                    width: 100%;
                    min-height: 85vh;
                }}
                .collabora-frame {{
                    width: 100%;
                    height: 85vh;
                    min-height: 900px;
                    border: none;
                    border-radius: 0;
                    background: #fff;
                    display: block;
                }}
            </style>
            <iframe
                class="collabora-frame"
                src="/storage/file/{file_obj.id}/office/"
                title="Collabora Online"
                loading="lazy">
            </iframe>
        </div>
        '''
