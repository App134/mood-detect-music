from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control, never_cache
from .forms import SignUpForm, LoginForm, UserProfileForm
from .models import UserProfile, Song, PlaylistHistory, LikedSong, Playlist, PlaylistSong
from .youtube_api import YouTubeAPI
from . import emotion_detector
import json
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from django.contrib.auth.models import User
import pyrebase

# Initialize Pyrebase
firebaseConfig = {
    "apiKey": "AIzaSyAyYhybmDuEklIdvjYP6I2f4W4GifeS_9g",
    "authDomain": "mood-detect-music.firebaseapp.com",
    "projectId": "mood-detect-music",
    "storageBucket": "mood-detect-music.firebasestorage.app",
    "messagingSenderId": "317958909783",
    "appId": "1:317958909783:web:82bdb7ef8f691a24e35812",
    "measurementId": "G-8YT32QJ9BK",
    "databaseURL": ""
}

import logging

logger = logging.getLogger(__name__)

# Initialize Pyrebase only once
# Your pyrebase configuration
firebaseConfig = {
    "apiKey": "AIzaSyAyYhybmDuEklIdvjYP6I2f4W4GifeS_9g",
    "authDomain": "mood-detect-music.firebaseapp.com",
    "projectId": "mood-detect-music",
    "storageBucket": "mood-detect-music.firebasestorage.app",
    "messagingSenderId": "317958909783",
    "appId": "1:317958909783:web:82bdb7ef8f691a24e35812",
    "measurementId": "G-8YT32QJ9BK",
    "databaseURL": "" # Required by pyrebase4
}

try:
    if not firebaseConfig.get("apiKey") or firebaseConfig.get("apiKey") == "YOUR_API_KEY":
        logger.warning("Firebase API Key is missing or default. Firebase Auth may not work.")
    
    firebase = pyrebase.initialize_app(firebaseConfig)
    firebase_auth = firebase.auth()
    logger.info("Successfully initialized Pyrebase")
except Exception as e:
    logger.error(f"Failed to initialize Pyrebase: {e}")
    # Don't let this crash the app on startup
    firebase_auth = None
    firebase = None

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
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            username = form.cleaned_data.get('username')
            
            logger.info(f"Attempting signup for user: {username} ({email})")
            
            try:
                # 1. Create user in Firebase Authentication
                if firebase_auth:
                    try:
                        firebase_auth.create_user_with_email_and_password(email, password)
                        logger.info(f"Firebase user created successfully for {email}")
                    except Exception as fe:
                        # Check if user already exists in Firebase
                        error_str = str(fe)
                        if 'EMAIL_EXISTS' in error_str:
                            logger.warning(f"Firebase user {email} already exists. This might be a retry attempt. Proceeding to Django sync.")
                        else:
                            logger.error(f"Firebase signup error: {error_str}")
                            raise fe
                else:
                    logger.warning("Firebase auth not initialized, skipping Firebase user creation.")

                # 2. Create user in Django Local DB
                # This will trigger the signal in signals.py to create UserProfile
                user = form.save()
                logger.info(f"Django user {username} saved successfully.")
                
                # Auto-login the new user
                auth_user = authenticate(username=username, password=password)
                if auth_user is not None:
                    login(request, auth_user)
                    logger.info(f"User {username} auto-logged in.")
                    messages.success(request, f'Welcome, {username}! Your account has been created.')
                    return redirect('home')
                else:
                    logger.warning(f"Auto-login failed for {username} after successful creation.")
                    messages.success(request, f'Account created for {username}. Please log in to continue.')
                    return redirect('login')
                    
            except Exception as e:
                # Detailed logging for Render
                logger.error(f"Signup error for {username}: {str(e)}", exc_info=True)
                
                error_msg = str(e)
                try:
                    # Pyrebase errors often have a JSON string in args[1]
                    if hasattr(e, 'args') and len(e.args) > 1:
                        error_json = json.loads(e.args[1])
                        error_msg = error_json['error']['message']
                except:
                    pass
                
                messages.error(request, f"Signup failed: {error_msg}")
        else:
            logger.warning(f"Signup form validation failed for user {request.POST.get('username')}: {form.errors.as_text()}")
            # Form errors will be displayed in the template
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
            password = form.cleaned_data.get('password')
            user = form.get_user()
            
            # Form validation in Django was successful. Wait, let's auth against Firebase too!
            try:
                # Firebase requires an email. We assume user.email is populated properly.
                if user.email:
                    try:
                        firebase_auth.sign_in_with_email_and_password(user.email, password)
                    except Exception as inner_e:
                        error_str = str(inner_e)
                        # If Firebase says invalid credentials (or email not found), it likely means 
                        # this is an old Django user that hasn't been synced to Firebase yet.
                        # Since Django just authenticated them successfully, we KNOW the password is correct.
                        # We can securely create their Firebase account now.
                        if 'INVALID_LOGIN_CREDENTIALS' in error_str or 'EMAIL_NOT_FOUND' in error_str:
                            firebase_auth.create_user_with_email_and_password(user.email, password)
                            print(f"Auto-synced existing Django user {username} to Firebase.")
                        else:
                            raise inner_e
                else:
                    # Proceed without Firebase if no email tied to account (legacy accounts)
                    print(f"User {username} has no email, skipping Firebase auth.")
                
                login(request, user)
                messages.success(request, f'Welcome, {username}!')
                return redirect('home')
            except Exception as e:
                error_msg = str(e)
                try:
                    error_json = json.loads(e.args[1])
                    error_msg = error_json['error']['message']
                except:
                    pass
                messages.error(request, f"Firebase Auth Error: {error_msg}")
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
    
    # Log language preference for debugging on Render
    logger.info(f"Home View: User {request.user.username} preferred language is '{user_profile.preferred_language}'")
    
    # 0. Custom Playlists
    user_playlists = Playlist.objects.filter(user=request.user)
    
    # 1. Recommended Playlist (recommendation based on language)
    recommended_qs = Song.objects.filter(language=user_profile.preferred_language).exclude(audio_file__exact='')
    logger.info(f"Home View: Found {recommended_qs.count()} songs for language '{user_profile.preferred_language}'")
    
    my_playlist = list(recommended_qs[:10])
    if not my_playlist:
        logger.warning(f"Home View: No songs found for language '{user_profile.preferred_language}', falling back to all songs.")
        my_playlist = list(Song.objects.exclude(audio_file__exact='')[:10])
        
    # 2. Liked Songs
    liked_songs = [ls.song for ls in LikedSong.objects.filter(user=request.user).select_related('song').order_by('-liked_at')[:10]]
    
    # 3. Recently Played (deduplicated)
    history_entries = PlaylistHistory.objects.filter(user=request.user).select_related('song').order_by('-played_at')[:30]
    recent_songs = []
    seen_song_ids = set()
    for entry in history_entries:
        if entry.song.id not in seen_song_ids:
            recent_songs.append(entry.song)
            seen_song_ids.add(entry.song.id)
            if len(recent_songs) >= 10:
                break
                
    return render(request, 'home.html', {
        'user_profile': user_profile,
        'user_playlists': user_playlists,
        'my_playlist': my_playlist,
        'liked_songs': liked_songs,
        'recent_songs': recent_songs,
    })


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

        # Log for dashboard monitoring
        logger.info(f"Emotion detection result: emotion={emotion}, mood={mood}, confidence={confidence}")

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
def search_songs(request):
    """AJAX endpoint for live search of songs"""
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'songs': []})
            
        from django.db.models import Q
        # Search by title or artist, case-insensitive
        songs = Song.objects.filter(
            Q(title__icontains=query) | Q(artist__icontains=query)
        ).exclude(audio_file__exact='')[:10]
        
        songs_data = [{
            'id': song.id,
            'title': song.title,
            'artist': song.artist,
            'thumb': song.thumbnail_image.url if song.thumbnail_image else (song.thumbnail_url or 'https://via.placeholder.com/200x200?text=MinuMusic'),
            'url': song.audio_file.url if song.audio_file else '#'
        } for song in songs]
        
        return JsonResponse({'songs': songs_data})
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
            'thumb': song.thumbnail_image.url if song.thumbnail_image else (song.thumbnail_url or 'https://via.placeholder.com/200x200?text=MoodMusic'),
            'mood': song.mood,
            'language': song.language,
            'youtube_id': song.youtube_id,
            'url': song.audio_file.url if song.audio_file else '#'
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
@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_dashboard(request):
    """User dashboard with statistics"""
    from django.db.models.functions import TruncDate
    user_profile = UserProfile.objects.get(user=request.user)
    history = PlaylistHistory.objects.filter(user=request.user).order_by('-played_at')
    
    total_songs_played = history.count()
    
    # Active Days calculation
    active_days = history.annotate(day=TruncDate('played_at')).values('day').distinct().count()
    
    # Recent Activity
    recent_activity = history.select_related('song')[:5]
    
    # Get top moods
    mood_stats = {}
    for entry in history:
        mood = entry.emotion_detected
        mood_stats[mood] = mood_stats.get(mood, 0) + 1
        
    return render(request, 'dashboard.html', {
        'user_profile': user_profile,
        'total_songs_played': total_songs_played,
        'mood_stats': mood_stats,
        'active_days': active_days,
        'recent_activity': recent_activity
    })

@login_required(login_url='login')
@require_POST
def create_playlist(request):
    try:
        import json
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Playlist name is required'})
            
        playlist = Playlist.objects.create(user=request.user, name=name)
        return JsonResponse({'success': True, 'playlist': {'id': playlist.id, 'name': playlist.name}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='login')
def get_playlists(request):
    playlists = Playlist.objects.filter(user=request.user).order_by('-created_at')
    data = [{'id': p.id, 'name': p.name} for p in playlists]
    return JsonResponse({'playlists': data})

@login_required(login_url='login')
@require_POST
def add_to_playlist(request):
    try:
        import json
        data = json.loads(request.body)
        playlist_id = data.get('playlist_id')
        song_id = data.get('song_id')
        
        playlist = Playlist.objects.get(id=playlist_id, user=request.user)
        song = Song.objects.get(id=song_id)
        
        PlaylistSong.objects.get_or_create(playlist=playlist, song=song)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='login')
def playlist_detail(request, playlist_id):
    from django.shortcuts import get_object_or_404
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist_songs = PlaylistSong.objects.filter(playlist=playlist).select_related('song').order_by('-added_at')
    return render(request, 'playlist_detail.html', {'playlist': playlist, 'playlist_songs': playlist_songs})
