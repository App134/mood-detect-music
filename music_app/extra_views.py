from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json

from .models import Song, LikedSong, UserProfile
from .youtube_api import YouTubeAPI


@login_required(login_url='login')
def player_page(request, song_id):
    """Dedicated player page with controls and seek support"""
    user_profile = UserProfile.objects.get(user=request.user)
    song = get_object_or_404(Song, id=song_id)
    is_liked = LikedSong.objects.filter(user=request.user, song=song).exists()
    
    # Get previous and next songs (same mood and language)
    prev_song = Song.objects.filter(
        mood=song.mood,
        language=song.language,
        audio_file__isnull=False
    ).exclude(audio_file__exact='').filter(
        id__lt=song.id
    ).order_by('-id').first()
    
    next_song = Song.objects.filter(
        mood=song.mood,
        language=song.language,
        audio_file__isnull=False
    ).exclude(audio_file__exact='').filter(
        id__gt=song.id
    ).order_by('id').first()
    
    return render(request, 'player.html', {
        'user_profile': user_profile,
        'song': song,
        'is_liked': is_liked,
        'prev_song': prev_song,
        'next_song': next_song
    })


@login_required(login_url='login')
def liked_songs(request):
    """List user's liked songs"""
    user_profile = UserProfile.objects.get(user=request.user)
    liked = LikedSong.objects.filter(user=request.user).select_related('song')
    return render(request, 'liked_songs.html', {
        'user_profile': user_profile,
        'liked_songs': liked
    })


@login_required(login_url='login')
@require_POST
def toggle_like(request):
    """Toggle like/unlike for a given song (AJAX)"""
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        song = get_object_or_404(Song, id=song_id)
        obj, created = LikedSong.objects.get_or_create(user=request.user, song=song)
        if not created:
            obj.delete()
            return JsonResponse({'liked': False})
        return JsonResponse({'liked': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
