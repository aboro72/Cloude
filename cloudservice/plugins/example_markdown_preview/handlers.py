"""
Markdown preview provider handler.

Implements the FilePreviewProvider interface to render Markdown files as HTML.
"""

from plugins.preview import FilePreviewProvider
import markdown
import logging

logger = logging.getLogger(__name__)


class MarkdownPreviewProvider(FilePreviewProvider):
    """
    Provides Markdown file preview functionality.

    Converts Markdown (.md) files to styled HTML for preview display.
    Uses Python's markdown library for conversion.
    """

    @property
    def supported_mime_types(self):
        """
        MIME types supported by this provider.

        Returns:
            List of MIME type strings
        """
        return [
            'text/markdown',
            'text/x-markdown',
            'text/plain',  # Also support plain text .md files
        ]

    def can_preview(self, file_obj) -> bool:
        """
        Check if this provider can preview the given file.

        Args:
            file_obj: StorageFile instance

        Returns:
            True if file is a supported Markdown type
        """
        return file_obj.mime_type in self.supported_mime_types

    def get_preview_html(self, file_obj) -> str:
        """
        Generate HTML preview of Markdown file.

        Reads the file content, converts Markdown to HTML,
        and wraps it in styled div.

        Args:
            file_obj: StorageFile instance

        Returns:
            HTML string ready for display

        Raises:
            Exception: If file reading or conversion fails
        """
        try:
            logger.info(f"Generating Markdown preview for {file_obj.name}")

            # Read file content
            with file_obj.file.open('r', encoding='utf-8') as f:
                content = f.read()

            # Convert Markdown to HTML
            html = markdown.markdown(
                content,
                extensions=[
                    'extra',  # Extra features like tables, footnotes
                    'codehilite',  # Code syntax highlighting
                    'toc',  # Table of contents
                ],
                extension_configs={
                    'codehilite': {
                        'css_class': 'highlight',
                        'linenums': False,
                    }
                }
            )

            # Wrap in styled container
            styled_html = f'''
            <div class="markdown-preview">
                <style>
                    .markdown-preview {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .markdown-preview h1,
                    .markdown-preview h2,
                    .markdown-preview h3,
                    .markdown-preview h4,
                    .markdown-preview h5,
                    .markdown-preview h6 {{
                        margin-top: 24px;
                        margin-bottom: 16px;
                        font-weight: 600;
                        line-height: 1.25;
                        border-bottom: 1px solid #eaecef;
                        padding-bottom: 0.3em;
                    }}
                    .markdown-preview h1 {{
                        font-size: 2em;
                    }}
                    .markdown-preview h2 {{
                        font-size: 1.5em;
                    }}
                    .markdown-preview h3 {{
                        font-size: 1.25em;
                    }}
                    .markdown-preview code {{
                        background-color: #f6f8fa;
                        padding: 0.2em 0.4em;
                        margin: 0;
                        border-radius: 3px;
                        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                        font-size: 85%;
                    }}
                    .markdown-preview pre {{
                        background-color: #f6f8fa;
                        border-radius: 6px;
                        padding: 16px;
                        overflow: auto;
                        line-height: 1.45;
                    }}
                    .markdown-preview pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    .markdown-preview blockquote {{
                        padding: 0 1em;
                        color: #6a737d;
                        border-left: 0.25em solid #dfe2e5;
                        margin: 0 0 16px 0;
                    }}
                    .markdown-preview table {{
                        border-collapse: collapse;
                        width: 100%;
                    }}
                    .markdown-preview table th,
                    .markdown-preview table td {{
                        border: 1px solid #dfe2e5;
                        padding: 6px 13px;
                    }}
                    .markdown-preview table tr:nth-child(2n) {{
                        background-color: #f6f8fa;
                    }}
                    .markdown-preview a {{
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    .markdown-preview a:hover {{
                        text-decoration: underline;
                    }}
                </style>
                {html}
            </div>
            '''

            logger.info(f"Markdown preview generated successfully for {file_obj.name}")
            return styled_html

        except Exception as e:
            logger.error(f"Failed to generate Markdown preview: {e}")
            raise
