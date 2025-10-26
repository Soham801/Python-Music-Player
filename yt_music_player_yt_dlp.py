#!/usr/bin/env python3
"""
yt_music_player_yt_dlp.py

Stream audio from a YouTube video, display synced transcript/lyrics (if available).

Requirements:
    pip install yt-dlp youtube-transcript-api python-vlc
    VLC must be installed on your system (libvlc accessible).

Usage:
    python yt_music_player_yt_dlp.py
    Paste a YouTube URL or video id when prompted.
"""

import time
import threading
import sys
import math
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import vlc
from yt_dlp import YoutubeDL

# ---------- Utility functions ----------

def fetch_info_and_audio_url(youtube_url_or_id: str):
    """
    Uses yt_dlp to extract video metadata and the best audio format's direct URL
    without downloading the file.
    Returns tuple: (info_dict, audio_url) or raises Exception
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        # do not merge into m4a etc; we want the direct stream URL from a format entry
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url_or_id, download=False)
        # If playlist or webpage returns a 'entries' list, pick first
        if "entries" in info and isinstance(info["entries"], list):
            # pick first non-None entry
            for e in info["entries"]:
                if e:
                    info = e
                    break

        # Prefer formats with acodec != 'none'
        formats = info.get("formats") or []
        best_audio_url = None
        best_bitrate = -1
        for f in formats:
            acodec = f.get("acodec")
            if not acodec or acodec == "none":
                continue
            # prefer higher abr or filesize
            abr = f.get("abr") or 0
            filesize = f.get("filesize") or 0
            score = (abr or 0) * 1000 + (filesize or 0)
            if score > best_bitrate:
                best_bitrate = score
                best_audio_url = f.get("url")
        # Fallback: some entries expose 'url' directly
        if not best_audio_url:
            # try top-level url
            best_audio_url = info.get("url")
        if not best_audio_url:
            raise RuntimeError("Could not find a direct audio URL in the video formats.")
        return info, best_audio_url

def fetch_transcript(video_id: str, languages=None):
    """
    Try to fetch transcript entries via youtube_transcript_api.
    Returns a list of dicts: {'text': ..., 'start': <sec>, 'duration': <sec>}
    If not available returns None.
    """
    try:
        if languages:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except TranscriptsDisabled:
        print("[Transcript] Transcripts are disabled for this video.")
    except NoTranscriptFound:
        print("[Transcript] No transcript found for this video (in requested languages).")
    except VideoUnavailable:
        print("[Transcript] Video unavailable; cannot fetch transcript.")
    except Exception as e:
        print(f"[Transcript] Unexpected error while fetching transcript: {e}")
    return None

def format_time_ms(ms: int) -> str:
    s = max(0, ms // 1000)
    m = s // 60
    s = s % 60
    return f"{m:02d}:{s:02d}"

# ---------- Lyrics display thread ----------

class LyricsDisplayer(threading.Thread):
    def __init__(self, player: vlc.MediaPlayer, transcript):
        super().__init__(daemon=True)
        self.player = player
        self.transcript = transcript or []
        self.entries = []
        for item in self.transcript:
            start_ms = int(item.get("start", 0) * 1000)
            text = item.get("text", "").strip()
            self.entries.append((start_ms, text))
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def run(self):
        if not self.entries:
            # No transcript: show simple playback timer
            print("\n[No transcript available] Showing playback time. Type 's' + Enter to stop.\n")
            prev_time = -1
            try:
                while not self.stop_flag and self.player.is_playing():
                    t = self.player.get_time()  # ms
                    if t != prev_time:
                        prev_time = t
                        sys.stdout.write(f"\rPlaying — {format_time_ms(t)}")
                        sys.stdout.flush()
                    time.sleep(0.2)
            except KeyboardInterrupt:
                pass
            print()
            return

        idx = 0
        total = len(self.entries)
        print("\nLyrics (synced). Type 's' + Enter to stop playback.\n")
        try:
            while not self.stop_flag and idx < total:
                current_ms = self.player.get_time()
                if current_ms < 0:
                    time.sleep(0.1)
                    continue
                start_ms, text = self.entries[idx]
                # if playback passed start_ms, print it
                if current_ms + 250 >= start_ms:
                    timestamp = format_time_ms(start_ms)
                    sys.stdout.write(f"{timestamp} — {text}\n")
                    sys.stdout.flush()
                    idx += 1
                else:
                    time.sleep(0.05)
            # After finishing transcript, wait until playback ends (or stop)
            while not self.stop_flag and self.player.is_playing():
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass

# ---------- Main program ----------

def main():
    print("YouTube Music Player (yt-dlp) with Synced Lyrics")
    print("------------------------------------------------")
    url = input("Paste a YouTube URL (or video id) and press Enter:\n").strip()
    if not url:
        print("No URL provided. Exiting.")
        return

    print("\nFetching video info via yt-dlp...")
    try:
        info, audio_url = fetch_info_and_audio_url(url)
    except Exception as e:
        print(f"Failed to extract info/audio URL: {e}")
        print("If this persists, try updating yt-dlp: pip install -U yt-dlp")
        return

    title = info.get("title", "<unknown>")
    uploader = info.get("uploader") or info.get("channel") or "<unknown>"
    duration = info.get("duration") or 0
    video_id = info.get("id")
    print(f"\nTitle  : {title}")
    print(f"Uploader: {uploader}")
    mins = duration // 60
    secs = duration % 60
    print(f"Duration: {mins}m {secs}s")
    if video_id:
        print(f"Video id: {video_id}")

    # Try to fetch transcript (prefer english then defaults)
    transcript = None
    print("\nTrying to fetch transcript (captions) for lyrics...")
    for lang_try in (["en"], None):
        transcript = fetch_transcript(video_id, languages=lang_try)
        if transcript:
            break

    if transcript:
        print("Transcript fetched — will attempt to sync lyrics.")
    else:
        print("Transcript not found. Playback will continue without synced lyrics.")

    # Start VLC player
    print("\nStarting player (VLC)...")
    try:
        instance = vlc.Instance()
        player = instance.media_player_new()
        media = instance.media_new(audio_url)
        player.set_media(media)
        player.play()
        # wait for play to initialize (give time)
        time.sleep(0.7)
        # check for error state
        if player.get_state() == vlc.State.Error:
            print("VLC failed to start playback. Ensure VLC is installed and libvlc is accessible.")
            return
    except Exception as e:
        print(f"Error initializing VLC player: {e}")
        return

    # Start lyrics displayer
    lyrics_thread = LyricsDisplayer(player, transcript)
    lyrics_thread.start()

    # Simple control loop: blocking input on commands in main thread
    print("\nControls: Type 'p' + Enter to pause/resume, 's' + Enter to stop and exit.")
    try:
        while True:
            # If playback ended, exit
            state = player.get_state()
            if state in (vlc.State.Ended, vlc.State.Stopped):
                break
            cmd = input().strip().lower()
            if cmd == "p":
                if player.is_playing():
                    player.pause()
                    print("[Paused]")
                else:
                    player.play()
                    print("[Playing]")
            elif cmd == "s":
                print("[Stopping playback]")
                player.stop()
                break
            else:
                print("Unknown command. Use 'p' to pause/resume, 's' to stop.")
    except KeyboardInterrupt:
        print("\n[Interrupted by user] Stopping...")
    finally:
        lyrics_thread.stop()
        try:
            player.stop()
        except Exception:
            pass
        time.sleep(0.2)
        print("Exited. Goodbye!")

if __name__ == "__main__":
    main()