from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='NodeHealth',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('node_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('host', models.CharField(max_length=255)),
                ('port', models.IntegerField(default=14222)),
                ('status', models.CharField(choices=[('active', 'Active'), ('standby', 'Standby'), ('failed', 'Failed'), ('recovering', 'Recovering')], default='standby', max_length=20)),
                ('cpu_usage', models.FloatField(default=0.0, help_text='CPU usage percentage')),
                ('memory_usage', models.FloatField(default=0.0, help_text='Memory usage percentage')),
                ('disk_usage', models.FloatField(default=0.0, help_text='Disk usage percentage')),
                ('network_latency_ms', models.FloatField(default=0.0, help_text='Network latency in milliseconds')),
                ('last_heartbeat', models.DateTimeField(auto_now=True)),
                ('heartbeat_count', models.IntegerField(default=0)),
                ('missed_heartbeats', models.IntegerField(default=0)),
                ('failover_count', models.IntegerField(default=0)),
                ('load_score', models.FloatField(default=0.0)),
                ('error_message', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-last_heartbeat'],
                'indexes': [
                    models.Index(fields=['node_id', 'status'], name='infra_node_id_status_idx'),
                    models.Index(fields=['status', 'last_heartbeat'], name='infra_status_heartbeat_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='FailoverEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('node_failure', 'Node Failure'), ('leader_election', 'Leader Election'), ('broker_failover', 'Broker Failover'), ('mt5_reconnect', 'MT5 Reconnect'), ('isp_failover', 'ISP Failover'), ('power_event', 'Power Event'), ('manual_failover', 'Manual Failover'), ('recovery', 'Recovery')], db_index=True, max_length=50)),
                ('source_node', models.CharField(blank=True, default='', max_length=100)),
                ('target_node', models.CharField(blank=True, default='', max_length=100)),
                ('severity', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error'), ('CRITICAL', 'Critical')], default='INFO', max_length=10)),
                ('description', models.TextField()),
                ('duration_seconds', models.FloatField(default=0.0)),
                ('success', models.BooleanField(default=True)),
                ('error_message', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['event_type', 'created_at'], name='infra_event_created_idx'),
                    models.Index(fields=['severity', 'created_at'], name='infra_severity_created_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='AlertLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('level', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error'), ('CRITICAL', 'Critical')], db_index=True, max_length=10)),
                ('channel', models.CharField(choices=[('email', 'Email'), ('telegram', 'Telegram'), ('slack', 'Slack'), ('webhook', 'Webhook')], db_index=True, max_length=20)),
                ('subject', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('recipient', models.CharField(blank=True, default='', max_length=255)),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('failed', 'Failed'), ('pending', 'Pending')], default='sent', max_length=10)),
                ('error_message', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('sent_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'ordering': ['-sent_at'],
                'indexes': [
                    models.Index(fields=['level', 'sent_at'], name='infra_alert_level_idx'),
                    models.Index(fields=['channel', 'status'], name='infra_alert_channel_idx'),
                ],
            },
        ),
    ]
