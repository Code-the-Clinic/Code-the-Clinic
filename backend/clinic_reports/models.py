from django.db import models
import datetime
from django.utils import timezone


class Sport(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"


class ClinicReport(models.Model):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    sport = models.ForeignKey(Sport, on_delete=models.PROTECT)
    
    # Patient categories
    immediate_emergency_care = models.IntegerField()
    musculoskeletal_exam = models.IntegerField()
    non_musculoskeletal_exam = models.IntegerField()
    taping_bracing = models.IntegerField()
    rehabilitation_reconditioning = models.IntegerField()
    modalities = models.IntegerField()
    pharmacology = models.IntegerField()
    injury_illness_prevention = models.IntegerField()
    non_sport_patient = models.IntegerField()
    # Did the student interact with other healthcare providers this week?
    interacted_hcps = models.BooleanField(default=False,
                                          verbose_name="Interacted with other Health Care Professionals this week?")
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Semester and week (1-16) determination based on `created_at`.
    SEMESTER_CHOICES = [
        ('Spring', 'Spring'),
        ('Fall', 'Fall'),
    ]

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='Spring')
    week = models.PositiveSmallIntegerField(null=True, blank=True)

    # Determine semester and week (1-16) from created_at when saving.
    # Logic:
    #  - Jan-May  -> Spring (start Jan 1)
    #  - Aug-Dec  -> Fall   (start Aug 1)
    # Week is clamped to range 1..16.
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        # First ensure instance has a created_at value by saving once if new.
        if is_new:
            super().save(*args, **kwargs)

        created = self.created_at or timezone.now()
        year = created.year
        month = created.month

        if 1 <= month <= 5:
            semester_name = 'Spring'
            start_date = datetime.date(year, 1, 1)
        else:
            # No Summer semester: treat June..December as Fall
            semester_name = 'Fall'
            start_date = datetime.date(year, 6, 1)

        # Determine week as the student's nth submission in this semester.
        # Use the created date window (start_date .. semester end) to find prior reports
        if semester_name == 'Spring':
            end_date = datetime.date(year, 5, 31)
        else:
            end_date = datetime.date(year, 12, 31)

        # Count prior reports by the same student (identified by email) in this semester
        prior_count = ClinicReport.objects.filter(
            email=self.email,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            created_at__lt=created
        ).exclude(pk=self.pk).count()

        computed_week = prior_count + 1
        # Clamp week to 1..16
        computed_week = max(1, min(16, computed_week))

        changed = False
        if self.semester != semester_name:
            self.semester = semester_name
            changed = True
        if self.week != computed_week:
            self.week = computed_week
            changed = True

        if changed:
            super().save(update_fields=['semester', 'week'])

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.sport} ({self.created_at.date()})"

