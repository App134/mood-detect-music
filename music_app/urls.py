from django.urls import path
from . import views
from . import extra_views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('language-selection/', views.language_selection, name='language_selection'),
    path('home/', views.home, name='home'),
    path('emotion-detection/', views.emotion_detection_page, name='emotion_detection'),
    path('api/detect-emotion/', views.detect_emotion, name='detect_emotion'),
    path('api/get-songs/', views.get_song_recommendations, name='get_songs'),
    path('api/search-songs/', views.search_songs, name='search_songs'),
    path('api/play-song/', views.play_song, name='play_song'),
    path('api/create-playlist/', views.create_playlist, name='create_playlist'),
    path('api/add-to-playlist/', views.add_to_playlist, name='add_to_playlist'),
    path('api/get-playlists/', views.get_playlists, name='get_playlists'),
    path('playlist/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    path('api/toggle-like/', extra_views.toggle_like, name='toggle_like'),
    path('api/song-status/', extra_views.get_song_status, name='get_song_status'),
    path('playlist-history/', views.playlist_history, name='playlist_history'),
    path('liked-songs/', extra_views.liked_songs, name='liked_songs'),
    path('player/<int:song_id>/', extra_views.player_page, name='player'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
]
