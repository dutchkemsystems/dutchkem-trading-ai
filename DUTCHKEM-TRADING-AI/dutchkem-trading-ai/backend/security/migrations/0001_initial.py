import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockedIP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ip_address', models.GenericIPAddressField(db_index=True, unique=True)),
                ('reason', models.CharField(blank=True, default='', max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('blocked_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('threat_level', models.IntegerField(default=3)),
                ('blocked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blocked_ips', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-blocked_at'],
            },
        ),
        migrations.CreateModel(
            name='SecurityEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(db_index=True, max_length=100)),
                ('threat_level', models.IntegerField(default=0)),
                ('user_id', models.CharField(blank=True, default='', max_length=100)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('details', models.JSONField(blank=True, default=dict)),
                ('endpoint', models.CharField(blank=True, default='', max_length=500)),
                ('method', models.CharField(blank=True, default='', max_length=10)),
                ('action_taken', models.CharField(default='allowed', max_length=50)),
                ('event_hash', models.CharField(blank=True, default='', max_length=64)),
                ('previous_hash', models.CharField(blank=True, default='', max_length=64)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['event_type', 'timestamp'], name='security_ev_event__b0d5c7_idx'),
                    models.Index(fields=['ip_address', 'timestamp'], name='security_ev_ip_addr_a1b2c3_idx'),
                    models.Index(fields=['user_id', 'timestamp'], name='security_ev_user_id_c4d5e6_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='EncryptionKey',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.PositiveIntegerField(db_index=True, unique=True)),
                ('encrypted_key', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-version'],
            },
        ),
        migrations.CreateModel(
            name='CredentialVault',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('credential_type', models.CharField(default='secret', max_length=50)),
                ('encrypted_value', models.BinaryField()),
                ('value_hash', models.CharField(blank=True, default='', max_length=64)),
                ('description', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('rotated_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('last_accessed', models.DateTimeField(blank=True, null=True)),
                ('access_count', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
