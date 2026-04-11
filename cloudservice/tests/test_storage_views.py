import os
import tempfile
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Model as DjangoModel
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.admin import UserProfileAdminForm
from accounts.models import UserProfile
from departments.models import Company, CompanyInvitation, Department
from core.context_processors import plugin_menu_items
from core.models import StorageFile, StorageFolder
from sharing.models import GroupShare
from sharing.models import TeamSiteNews
from storage.views import build_collabora_token


class StorageViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='storage-test', password='secret123')
        self.company = Company.objects.create(name='Storage GmbH', owner=self.user)
        self.company.admins.add(self.user)
        self.user.user_permissions.add(Permission.objects.get(codename='create_groupshare'))
        self.user.profile.company = self.company
        self.user.profile.save(update_fields=['company'])
        self.client.force_login(self.user)
        self.factory = RequestFactory()
        self.root_folder = StorageFolder.objects.create(
            owner=self.user,
            parent=None,
            name='Cloud',
        )

    def test_root_view_lists_child_folders(self):
        child_folder = StorageFolder.objects.create(
            owner=self.user,
            parent=self.root_folder,
            name='Bilder',
        )

        response = self.client.get(reverse('storage:file_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, child_folder.name)

    def test_home_redirects_authenticated_user_to_storage_when_no_plugin_home_exists(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('storage:file_list'))

    def test_mysite_plugin_url_redirects_to_storage_when_plugin_is_disabled(self):
        response = self.client.get(reverse('core:plugin_app', kwargs={'slug': 'mysite'}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('storage:file_list'))

    def test_disabled_landing_editor_and_mysite_hide_menu_items(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        request = self.factory.get('/')
        request.user = self.user

        items = plugin_menu_items(request)['plugin_menu_items']

        labels = [item['label'] for item in items]
        self.assertNotIn('Landingpage', labels)
        self.assertNotIn('Bereiche', labels)

    def test_groups_list_page_renders(self):
        response = self.client.get(reverse('sharing:groups_list', kwargs={'company_slug': self.company.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team Sites')

    def test_create_group_creates_team_site_library_and_redirects_to_detail(self):
        response = self.client.post(
            reverse('sharing:create_group', kwargs={'company_slug': self.company.slug}),
            {
                'company': self.company.id,
                'group_name': 'Projekt Alpha',
                'members': [self.user.id],
            },
        )

        group = GroupShare.objects.get(group_name='Projekt Alpha')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('sharing:group_detail', kwargs={'company_slug': self.company.slug, 'group_id': group.id}))
        self.assertEqual(group.permission, 'admin')
        self.assertEqual(group.content_object.name, 'Projekt Alpha')
        self.assertEqual(group.company, self.company)

    def test_group_detail_page_renders(self):
        team_library = StorageFolder.objects.create(
            owner=self.user,
            parent=None,
            name='Team Docs',
        )
        group = GroupShare.objects.create(
            owner=self.user,
            company=self.company,
            group_name='Team Docs',
            content_type=ContentType.objects.get_for_model(StorageFolder),
            object_id=team_library.id,
            permission='admin',
        )
        group.members.add(self.user)

        response = self.client.get(reverse('sharing:group_detail', kwargs={'company_slug': self.company.slug, 'group_id': group.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zusammenarbeitsbereich')
        self.assertContains(response, 'Dokumentbibliothek')
        self.assertContains(response, 'Team Docs')

    def test_team_leader_can_create_team_news(self):
        leader = User.objects.create_user(username='leader', password='secret123')
        leader.profile.company = self.company
        leader.profile.save(update_fields=['company'])
        team_library = StorageFolder.objects.create(
            owner=self.user,
            parent=None,
            name='Leader Docs',
        )
        group = GroupShare.objects.create(
            owner=self.user,
            company=self.company,
            group_name='Leader Team',
            content_type=ContentType.objects.get_for_model(StorageFolder),
            object_id=team_library.id,
            permission='admin',
        )
        group.members.add(self.user, leader)
        group.team_leaders.add(leader)

        self.client.force_login(leader)
        response = self.client.post(
            reverse('sharing:team_news_create', kwargs={'company_slug': self.company.slug, 'group_id': group.id}),
            {
                'title': 'Sprint Update',
                'summary': 'Kurzstatus',
                'content': 'Team Leader darf diese News anlegen.',
                'is_published': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TeamSiteNews.objects.filter(group=group, title='Sprint Update').exists())

    def test_member_cannot_create_team_news(self):
        member = User.objects.create_user(username='member', password='secret123')
        member.profile.company = self.company
        member.profile.save(update_fields=['company'])
        team_library = StorageFolder.objects.create(
            owner=self.user,
            parent=None,
            name='Member Docs',
        )
        group = GroupShare.objects.create(
            owner=self.user,
            company=self.company,
            group_name='Member Team',
            content_type=ContentType.objects.get_for_model(StorageFolder),
            object_id=team_library.id,
            permission='admin',
        )
        group.members.add(self.user, member)

        self.client.force_login(member)
        response = self.client.post(
            reverse('sharing:team_news_create', kwargs={'company_slug': self.company.slug, 'group_id': group.id}),
            {
                'title': 'Nicht erlaubt',
                'summary': 'x',
                'content': 'x',
                'is_published': 'on',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(TeamSiteNews.objects.filter(group=group, title='Nicht erlaubt').exists())

    def test_folder_view_uses_storage_listing_template(self):
        child_folder = StorageFolder.objects.create(
            owner=self.user,
            parent=self.root_folder,
            name='Videos',
        )

        response = self.client.get(reverse('storage:folder', kwargs={'folder_id': child_folder.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/file_list.html')
        self.assertEqual(response.context['current_folder'], child_folder)

    def test_preview_endpoint_serves_file_inline(self):
        uploaded_file = SimpleUploadedFile(
            'poster.png',
            b'fake-image-bytes',
            content_type='image/png',
        )
        storage_file = StorageFile.objects.create(
            owner=self.user,
            folder=self.root_folder,
            name='poster.png',
            file=uploaded_file,
            mime_type='image/png',
        )

        response = self.client.get(reverse('storage:preview', kwargs={'file_id': storage_file.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('inline;', response['Content-Disposition'])

    def test_preview_endpoint_supports_byte_ranges(self):
        uploaded_file = SimpleUploadedFile(
            'clip.mp4',
            b'0123456789abcdef',
            content_type='video/mp4',
        )
        storage_file = StorageFile.objects.create(
            owner=self.user,
            folder=self.root_folder,
            name='clip.mp4',
            file=uploaded_file,
            mime_type='video/mp4',
        )

        response = self.client.get(
            reverse('storage:preview', kwargs={'file_id': storage_file.id}),
            HTTP_RANGE='bytes=0-3',
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(response['Content-Range'], 'bytes 0-3/16')
        self.assertEqual(response.content, b'0123')

    def test_broken_file_can_be_moved_to_trash(self):
        storage_file = StorageFile(
            owner=self.user,
            folder=self.root_folder,
            name='missing.png',
            mime_type='image/png',
            size=123,
            file_hash='missing-file-hash',
        )
        storage_file.file.name = 'files/missing.png'
        DjangoModel.save(storage_file)

        response = self.client.post(reverse('storage:delete', kwargs={'file_id': storage_file.id}))
        storage_file.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(storage_file.is_trashed)

    def test_broken_trashed_file_can_be_deleted_permanently(self):
        storage_file = StorageFile(
            owner=self.user,
            folder=self.root_folder,
            name='missing.png',
            mime_type='image/png',
            size=123,
            file_hash='missing-file-hash',
            is_trashed=True,
        )
        storage_file.file.name = 'files/missing.png'
        DjangoModel.save(storage_file)

        response = self.client.post(reverse('storage:permanently_delete', kwargs={'file_id': storage_file.id}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(StorageFile.objects.filter(id=storage_file.id).exists())

    def test_folder_can_be_deleted(self):
        child_folder = StorageFolder.objects.create(
            owner=self.user,
            parent=self.root_folder,
            name='Zu loeschen',
        )

        response = self.client.post(reverse('storage:delete_folder', kwargs={'folder_id': child_folder.id}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(StorageFolder.objects.filter(id=child_folder.id).exists())

    def test_file_can_be_moved_to_another_folder(self):
        source_folder = StorageFolder.objects.create(
            owner=self.user,
            parent=self.root_folder,
            name='Quelle',
        )
        target_folder = StorageFolder.objects.create(
            owner=self.user,
            parent=self.root_folder,
            name='Ziel',
        )
        storage_file = StorageFile.objects.create(
            owner=self.user,
            folder=source_folder,
            name='move-me.txt',
            file=SimpleUploadedFile('move-me.txt', b'data', content_type='text/plain'),
            mime_type='text/plain',
        )

        response = self.client.post(
            reverse('storage:move', kwargs={'file_id': storage_file.id}),
            {'folder_id': target_folder.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        storage_file.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(storage_file.folder, target_folder)

    def test_root_folder_cannot_be_deleted(self):
        response = self.client.post(reverse('storage:delete_folder', kwargs={'folder_id': self.root_folder.id}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(StorageFolder.objects.filter(id=self.root_folder.id).exists())

    def test_user_profile_is_registered_in_admin(self):
        self.assertIn(UserProfile, admin.site._registry)

    def test_user_profile_admin_form_accepts_gb_and_mb(self):
        self.assertEqual(UserProfileAdminForm.parse_quota('10 GB'), 10 * 1024 ** 3)
        self.assertEqual(UserProfileAdminForm.parse_quota('500 MB'), 500 * 1024 ** 2)

    def test_user_profile_admin_form_saves_quota(self):
        form = UserProfileAdminForm(
            data={
                'user': self.user.id,
                'role': self.user.profile.role,
                'phone_number': '',
                'bio': '',
                'website': '',
                'language': self.user.profile.language,
                'timezone': self.user.profile.timezone,
                'theme': self.user.profile.theme,
                'design_variant': self.user.profile.design_variant,
                'color_preset': self.user.profile.color_preset,
                'primary_color': self.user.profile.primary_color,
                'secondary_color': self.user.profile.secondary_color,
                'mysite_hero_style': self.user.profile.mysite_hero_style,
                'is_active': 'on',
                'storage_quota_display': '300 GB',
            },
            files={},
            instance=self.user.profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        self.assertEqual(profile.storage_quota, 300 * 1024 ** 3)

    def test_regular_upload_is_blocked_when_quota_is_exceeded(self):
        self.user.profile.storage_quota = 2
        self.user.profile.save(update_fields=['storage_quota'])

        response = self.client.post(
            reverse('storage:upload'),
            {
                'name': 'too-big.txt',
                'file': SimpleUploadedFile('too-big.txt', b'12345', content_type='text/plain'),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StorageFile.objects.filter(owner=self.user, name='too-big.txt').exists())

    def test_chunk_upload_is_blocked_when_quota_is_exceeded(self):
        self.user.profile.storage_quota = 2
        self.user.profile.save(update_fields=['storage_quota'])

        response = self.client.post(
            reverse('storage:upload_chunk'),
            {
                'upload_id': 'quota-test',
                'chunk_index': '0',
                'total_chunks': '1',
                'total_size': '5',
                'filename': 'too-big.bin',
                'chunk': SimpleUploadedFile('chunk.bin', b'12345', content_type='application/octet-stream'),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StorageFile.objects.filter(owner=self.user, name='too-big.bin').exists())

    def test_collabora_office_redirects_for_supported_file(self):
        storage_file = StorageFile.objects.create(
            owner=self.user,
            folder=self.root_folder,
            name='report.docx',
            file=SimpleUploadedFile('report.docx', b'docx-content', content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

        response = self.client.get(reverse('storage:office', kwargs={'file_id': storage_file.id}))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/browser/dist/cool.html', response['Location'])

    def test_wopi_check_file_info_returns_metadata(self):
        storage_file = StorageFile.objects.create(
            owner=self.user,
            folder=self.root_folder,
            name='report.docx',
            file=SimpleUploadedFile('report.docx', b'docx-content', content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        token = build_collabora_token(self.user, storage_file)

        response = self.client.get(
            reverse('storage:wopi_file', kwargs={'file_id': storage_file.id}),
            {'access_token': token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['BaseFileName'], 'report.docx')

    def test_logout_view_allows_get_and_redirects_to_login(self):
        response = self.client.get(reverse('accounts:logout'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))

    def test_logout_view_allows_post_and_redirects_to_login(self):
        response = self.client.post(reverse('accounts:logout'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))

    def test_settings_page_renders_appearance_form(self):
        response = self.client.get(reverse('accounts:settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Design und Farben')
        self.assertContains(response, 'Farbpreset')

    def test_settings_page_saves_custom_appearance(self):
        response = self.client.post(
            reverse('accounts:settings'),
            {
                'theme': 'dark',
                'design_variant': 'contrast',
                'color_preset': 'custom',
                'primary_color': '#112233',
                'secondary_color': '#445566',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:settings'))

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, 'dark')
        self.assertEqual(self.user.profile.design_variant, 'contrast')
        self.assertEqual(self.user.profile.color_preset, 'custom')
        self.assertEqual(self.user.profile.primary_color, '#112233')
        self.assertEqual(self.user.profile.secondary_color, '#445566')

    def test_settings_page_applies_selected_preset_colors(self):
        response = self.client.post(
            reverse('accounts:settings'),
            {
                'theme': 'light',
                'design_variant': 'gradient',
                'color_preset': 'forest',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.color_preset, 'forest')
        self.assertEqual(self.user.profile.primary_color, '#2f855a')
        self.assertEqual(self.user.profile.secondary_color, '#276749')

    def test_settings_page_requires_colors_only_for_custom_preset(self):
        response = self.client.post(
            reverse('accounts:settings'),
            {
                'theme': 'light',
                'design_variant': 'gradient',
                'color_preset': 'custom',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bitte waehlen Sie eine Primaerfarbe.')
        self.assertContains(response, 'Bitte waehlen Sie eine Sekundarfarbe.')

    def test_settings_page_saves_mysite_hero_style(self):
        response = self.client.post(
            reverse('accounts:settings'),
            {
                'theme': 'light',
                'design_variant': 'gradient',
                'color_preset': 'forest',
                'mysite_hero_style': 'gradient',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.mysite_hero_style, 'gradient')

    def test_profile_page_shows_account_overview_sections(self):
        company = Company.objects.create(name='Profil GmbH', owner=self.user)
        department = Department.objects.create(name='Vertrieb', company=company, created_by=self.user)
        self.user.profile.company = company
        self.user.profile.department_ref = department
        self.user.profile.bio = 'Cloud admin'
        self.user.profile.color_preset = 'forest'
        self.user.profile.design_variant = 'contrast'
        self.user.profile.save(update_fields=['company', 'department_ref', 'department', 'bio', 'color_preset', 'design_variant'])

        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Benutzerprofil')
        self.assertContains(response, 'Persoenliche Daten')
        self.assertContains(response, 'Speicher und Nutzung')
        self.assertContains(response, 'Cloud admin')
        self.assertContains(response, 'Profil GmbH')
        self.assertContains(response, 'Vertrieb')

    def test_registration_can_create_new_company(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'newuser',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'password': 'secret1234',
                'company_mode': 'create',
                'company_name': 'Neue Firma GmbH',
                'company_domain': 'neuefirma.test',
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newuser')
        self.assertEqual(user.profile.company.name, 'Neue Firma GmbH')
        self.assertEqual(user.profile.company.owner, user)

    def test_registration_can_join_company_by_domain_when_enabled(self):
        company = Company.objects.create(
            name='Domain GmbH',
            owner=self.user,
            domain='domain.test',
            allow_domain_signup=True,
        )
        company.admins.add(self.user)

        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'domainuser',
                'email': 'joiner@domain.test',
                'first_name': 'Domain',
                'last_name': 'User',
                'password': 'secret1234',
                'company_mode': 'join',
                'company': company.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='domainuser')
        self.assertEqual(user.profile.company, company)

    def test_registration_with_invite_assigns_company_department_and_admin_role(self):
        company = Company.objects.create(name='Invite GmbH', owner=self.user)
        company.admins.add(self.user)
        department = Department.objects.create(name='Support', company=company, created_by=self.user)
        invitation = CompanyInvitation.objects.create(
            company=company,
            email='invitee@example.com',
            invited_by=self.user,
            department=department,
            role='admin',
            expires_at=timezone.now() + timedelta(days=7),
        )

        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'invitee',
                'email': 'invitee@example.com',
                'first_name': 'Invited',
                'last_name': 'Admin',
                'password': 'secret1234',
                'company_mode': 'join',
                'invite_token': invitation.token,
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='invitee')
        invitation.refresh_from_db()
        self.assertEqual(user.profile.company, company)
        self.assertEqual(user.profile.department_ref, department)
        self.assertTrue(company.admins.filter(pk=user.pk).exists())
        self.assertIsNotNone(invitation.accepted_at)
        self.assertFalse(invitation.is_active)

    def test_registration_cannot_join_full_company(self):
        company = Company.objects.create(name='Volle Firma', owner=self.user, employee_limit=1)
        company.admins.add(self.user)
        self.user.profile.company = company
        self.user.profile.save(update_fields=['company'])

        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'blockeduser',
                'email': 'blocked@example.com',
                'first_name': 'Blocked',
                'last_name': 'User',
                'password': 'secret1234',
                'company_mode': 'join',
                'company': company.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hat bereits 1 Mitarbeiter')
        self.assertFalse(User.objects.filter(username='blockeduser').exists())

    def test_company_manager_can_create_invitation(self):
        company = Company.objects.create(name='Onboarding GmbH', owner=self.user)
        company.admins.add(self.user)
        self.user.profile.company = company
        self.user.profile.save(update_fields=['company'])
        department = Department.objects.create(name='People Ops', company=company, created_by=self.user)

        response = self.client.post(
            reverse('departments:company_invite_create', kwargs={'company_slug': company.slug}),
            {
                'email': 'newhire@example.com',
                'role': 'member',
                'department': department.id,
                'expires_at': '2030-01-15T10:00',
            },
        )

        self.assertEqual(response.status_code, 302)
        invitation = CompanyInvitation.objects.get(company=company, email='newhire@example.com')
        self.assertEqual(invitation.department, department)
        self.assertEqual(invitation.invited_by, self.user)

    def test_company_detail_renders_without_owner(self):
        company = Company.objects.create(name='Ownerless GmbH', owner=None)
        company.admins.add(self.user)
        self.user.profile.company = company
        self.user.profile.save(update_fields=['company'])

        response = self.client.get(reverse('departments:company_detail', kwargs={'company_slug': company.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nicht gesetzt')

    def test_department_member_add_respects_company_limit(self):
        company = Company.objects.create(name='Limit GmbH', owner=self.user, employee_limit=1)
        company.admins.add(self.user)
        self.user.profile.company = company
        self.user.profile.save(update_fields=['company'])
        department = Department.objects.create(name='IT', company=company, created_by=self.user)
        outsider = User.objects.create_user(username='outsider', password='secret123')

        response = self.client.post(
            reverse('departments:member_add', kwargs={'company_slug': company.slug, 'slug': department.slug}),
            data='{"user_id": %d, "role": "member"}' % outsider.id,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Limit von 1 Mitarbeitern erreicht', response.json()['error'])

    def test_profile_edit_saves_avatar_upload(self):
        avatar = SimpleUploadedFile(
            'avatar.gif',
            (
                b'GIF89a\x01\x00\x01\x00\x80\x00\x00'
                b'\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,'
                b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif',
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.settings(MEDIA_ROOT=tmpdir):
                response = self.client.post(
                    reverse('accounts:profile_edit'),
                    {
                        'phone_number': '',
                        'bio': '',
                        'website': '',
                        'language': self.user.profile.language,
                        'timezone': self.user.profile.timezone,
                        'theme': self.user.profile.theme,
                        'avatar': avatar,
                    },
                )

                self.assertEqual(response.status_code, 302)
                self.user.profile.refresh_from_db()
                self.assertTrue(bool(self.user.profile.avatar))
                self.assertTrue(os.path.exists(self.user.profile.avatar.path))
