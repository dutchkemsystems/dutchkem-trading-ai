"""
Management command: populate_celery_schedule
============================================
Loads the Celery Beat schedule from celery_schedule.py into the
django_celery_beat DatabaseScheduler on first deploy.

Usage:
    python manage.py populate_celery_schedule
    python manage.py populate_celery_schedule --clear   # Remove all existing, then load
    python manage.py populate_celery_schedule --dry-run  # Preview without saving
"""

import importlib
import logging
import sys

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

logger = logging.getLogger("celery")

# Import the schedule definitions
celery_schedule_module = importlib.import_module("config.celery_schedule")
CELERY_BEAT_SCHEDULE = celery_schedule_module.CELERY_BEAT_SCHEDULE


class Command(BaseCommand):
    help = (
        "Populate the Django Celery Beat DatabaseScheduler with tasks "
        "from config.celery_schedule.CELERY_BEAT_SCHEDULE"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove ALL existing periodic tasks before loading",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without saving",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        # ── Clear existing tasks ──────────────────────────────────────────────
        if clear:
            count = PeriodicTask.objects.count()
            if dry_run:
                self.stdout.write(f"Would remove {count} existing periodic tasks")
            else:
                PeriodicTask.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"Removed {count} existing periodic tasks"))

        # ── Create or get interval schedules ──────────────────────────────────
        interval_cache = {}

        def get_or_create_interval(every, period):
            key = (every, period)
            if key not in interval_cache:
                if dry_run:
                    interval_cache[key] = f"interval({every} {period})"
                else:
                    obj, _ = IntervalSchedule.objects.get_or_create(
                        every=every,
                        period=period,
                    )
                    interval_cache[key] = obj
            return interval_cache[key]

        # Map seconds to IntervalSchedule periods
        def seconds_to_interval(seconds):
            if seconds < 60:
                return get_or_create_interval(int(seconds), IntervalSchedule.SECONDS)
            elif seconds < 3600:
                return get_or_create_interval(int(seconds) // 60, IntervalSchedule.MINUTES)
            elif seconds < 86400:
                return get_or_create_interval(int(seconds) // 3600, IntervalSchedule.HOURS)
            else:
                return get_or_create_interval(int(seconds) // 86400, IntervalSchedule.DAYS)

        # ── Create or get crontab schedules ───────────────────────────────────
        crontab_cache = {}

        def get_or_create_crontab(crontab_obj):
            """Convert a celery.schedules.crontab to a django_celery_beat CrontabSchedule."""
            minute = str(crontab_obj._orig_minute) if hasattr(crontab_obj, '_orig_minute') else '*'
            hour = str(crontab_obj._orig_hour) if hasattr(crontab_obj, '_orig_hour') else '*'
            day_of_week = str(crontab_obj._orig_day_of_week) if hasattr(crontab_obj, '_orig_day_of_week') else '*'
            day_of_month = str(crontab_obj._orig_day_of_month) if hasattr(crontab_obj, '_orig_day_of_month') else '*'
            month_of_year = str(crontab_obj._orig_month_of_year) if hasattr(crontab_obj, '_orig_month_of_year') else '*'

            key = (minute, hour, day_of_week, day_of_month, month_of_year)
            if key not in crontab_cache:
                if dry_run:
                    crontab_cache[key] = f"crontab({minute} {hour} {day_of_week} {day_of_month} {month_of_year})"
                else:
                    obj, _ = CrontabSchedule.objects.get_or_create(
                        minute=minute,
                        hour=hour,
                        day_of_week=day_of_week,
                        day_of_month=day_of_month,
                        month_of_year=month_of_year,
                    )
                    crontab_cache[key] = obj
            return crontab_cache[key]

        # ── Load tasks ────────────────────────────────────────────────────────
        created = 0
        skipped = 0
        errors = 0

        for task_name, task_config in CELERY_BEAT_SCHEDULE.items():
            schedule = task_config["schedule"]
            task_path = task_config["task"]
            args = task_config.get("args", ())
            kwargs = task_config.get("kwargs", {})

            # Determine schedule type
            if isinstance(schedule, (int, float)):
                # Interval schedule (seconds)
                schedule_obj = seconds_to_interval(schedule)
                crontab = None
            else:
                # Crontab schedule
                schedule_obj = None
                crontab = get_or_create_crontab(schedule)

            if dry_run:
                sched_type = schedule_obj or crontab
                self.stdout.write(
                    f"  {'CREATE' if not PeriodicTask.objects.filter(name=task_name).exists() else 'UPDATE'}: "
                    f"{task_name} -> {task_path} ({sched_type})"
                )
                continue

            # Create or update the periodic task
            try:
                obj, was_created = PeriodicTask.objects.update_or_create(
                    name=task_name,
                    defaults={
                        "task": task_path,
                        "args": str(list(args)) if args else "[]",
                        "kwargs": str(kwargs) if kwargs else "{}",
                        "interval": schedule_obj,
                        "crontab": crontab,
                        "enabled": True,
                    },
                )
                if was_created:
                    created += 1
                    self.stdout.write(f"  + Created: {task_name}")
                else:
                    skipped += 1
                    self.stdout.write(f"  ~ Updated: {task_name}")
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(f"  ! Error creating {task_name}: {e}"))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete — no changes made"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done: {created} created, {skipped} updated, {errors} errors, "
                f"{len(CELERY_BEAT_SCHEDULE)} total tasks"
            ))
