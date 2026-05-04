import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0006_company_landing_fields'),
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_type', models.CharField(
                    choices=[('channel', 'Channel'), ('direct', 'Direct Message'), ('group', 'Group Chat')],
                    db_index=True, default='channel', max_length=20, verbose_name='Room type',
                )),
                ('name', models.CharField(max_length=150, verbose_name='Name')),
                ('slug', models.SlugField(max_length=150, verbose_name='Slug')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('is_private', models.BooleanField(default=False, verbose_name='Private')),
                ('is_archived', models.BooleanField(db_index=True, default=False, verbose_name='Archived')),
                ('video_enabled', models.BooleanField(default=False, verbose_name='Video conferencing enabled')),
                ('video_provider', models.CharField(blank=True, max_length=50, verbose_name='Video provider')),
                ('video_room_id', models.CharField(blank=True, max_length=255, verbose_name='Video room ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chat_rooms', to='accounts.company', verbose_name='Company',
                )),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_rooms', to=settings.AUTH_USER_MODEL, verbose_name='Created by',
                )),
                ('guest_companies', models.ManyToManyField(
                    blank=True, related_name='guest_rooms', to='accounts.company', verbose_name='Guest companies',
                )),
            ],
            options={'verbose_name': 'Chat Room', 'verbose_name_plural': 'Chat Rooms', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='ChatMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('owner', 'Owner'), ('admin', 'Admin'), ('member', 'Member')],
                    default='member', max_length=20, verbose_name='Role',
                )),
                ('joined_at', models.DateTimeField(auto_now_add=True, verbose_name='Joined at')),
                ('last_read_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Last read at')),
                ('is_muted', models.BooleanField(default=False, verbose_name='Muted')),
                ('room', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships', to='messenger.chatroom', verbose_name='Room',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messenger_memberships', to=settings.AUTH_USER_MODEL, verbose_name='User',
                )),
            ],
            options={'verbose_name': 'Chat Membership', 'verbose_name_plural': 'Chat Memberships'},
        ),
        migrations.AddField(
            model_name='chatroom',
            name='members',
            field=models.ManyToManyField(
                related_name='chat_rooms', through='messenger.ChatMembership',
                to=settings.AUTH_USER_MODEL, verbose_name='Members',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='chatroom',
            unique_together={('company', 'slug')},
        ),
        migrations.AlterUniqueTogether(
            name='chatmembership',
            unique_together={('room', 'user')},
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_type', models.CharField(
                    choices=[('text', 'Text'), ('file', 'File'), ('system', 'System'), ('call_invite', 'Call Invite')],
                    db_index=True, default='text', max_length=20, verbose_name='Type',
                )),
                ('content', models.TextField(blank=True, verbose_name='Content')),
                ('reactions', models.JSONField(default=dict, verbose_name='Reactions')),
                ('is_edited', models.BooleanField(default=False, verbose_name='Edited')),
                ('edited_at', models.DateTimeField(blank=True, null=True, verbose_name='Edited at')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, verbose_name='Deleted')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Sent at')),
                ('room', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages', to='messenger.chatroom', verbose_name='Room',
                )),
                ('author', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='chat_messages', to=settings.AUTH_USER_MODEL, verbose_name='Author',
                )),
                ('reply_to', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='replies', to='messenger.chatmessage', verbose_name='Reply to',
                )),
                ('storage_file', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='chat_attachments', to='core.storagefile', verbose_name='Attached file',
                )),
            ],
            options={
                'verbose_name': 'Chat Message',
                'verbose_name_plural': 'Chat Messages',
                'ordering': ['created_at'],
                'indexes': [
                    models.Index(fields=['room', 'created_at'], name='messenger_c_room_id_idx'),
                    models.Index(fields=['room', 'is_deleted'], name='messenger_c_room_del_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ChatInvite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invited_email', models.EmailField(blank=True, verbose_name='Invited email')),
                ('token', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True, verbose_name='Token')),
                ('max_uses', models.PositiveSmallIntegerField(default=1, verbose_name='Max uses')),
                ('use_count', models.PositiveSmallIntegerField(default=0, verbose_name='Use count')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Expires at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('room', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invites', to='messenger.chatroom', verbose_name='Room',
                )),
                ('invited_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sent_chat_invites', to=settings.AUTH_USER_MODEL, verbose_name='Invited by',
                )),
            ],
            options={'verbose_name': 'Chat Invite', 'verbose_name_plural': 'Chat Invites', 'ordering': ['-created_at']},
        ),
    ]
