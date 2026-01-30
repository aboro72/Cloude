# CloudService Plugin Development Guide

## Overview

CloudService has a plugin system that allows you to extend functionality without modifying the core code. Plugins can be uploaded, activated, and deactivated via the Django Admin interface - **no server restart needed**.

## Quick Start

### Step 1: Create Plugin Directory Structure

```
my_plugin/
├── __init__.py
├── apps.py              (Django AppConfig)
├── handlers.py          (Feature implementation)
├── plugin.json          (Manifest)
└── [optional files]
```

### Step 2: Write plugin.json Manifest

```json
{
  "name": "My Plugin",
  "slug": "my-plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What it does",

  "django_app": {
    "app_config": "my_plugin.apps.MyPluginConfig"
  },

  "requirements": {
    "django": ">=5.0",
    "python": ">=3.10",
    "python_packages": ["some_package==1.0.0"]
  },

  "hooks": {
    "file_preview_provider": {
      "handler": "my_plugin.handlers.MyPreviewProvider",
      "priority": 10,
      "mime_types": ["text/my-type"]
    }
  }
}
```

### Step 3: Create Django App Config

**apps.py**:
```python
from django.apps import AppConfig

class MyPluginConfig(AppConfig):
    name = 'my_plugin'

    def ready(self):
        # Register your hooks here
        from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER
        from my_plugin.handlers import MyPreviewProvider

        hook_registry.register(
            FILE_PREVIEW_PROVIDER,
            MyPreviewProvider,
            priority=10,
            mime_type='text/my-type'
        )
```

### Step 4: Implement Preview Provider

**handlers.py**:
```python
from plugins.preview import FilePreviewProvider

class MyPreviewProvider(FilePreviewProvider):

    @property
    def supported_mime_types(self):
        return ['text/my-type']

    def can_preview(self, file_obj):
        return file_obj.mime_type in self.supported_mime_types

    def get_preview_html(self, file_obj):
        # Read file
        with file_obj.file.open('r') as f:
            content = f.read()

        # Convert to HTML
        html = self.convert_to_html(content)

        # Return styled HTML
        return f'<div class="my-preview">{html}</div>'

    def convert_to_html(self, content):
        # Implement your conversion logic
        return content
```

### Step 5: ZIP and Upload

1. Create ZIP file: `my_plugin.zip`
2. Go to Django Admin → Plugins
3. Click "Upload Plugin"
4. Select ZIP file
5. Click "Activate" to enable

## Available Hooks

### MVP (Current)

#### `file_preview_provider`
Provides file preview functionality for specific MIME types.

**Handler signature**:
```python
class MyPreviewProvider(FilePreviewProvider):
    @property
    def supported_mime_types(self):
        return ['mime/type']

    def can_preview(self, file_obj) -> bool:
        pass

    def get_preview_html(self, file_obj) -> str:
        pass
```

**Usage in plugin.json**:
```json
{
  "hooks": {
    "file_preview_provider": {
      "handler": "my_plugin.handlers.MyPreviewProvider",
      "mime_types": ["mime/type"],
      "priority": 10
    }
  }
}
```

### Future (Post-MVP)

- `storage_backend_provider` - S3, Dropbox, etc.
- `ui_dashboard_widget` - Custom dashboard widgets
- `api_endpoint_provider` - Custom API endpoints
- `workflow_step_provider` - Automation workflows

## Example: Markdown Preview Plugin

See `cloudservice/plugins/example_markdown_preview/` for a complete working example.

**Key files**:
- `__init__.py` - Package marker
- `apps.py` - AppConfig with hook registration
- `handlers.py` - MarkdownPreviewProvider implementation
- `plugin.json` - Manifest with requirements

## Security Considerations

### What Plugins Can Do
- ✅ Extend file previews
- ✅ Add new file type handlers
- ✅ Use Django ORM and templates
- ✅ Import Python packages
- ✅ Execute custom code

### Security Precautions
- ❗ Only upload from trusted sources
- ❗ Plugins have full access to Django app and database
- ❗ Always review code before activating
- ❗ Admin-only upload (superuser required)

## Plugin Lifecycle

### Upload
1. ZIP validation (manifest check, syntax validation)
2. Plugin record created in database
3. ZIP extracted to `plugins/installed/{slug}/`
4. Status: `inactive`

### Activation
1. Plugin module imported dynamically
2. AppConfig.ready() called (registers hooks, etc.)
3. Added to INSTALLED_APPS at runtime
4. Status: `active`
5. No server restart needed

### Deactivation
1. All hooks cleared
2. Module removed from INSTALLED_APPS
3. Module removed from sys.modules
4. Status: `inactive`
5. No server restart needed

## Debugging

### Check Plugin Status
- Go to Django Admin → Plugins
- See status badge (Active/Inactive/Error)
- Check error message if status is Error
- View operation logs in PluginLog

### View Logs
```bash
# See plugin system logs
python manage.py tail --level=DEBUG | grep -i plugin
```

### Test Plugin Locally
Before uploading:
```bash
# Create test data
python manage.py shell

from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER
from my_plugin.handlers import MyPreviewProvider

# Test instantiation
provider = MyPreviewProvider()
print(provider.supported_mime_types)

# Test preview
from core.models import StorageFile
file_obj = StorageFile.objects.first()
if provider.can_preview(file_obj):
    html = provider.get_preview_html(file_obj)
    print(html)
```

## Dependencies

### Required
- Python >= 3.10
- Django >= 5.0
- CloudService core, storage apps

### Optional
- Any Python packages specified in `plugin.json`

### Installing Dependencies
Currently, manually install packages:
```bash
pip install markdown==3.5.2
```

Future: Auto-install from manifest (post-MVP)

## Plugin Manifest Reference

### Required Fields

```json
{
  "name": "string",           // Display name
  "slug": "string",           // URL identifier (lowercase, hyphens)
  "version": "string",        // SemVer format (e.g., 1.0.0)
  "author": "string",         // Author name
  "description": "string",    // Plugin description
  "django_app": {
    "app_config": "string"    // Full path to AppConfig
  }
}
```

### Optional Fields

```json
{
  "requirements": {
    "django": "string",           // Django version constraint
    "python": "string",           // Python version constraint
    "python_packages": ["array"]  // List of pip packages
  },

  "hooks": {
    "hook_name": {
      "handler": "string",        // Full path to handler class/function
      "priority": 10,             // Lower = higher priority
      "mime_types": ["array"]     // For file_preview_provider
    }
  }
}
```

## Best Practices

1. **Error Handling**
   - Wrap file operations in try-catch
   - Log errors properly
   - Return fallback HTML if conversion fails

2. **Performance**
   - Limit preview size for large files
   - Cache expensive conversions
   - Use async tasks for heavy lifting (future)

3. **Code Quality**
   - Use type hints
   - Add docstrings
   - Follow PEP 8
   - Test thoroughly before upload

4. **Documentation**
   - Include README in plugin ZIP
   - Document configuration options
   - Provide usage examples

## File Upload Limits

- Maximum ZIP size: 100 MB
- Maximum extracted size: 500 MB
- File count limit: 1000 files

## Troubleshooting

### Plugin Won't Activate
1. Check error message in Admin
2. Verify manifest syntax (valid JSON)
3. Check all required files present
4. Verify AppConfig path matches actual class
5. Check Python package dependencies installed

### Preview Not Working
1. Verify MIME types match file type
2. Test `can_preview()` returns True
3. Check `get_preview_html()` produces valid HTML
4. Look for exceptions in logs

### Import Errors
1. Plugin module not found → Check ZIP extraction path
2. Handler not found → Check handler path in plugin.json
3. Dependency missing → Install with pip

## Contributing

To share your plugin with the community:
1. Create GitHub repository
2. Add PLUGIN_DEVELOPMENT_GUIDE.md
3. Document usage clearly
4. Add example usage
5. Share link with community

## Support

For plugin development questions:
- Check example plugin: `cloudservice/plugins/example_markdown_preview/`
- Review API in `cloudservice/plugins/preview.py`
- Check plugin logs in Admin interface

---

**Happy plugin development!** 🚀

Remember: Plugins make CloudService extensible. Share your creations with the community!
