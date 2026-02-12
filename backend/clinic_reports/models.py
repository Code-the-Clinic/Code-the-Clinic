from django.db import models

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

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.sport} ({self.created_at.date()})"

