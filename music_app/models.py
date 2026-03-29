from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('ml', 'Malayalam'),
        ('kn', 'Kannada'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class Song(models.Model):
    MOOD_CHOICES = (
        ('happy', 'Happy'),
        ('sad', 'Sad'),
        ('fear', 'Fear'),
        ('surprise', 'Surprise'),
        ('neutral', 'Neutral'),
        ('angry', 'Angry'),
    )
    
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('ml', 'Malayalam'),
        ('kn', 'Kannada'),
    )
    
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    youtube_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    audio_file = models.FileField(upload_to='songs/', null=True, blank=True, help_text='Upload MP3 or other audio format (MP3, WAV, OGG supported)')
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES)
    description = models.TextField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True, help_text='URL to thumbnail image')
    thumbnail_image = models.ImageField(upload_to='thumbnails/', null=True, blank=True, help_text='Upload album art image (JPG, PNG)')
    duration = models.IntegerField(null=True, blank=True, help_text='Duration in seconds')
    lyrics_url = models.URLField(null=True, blank=True, help_text='Link to lyrics (Genius.com, AZLyrics, etc.)')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.artist}"
    
    class Meta:
        ordering = ['-created_at']


class PlaylistHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    emotion_detected = models.CharField(max_length=20)
    played_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.song.title}"
    
    class Meta:
        ordering = ['-played_at']


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    favorite_moods = models.CharField(max_length=100, blank=True)
    favorite_artists = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Preferences"


class LikedSong(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    liked_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} likes {self.song.title}"
    
    class Meta:
        unique_together = ('user', 'song')
        ordering = ['-liked_at']


class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Playlist: {self.name}"

    class Meta:
        ordering = ['-created_at']

    def get_cover_songs(self):
        """Returns the first 4 songs in the playlist for cover generation"""
        return self.songs.all().select_related('song')[:4]


class PlaylistSong(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='songs')
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.song.title} in {self.playlist.name}"

    class Meta:
        unique_together = ('playlist', 'song')
        ordering = ['-added_at']
