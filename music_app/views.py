from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import SignUpForm, LoginForm, UserProfileForm
from .models import UserProfile, Song, PlaylistHistory, LikedSong
from .youtube_api import YouTubeAPI
from . import emotion_detector
import json
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image


def landing_page(request):
    """Landing page view"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing.html')


def signup_view(request):
    """User registration view - redirect to login after signup"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # UserProfile is automatically created by signals.py
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}. Please log in to continue.')
            return redirect('login')  # Redirect to login page instead of home
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('landing')


@login_required(login_url='login')
def language_selection(request):
    """Language selection view"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Language preference updated!')
            return redirect('home')
    else:
        form = UserProfileForm(instance=user_profile)
    
    return render(request, 'language_selection.html', {'form': form})


@login_required(login_url='login')
def home(request):
    """Home page view"""
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'home.html', {'user_profile': user_profile})


@login_required(login_url='login')
def emotion_detection_page(request):
    """Emotion detection and music recommendation page"""
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'emotion_detection.html', {'user_profile': user_profile})


@login_required(login_url='login')
@require_POST
def detect_emotion(request):
    """AJAX endpoint to detect emotion from uploaded image"""
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Detect emotion (uses ai model if available)
        emotion, mood, confidence = emotion_detector.detect_emotion_from_frame(image_cv)

        # If no face detected, return mood='null' (client can map to neutral/fallback)
        if emotion is None:
            return JsonResponse({
                'emotion': None,
                'mood': 'null',
                'confidence': 0.0
            })

        return JsonResponse({
            'emotion': emotion,
            'mood': mood,
            'confidence': round(confidence, 2)
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='login')
@require_POST
def get_song_recommendations(request):
    """AJAX endpoint to get song recommendations based on mood and language"""
    try:
        import random
        
        data = json.loads(request.body)
        mood = data.get('mood', 'neutral')
        language = data.get('language', 'en')
        
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Map 'null' (no face) to 'neutral' for song search
        search_mood = 'neutral' if mood == 'null' else mood

        # Get songs from database that match BOTH mood and language (must have audio file)
        songs_qs = Song.objects.filter(mood=search_mood, language=language).exclude(audio_file__exact='')
        all_songs = list(songs_qs)
        
        # If no songs in that language, fallback to same mood, any language
        if len(all_songs) == 0:
            songs_qs = Song.objects.filter(mood=search_mood).exclude(audio_file__exact='')
            all_songs = list(songs_qs)
        
        # Randomly select up to 10 songs
        songs = random.sample(all_songs, min(10, len(all_songs))) if len(all_songs) > 0 else []
        
        songs_data = [{
            'id': song.id,
            'title': song.title,
            'artist': song.artist,
            'thumbnail_url': song.thumbnail_url or 'https://via.placeholder.com/200x200?text=MoodMusic',
            'mood': song.mood,
            'language': song.language,
            'youtube_id': song.youtube_id,
            'audio_url': song.audio_file.url if song.audio_file else None
        } for song in songs]
        
        return JsonResponse({'songs': songs_data})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='login')
@require_POST
def play_song(request):
    """AJAX endpoint to log song play history"""
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        emotion_detected = data.get('emotion', 'neutral')
        
        song = get_object_or_404(Song, id=song_id)
        
        PlaylistHistory.objects.create(
            user=request.user,
            song=song,
            emotion_detected=emotion_detected
        )
        
        return JsonResponse({'success': True, 'message': 'Song added to history'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='login')
def playlist_history(request):
    """View user's playlist history"""
    user_profile = UserProfile.objects.get(user=request.user)
    history = PlaylistHistory.objects.filter(user=request.user)
    
    return render(request, 'playlist_history.html', {
        'user_profile': user_profile,
        'history': history
    })


@login_required(login_url='login')
def user_dashboard(request):
    """User dashboard with statistics"""
    user_profile = UserProfile.objects.get(user=request.user)
    total_songs_played = PlaylistHistory.objects.filter(user=request.user).count()
    
    # Get top moods
    history = PlaylistHistory.objects.filter(user=request.user)
    mood_stats = {}
    for entry in history:
        mood = entry.song.mood
        mood_stats[mood] = mood_stats.get(mood, 0) + 1
    
    return render(request, 'dashboard.html', {
        'user_profile': user_profile,
        'total_songs_played': total_songs_played,
        'mood_stats': mood_stats
    })
