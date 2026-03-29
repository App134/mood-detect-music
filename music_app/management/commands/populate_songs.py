import os
import random
from django.core.management.base import BaseCommand
from django.conf import settings
from music_app.models import Song

class Command(BaseCommand):
    help = 'Automatically scans media/songs/ and imports MP3 files into the database with smart metadata guessing'

    def handle(self, *args, **options):
        # 1. Identify songs directory
        songs_dir = os.path.join(settings.MEDIA_ROOT, 'songs')
        if not os.path.exists(songs_dir):
            self.stdout.write(self.style.ERROR(f'Directory {songs_dir} not found'))
            return

        # 2. Get all MP3 files
        files = [f for f in os.listdir(songs_dir) if f.lower().endswith('.mp3')]
        self.stdout.write(self.style.SUCCESS(f'Scanning: Found {len(files)} MP3 files in media/songs/'))

        created_count = 0
        skipped_count = 0
        
        # Available model choices
        mood_list = ['happy', 'sad', 'angry', 'fear', 'surprise', 'neutral']
        lang_list = ['en', 'hi', 'ta', 'te', 'ml', 'kn']

        for filename in files:
            # Avoid duplicates by checking audio_file path
            audio_field_path = f'songs/{filename}'
            existing_song = Song.objects.filter(audio_file=audio_field_path).first()
            
            # 3. Clean up Filename for Metadata
            display_name = filename.rsplit('.', 1)[0]
            display_name = display_name.replace('spotdown.org', '')
            display_name = display_name.replace('_', ' ').strip()
            
            # Guess Artist and Title
            artist = "Various Artists"
            title = display_name
            
            if ' - ' in display_name:
                parts = display_name.split(' - ', 1)
                artist = parts[0].strip()
                title = parts[1].strip()
            elif ' by ' in display_name:
                parts = display_name.split(' by ', 1)
                artist = parts[0].strip()
                title = parts[1].strip()

            # 4. Smart Guessing (Mood & Language)
            lower_name = display_name.lower()
            
            # Default mood and language
            mood = 'neutral'
            language = 'en'
            
            # Basic keyword detection for mood
            if any(k in lower_name for k in ['happy', 'dance', 'party', 'fun', 'remix', 'thara', 'local', 'arambh', 'confident']):
                mood = 'happy'
            elif any(k in lower_name for k in ['sad', 'alone', 'cry', 'broken', 'phir', 'dil', 'judai', 'samjhawan', 'belageddu']):
                mood = 'sad'
            elif any(k in lower_name for k in ['fear', 'dark', 'monster', 'fear', 'horror', 'rudhra', 'agni']):
                mood = 'fear'
            elif any(k in lower_name for k in ['surprise', 'magic', 'spark', 'wonder', 'wao']):
                mood = 'surprise'
            elif any(k in lower_name for k in ['angry', 'war', 'fight', 'power', 'bhairava', 'monster', 'kalki']):
                mood = 'angry'
            
            # Basic keyword detection for language 
            if any(k in lower_name for k in [
                'tamil', 'kaadhal', 'penne', 'anna', 'pethu', 'thulluvadho', 'mari', 
                'rahman', 'anirudh', 'ilayaraja', 'yuvan', 'vairamuthu', 'vijay', 'ajith',
                'suriya', 'dhanush', 'kamal', 'rajini', 'maanery', 'adiye', 'eyala',
                'naan', 'unakkaga', 'enakku', 'nira', 'thamarai', 'poovai', 'veera',
                'vathi', 'kutti', 'petta', 'leo', 'master', 'vikram', 'ponniyin', 'selvan',
                'unnakul', 'kadhal', 'valai', 'uyire', 'kanmani', 'thalaiva', 'thalapathy'
            ]):
                language = 'ta'
            elif any(k in lower_name for k in ['hindi', 'dil', 'pyaar', 'mohabbat', 'apna', 'halka', 'kabira', 'arijit', 'shreya']):
                language = 'hi'
            elif any(k in lower_name for k in ['kannada', 'kantara', 'charlie', 'kempegowda', 'krantiveer', 'sudeep', 'rajkumar']):
                language = 'kn'
            elif any(k in lower_name for k in ['telugu', 'adiga', 'chitti', 'hosanna', 'bhairava', 'prabhas', 'mahesh']):
                language = 'te'
            elif any(k in lower_name for k in ['malayalam', 'aaraadhike', 'jimmiki', 'hridayam', 'darshana', 'mohanlal', 'mammootty']):
                language = 'ml'

            # If mood is still neutral, give it a bit of variety to populate sections
            if mood == 'neutral' and random.random() < 0.3:
                mood = random.choice(['happy', 'sad'])

            # 5. Save to Database
            try:
                if existing_song:
                    # Update language if it was default 'en' but now detected as something else
                    if existing_song.language == 'en' and language != 'en':
                        existing_song.language = language
                        existing_song.save()
                        self.stdout.write(self.style.SUCCESS(f'Updated language to {language} for: {filename}'))
                    skipped_count += 1
                else:
                    Song.objects.create(
                        title=title[:250],
                        artist=artist[:250],
                        audio_file=audio_field_path,
                        mood=mood,
                        language=language
                    )
                    created_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to process {filename}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished! Imported {created_count} songs. {skipped_count} were already in DB.'))
