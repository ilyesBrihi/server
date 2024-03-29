from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib import admin
from django.utils import timezone
from django.db.models import Avg


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=255, unique=True, null=True)
    github_id = models.CharField(max_length=255, unique=True, null=True)
    image = models.ImageField(upload_to='core/images', blank=True, null=True,max_length=500)
    def clean(self):
        if self.google_id is None and self.github_id is None:
            raise ValidationError("One of google_id or github_id must be set.")
# Address model
class Address(models.Model):
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

# ClientProfile model, using OneToOneField for a one-to-one relationship with User
class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE , related_name='client_profile') 
    age = models.IntegerField()
    gender = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    address = models.ForeignKey(Address, on_delete=models.CASCADE , related_name='client_address')

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'
    
    @admin.display(ordering='user__first_name')
    def first_name(self):
        return self.user.first_name

    @admin.display(ordering='user__last_name')
    def last_name(self):
        return self.user.last_name

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

# LawyerProfile model, using OneToOneField for a one-to-one relationship with User
class LawyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE , related_name='lawyer_profile')
    specialization = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    bio = models.CharField(max_length=255)
    address = models.ForeignKey(Address, on_delete=models.CASCADE , related_name='lawyer_address')
    language = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    rating = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='core/images', blank=True, null=True)

    # def save(self, *args, **kwargs):
    #     # Calculate and update the rating when saving the LawyerProfile instance
    #     reviews_avg = Review.objects.filter(lawyer=self).aggregate(Avg('rating'))['rating__avg']
    #     self.rating = reviews_avg if reviews_avg is not None else 0

    #     super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'
    
    @admin.display(ordering='user__first_name')
    def first_name(self):
        return self.user.first_name

    @admin.display(ordering='user__last_name')
    def last_name(self):
        return self.user.last_name

    class Meta:
        ordering = ['user__first_name', 'user__last_name']
    


# Administrator model, using OneToOneField for a one-to-one relationship with User
class Administrator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

# TimeSlot model
class TimeSlot(models.Model):
    day = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE , related_name='time_slots')

# Appointment model
class Appointment(models.Model):
    day = models.CharField(max_length=255, default=timezone.now) 
    start_time = models.TimeField(default=timezone.now )
    end_time = models.TimeField(default=timezone.now )
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE)
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=255)

# Review model
class Review(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='reviews')
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review for {self.lawyer.user.get_full_name()} by {self.client.user.get_full_name()}'

# LawyerDocument model
class LawyerImage(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='core/images', blank=True, null=True)

    def __str__(self):
        return f"Image for {self.lawyer.user.username}"


class LawyerDocument(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='documents')
    pdf_file = models.FileField(upload_to='core/docs', validators=[FileExtensionValidator(['pdf'])])

    def __str__(self):
        return f"Document for {self.lawyer.user.username}"

