from django.db import models
import datetime
from django.utils import timezone


class Sport(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"


class HealthcareProvider(models.Model):
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
    # Which healthcare provider did they interact with?
    healthcare_provider = models.ForeignKey(HealthcareProvider, on_delete=models.PROTECT, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Semester and week (1-16) determination based on `created_at`.
    SEMESTER_CHOICES = [
        ('Spring', 'Spring'),
        ('Fall', 'Fall'),
    ]

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='Spring')
    week = models.PositiveSmallIntegerField(null=True, blank=True)

    # Auto-determine semester from created_at when saving.
    # Logic:
    #  - Jan-May  -> Spring
    #  - Jun-Dec  -> Fall
    # Week is now manually selected by the student (1-16).
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
        else:
            # No Summer semester: treat June..December as Fall
            semester_name = 'Fall'

        # Only update semester if it changed
        if self.semester != semester_name:
            self.semester = semester_name
            super().save(update_fields=['semester'])

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.sport} ({self.created_at.date()})"

