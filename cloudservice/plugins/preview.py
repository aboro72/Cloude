"""
Base classes for file preview plugins.

Plugin developers should inherit from FilePreviewProvider to implement
custom file type previews.
"""

from abc import ABC, abstractmethod
from typing import List


class FilePreviewProvider(ABC):
    """
    Abstract base class for file preview plugins.

    Subclass this to implement preview functionality for specific file types.

    Example:
        class MarkdownPreviewProvider(FilePreviewProvider):
            @property
            def supported_mime_types(self):
                return ['text/markdown', 'text/x-markdown']

            def can_preview(self, file_obj):
                return file_obj.mime_type in self.supported_mime_types

            def get_preview_html(self, file_obj):
                with file_obj.file.open('r') as f:
                    content = f.read()
                html = markdown.markdown(content)
                return f'<div class="markdown">{html}</div>'
    """

    @property
    @abstractmethod
    def supported_mime_types(self) -> List[str]:
        """
        List of MIME types this provider supports.

        Returns:
            List of MIME type strings (e.g., ['text/markdown', 'text/x-markdown'])
        """
        pass

    @abstractmethod
    def can_preview(self, file_obj) -> bool:
        """
        Check if this provider can preview the given file.

        Called before attempting to generate preview.

        Args:
            file_obj: StorageFile instance from core.models

        Returns:
            True if this provider can preview the file, False otherwise
        """
        pass

    @abstractmethod
    def get_preview_html(self, file_obj) -> str:
        """
        Generate HTML preview for the file.

        Args:
            file_obj: StorageFile instance from core.models

        Returns:
            HTML string to display as preview

        Raises:
            Exception: If preview generation fails (will be caught and logged)
        """
        pass
