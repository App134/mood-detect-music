from django.contrib import admin
from .models import UserProfile, Song, PlaylistHistory, UserPreferences

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_language', 'created_at')
    list_filter = ('preferred_language',)
    search_fields = ('user__username',)

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'mood', 'language', 'has_audio_file', 'has_thumbnail', 'created_at')
    list_filter = ('mood', 'language', 'created_at')
    search_fields = ('title', 'artist', 'youtube_id')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'artist', 'description')
        }),
        ('Audio File (Upload Local Audio)', {
            'fields': ('audio_file',),
            'description': 'Upload an MP3, WAV, or OGG file. If you upload an audio file, you can leave YouTube ID blank.'
        }),
        ('Thumbnail/Album Art', {
            'fields': ('thumbnail_image', 'thumbnail_url'),
            'description': 'Upload a local image (JPG/PNG) OR provide a URL. Local image takes priority if both provided.'
        }),
        ('YouTube Integration (Optional)', {
            'fields': ('youtube_id',),
            'description': 'Leave blank if using manual audio file upload.'
        }),
        ('Lyrics (Optional)', {
            'fields': ('lyrics_url',),
            'description': 'Provide a link to lyrics on Genius.com or other lyrics platform.'
        }),
        ('Metadata', {
            'fields': ('mood', 'language', 'duration')
        }),
    )
    
    def has_audio_file(self, obj):
        return bool(obj.audio_file)
    has_audio_file.boolean = True
    has_audio_file.short_description = 'Has Audio'
    
    def has_thumbnail(self, obj):
        return bool(obj.thumbnail_image or obj.thumbnail_url)
    has_thumbnail.boolean = True
    has_thumbnail.short_description = 'Has Thumbnail'

@admin.register(PlaylistHistory)
class PlaylistHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'emotion_detected', 'played_at')
    list_filter = ('emotion_detected', 'played_at')
    search_fields = ('user__username', 'song__title')

@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'favorite_moods')
    search_fields = ('user__username',)

