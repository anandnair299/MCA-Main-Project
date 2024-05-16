from django.db import models

# Create your models here.

class CarEntry(models.Model):
    license_plate = models.CharField(max_length=255)
    entry_time = models.DateTimeField()

    def __str__(self):
        return f"{self.license_plate} - {self.entry_time}"