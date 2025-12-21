"""
Simple CLI for testing audio capture and transcription.

This is a Phase 1 test harness - will be replaced by the Textual TUI later.
"""

import asyncio
from datetime import datetime

from .config import config
from .engine import AudioCapture, TranscriberWorker, Session


async def main():
    """Main entry point for the CLI."""
    
    print("=" * 60)
    print("  Squelch - Phase 1 Test CLI")
    print("=" * 60)
    print()
    
    # List available devices
    print("Available audio devices:")
    print("-" * 40)
    devices = AudioCapture.list_devices()
    loopback_devices = [d for d in devices if d["is_loopback"]]
    
    for device in loopback_devices:
        print(f"  [{device['index']}] {device['name']}")
    
    if not loopback_devices:
        print("  No loopback devices found!")
        print("  Make sure you have audio playing or VB-Cable installed.")
        return
    
    print()
    print("-" * 40)
    print()
    
    # Create session
    session = Session()
    
    # Create transcriber worker
    print(f"[INFO] Loading Whisper model '{config.whisper.model_size}'...")
    transcriber = TranscriberWorker(config.whisper)
    transcriber.start()
    print("[INFO] Whisper model loaded.")
    print()
    
    # Callback when audio chunk is ready
    def on_chunk_ready(audio, start_time, end_time):
        session.audio_chunks_captured += 1
        duration = end_time - start_time
        print(f"[AUDIO] Chunk {session.audio_chunks_captured}: {duration:.1f}s captured, sending to Whisper...")
        transcriber.submit(audio, start_time, end_time)
    
    # Create audio capture
    audio = AudioCapture(config.audio, on_chunk_ready=on_chunk_ready)
    
    # Start capturing
    print(f"[INFO] Starting audio capture...")
    print(f"[INFO] Chunk duration: {config.audio.chunk_duration}s")
    print(f"[INFO] Press Ctrl+C to stop.")
    print()
    print("=" * 60)
    print("  TRANSCRIPT")
    print("=" * 60)
    print()
    
    session.is_recording = True
    audio.start()
    
    # Main loop - poll for transcription results
    try:
        while True:
            # Check for transcription results
            result = transcriber.get_result(timeout=None)
            if result:
                session.add_segment(result.text, result.start_time, result.end_time)
                
                # Format timestamp
                minutes = int(result.start_time // 60)
                seconds = int(result.start_time % 60)
                timestamp = f"[{minutes:02d}:{seconds:02d}]"
                
                # Print the transcribed text
                if result.text:
                    print(f"{timestamp} {result.text}")
                else:
                    print(f"{timestamp} (silence)")
            
            await asyncio.sleep(0.1)
    
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[INFO] Stopping...")
    
    finally:
        # Cleanup with robust error handling
        session.is_recording = False
        
        try:
            audio.stop()
        except Exception as e:
            print(f"[WARN] Error stopping audio: {e}")
        
        try:
            transcriber.stop()
        except Exception as e:
            print(f"[WARN] Error stopping transcriber: {e}")
        
        try:
            audio.terminate()
        except Exception as e:
            print(f"[WARN] Error terminating audio: {e}")
        
        print()
        print("=" * 60)
        print("  SESSION SUMMARY")
        print("=" * 60)
        print(f"  Duration: {session.duration:.1f}s")
        print(f"  Chunks captured: {session.audio_chunks_captured}")
        print(f"  Chunks transcribed: {session.audio_chunks_transcribed}")
        print(f"  Word count: {session.word_count}")
        print("=" * 60)


def run():
    """Entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()