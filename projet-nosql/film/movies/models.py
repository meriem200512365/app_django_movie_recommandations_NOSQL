from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    title = models.CharField(max_length=255)
    year = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text='Duration in minutes')
    poster = models.ImageField(upload_to='posters/', null=True, blank=True)
    poster_url = models.URLField(null=True, blank=True, help_text='URL to poster image')
    description = models.TextField(blank=True, null=True)
    genres = models.ManyToManyField('Genre', blank=True, related_name='movies')
    tags = models.ManyToManyField('Tag', blank=True, related_name='movies')

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='ratings')
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='in_watchlists')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')


class SyncLog(models.Model):
    STATUS_CHOICES = (
        ('started', 'Started'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    message = models.TextField(blank=True)
    triggered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Sync {self.started_at.isoformat()} - {self.status}"
