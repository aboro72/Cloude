# Testing the Clock Preview Plugin

Complete testing guide for the CloudService Plugin System using the Clock Preview test plugin.

---

## Quick Start (5 minutes)

### Prerequisites
- Server running: `python manage.py runserver`
- Admin user created: `python manage.py create_demo_users`
- Login to admin at: `http://localhost:8000/admin/`

### Test Steps

#### 1. Navigate to Plugins Section
```
1. Go to: http://localhost:8000/admin/plugins/
2. Should see "Plugins" and "Plugin Logs" sections
3. Should see "Upload Plugin" button
4. Plugin list should be empty (or show existing plugins)
```

#### 2. Upload Clock Plugin
```
1. Click "Upload Plugin" button
2. Select file: cloudservice/plugins/clock-preview.zip
3. Click "Upload"
4. Should see success message: "Plugin 'Analog Clock Preview' uploaded"
5. Should see new plugin in list with status "Inactive"
```

#### 3. Verify Plugin Details
```
1. Click on "Analog Clock Preview" plugin name
2. Verify fields:
   - Name: Analog Clock Preview ✓
   - Slug: clock-preview ✓
   - Version: 1.0.0 ✓
   - Author: CloudService Team ✓
   - Status: Inactive ✓
   - Enabled: [unchecked] ✓
   - Manifest (JSON): Should show full plugin.json content ✓
```

#### 4. Activate Plugin (Hot-Loading Test!) 🚀
```
1. Back to plugin list
2. Click "Activate" button on Clock Preview plugin
3. Status should change to "Active" IMMEDIATELY
4. Enabled should be checked
5. ⭐ NO SERVER RESTART NEEDED! ⭐
6. Check console for any errors (should be none)
```

#### 5. Test Clock Preview in File
```
1. Go to Storage → Files: http://localhost:8000/storage/files/
2. Create a new test file:
   - Name: test-clock.clock
   - Description: Test file for clock preview
3. Go to file detail page
4. Should see animated analog clock with:
   - ✓ Clock face with numbers 1-12
   - ✓ Hour hand (shorter)
   - ✓ Minute hand (longer)
   - ✓ Second hand (red, moving every second)
   - ✓ Center dot
   - ✓ Digital time below (HH:MM:SS)
   - ✓ Purple gradient background
   - ✓ Beautiful styling
5. Watch for 5+ seconds - second hand should move every second
```

#### 6. Check Plugin Logs
```
1. Go to Admin → Plugins → Plugin Logs
2. Should see entries:
   - "uploaded" - When plugin was uploaded
   - "activated" - When plugin was activated
3. Each log should show:
   - Plugin: Analog Clock Preview
   - Action: uploaded / activated
   - User: [your admin user]
   - Message: [descriptive text]
   - Created at: [timestamp]
```

#### 7. Deactivate Plugin
```
1. Back to plugins list
2. Click "Deactivate" button
3. Status should change to "Inactive"
4. Enabled should be unchecked
5. ⭐ NO SERVER RESTART NEEDED! ⭐
6. Check PluginLog - should see "deactivated" entry
```

#### 8. Verify Deactivation
```
1. Go back to test-clock.clock file
2. Clock preview should NO LONGER SHOW
3. Should see default file preview instead
4. This proves hot-unloading worked!
```

---

## Detailed Test Results Checklist

### ✅ Plugin Upload
- [ ] Can navigate to Admin → Plugins
- [ ] "Upload Plugin" button exists and works
- [ ] Can select clock-preview.zip from cloudservice/plugins/
- [ ] Upload succeeds with success message
- [ ] Plugin appears in list with "Inactive" status

### ✅ Plugin Details
- [ ] Plugin name is "Analog Clock Preview"
- [ ] Slug is "clock-preview"
- [ ] Version is "1.0.0"
- [ ] Author is "CloudService Team"
- [ ] Description is visible
- [ ] Manifest JSON is displayed correctly

### ✅ Hot-Loading Activation
- [ ] "Activate" button works
- [ ] Status changes to "Active" immediately
- [ ] Enabled checkbox is checked
- [ ] NO server restart is needed
- [ ] No errors in console
- [ ] PluginLog shows "activated" entry
- [ ] User field shows correct admin user

### ✅ Clock Preview Display
- [ ] Clock appears on test-clock.clock file detail
- [ ] Clock has numbers 1-12 on face
- [ ] Hour hand is visible
- [ ] Minute hand is visible
- [ ] Second hand is visible and RED
- [ ] Center dot is visible
- [ ] Digital time displays (HH:MM:SS format)
- [ ] Background has purple gradient
- [ ] Styling is professional and clean

### ✅ Real-Time Animation
- [ ] Watch for 10 seconds
- [ ] Second hand moves every second
- [ ] Minute hand moves smoothly
- [ ] Hour hand moves smoothly
- [ ] Digital time updates every second
- [ ] All hands move in correct direction (clockwise)

### ✅ Hot-Loading Deactivation
- [ ] "Deactivate" button works
- [ ] Status changes to "Inactive" immediately
- [ ] Enabled checkbox is unchecked
- [ ] NO server restart is needed
- [ ] PluginLog shows "deactivated" entry

### ✅ Deactivation Verification
- [ ] Clock NO LONGER appears on test-clock.clock page
- [ ] File shows default preview instead
- [ ] Proves the plugin was actually unloaded

---

## What This Tests

This test verifies all critical plugin system functionality:

1. **ZIP Upload**: Validates ZIP structure, extracts files ✓
2. **Database**: Stores plugin metadata correctly ✓
3. **Hot-Loading**: Dynamically loads plugin without restart ✓
4. **AppConfig**: Plugin's ready() method executes ✓
5. **Hook Registration**: Plugin registers handlers with hook_registry ✓
6. **File Preview Integration**: Checks hooks when rendering file ✓
7. **MIME Type Routing**: Routes to correct handler by MIME type ✓
8. **Hot-Unloading**: Cleans up plugin resources ✓
9. **Audit Logging**: Records all operations ✓

---

## Troubleshooting

### Problem: Upload Button Not Found
**Solution**: Make sure Admin panel is accessible at `http://localhost:8000/admin/` and you're logged in as superuser.

### Problem: ZIP File Not Found
**Solution**: ZIP is located at: `C:\Users\aborowczak\PycharmProjects\Cloude\cloudservice\plugins\clock-preview.zip`

### Problem: Upload Shows Error "Missing plugin.json"
**Solution**: ZIP file is corrupted. Delete and recreate:
```powershell
cd C:\Users\aborowczak\PycharmProjects\Cloude\cloudservice\plugins
Remove-Item clock-preview.zip
Compress-Archive -Path example_clock_preview -DestinationPath clock-preview.zip
```

### Problem: Clock Doesn't Appear After Activation
**Possible Causes**:
1. File MIME type might be wrong - check file.mime_type in database
2. Plugin not actually activated - refresh page and check Admin
3. Cache issue - try CTRL+F5 (hard refresh) in browser
4. Console errors - check browser DevTools (F12) for JavaScript errors

**Debug Steps**:
1. Go to Django shell: `python manage.py shell`
2. Check plugin status: `from plugins.models import Plugin; Plugin.objects.all()`
3. Check hooks: `from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER; hook_registry.get_handlers(FILE_PREVIEW_PROVIDER)`

### Problem: Server Restarted During Activation
**Expected**: This should NOT happen - that's the whole point of hot-loading!
- If it did, check server logs for exceptions
- Post log output to understand the error

### Problem: Clock Appears But Hands Don't Move
**Possible Cause**: JavaScript issue
**Solution**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Should be no errors
4. Check if animation is running: `document.getElementById('second').style.transform`

---

## Expected Output

### Admin → Plugins List
```
Name                      Version  Status   Enabled  Uploaded
-----------------------------------------------------------
Analog Clock Preview      1.0.0    Active   ✓       [date]
Markdown File Preview     1.0.0    Active   ✓       [date]
```

### File Detail Page (with Clock plugin active)
```
┌─────────────────────────────────────────┐
│        Test Clock File Preview          │
├─────────────────────────────────────────┤
│                                         │
│            [ANIMATED CLOCK]             │
│        with moving second hand          │
│      showing current time visually      │
│                                         │
│            14:35:42 (digital)           │
│                                         │
└─────────────────────────────────────────┘
```

---

## Success Criteria

All of the following should be true after testing:

1. ✅ Clock plugin uploaded successfully
2. ✅ Clock plugin activated without server restart
3. ✅ Animated clock displays on file preview
4. ✅ Clock hands move in real-time
5. ✅ Plugin deactivated without server restart
6. ✅ Clock no longer displays after deactivation
7. ✅ All operations logged to PluginLog
8. ✅ No errors in console or server logs

If all 8 criteria are met, **the plugin system is working correctly!** 🎉

---

## Next Steps After Testing

### If All Tests Pass ✅
1. Plugin system is MVP-complete and verified
2. Can now create more plugins using similar structure
3. Can document plugin API for community developers
4. Ready for production use with testing

### If Tests Fail ❌
1. Check error messages carefully
2. Review logs at: Django console output
3. Check database state: `python manage.py shell`
4. Review implementation files in: `cloudservice/plugins/`
5. Refer to PLUGIN_SYSTEM_IMPLEMENTATION_LOG.md for technical details

---

## Documentation References

- **Implementation Details**: `PLUGIN_SYSTEM_IMPLEMENTATION_LOG.md`
- **Developer Guide**: `PLUGIN_DEVELOPMENT_GUIDE.md`
- **Implementation Status**: `IMPLEMENTATION_COMPLETE.txt`
- **Plan File**: `C:\Users\aborowczak\.claude\plans\deep-bouncing-porcupine.md`

---

**Test Date**: [Complete this with current date/time]
**Tester**: [Your name]
**Result**: ✅ PASS / ❌ FAIL
**Notes**: [Any observations or issues]

---

Happy testing! 🚀 The Clock will be ticking in your plugin system soon!
