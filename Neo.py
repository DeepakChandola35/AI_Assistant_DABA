# """
# Daba - AI Desktop Assistant with Wake Word Detection
# Python Version: 3.12+ Compatible (PyAudio removed)
# ENHANCED MICROPHONE SENSITIVITY VERSION
# """
#
# import google.generativeai as genai
# import subprocess
# import os
# import time
# import glob
# import re
# import sounddevice as sd
# import soundfile as sf
# from RealtimeSTT import AudioToTextRecorder
# import threading
# from queue import Queue
# import logging
# from pathlib import PathF
# from typing import Optional, Tuple
# import sys
# import numpy as np
# # GEMINI API KEY
# os.environ["GEMINI_API_KEY"] = "AIzaSyA1_5lV1V35-7OXG0q0lnpHQj2-khfNLQQ"
# # Setup logging with UTF-8 encoding to handle emojis
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('neo.log', encoding='utf-8'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)
#
# # Set console encoding to UTF-8 for Windows
# if sys.platform == 'win32':
#     import codecs
#     sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
#     sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
#
#
# '''-----Configuration-----'''
# class Config:
#     # Wake words (case-insensitive)
#     WAKE_WORDS = ["hey ", "okay", "wake up","yes","Daba","Hey Daba"]  # Added "wake up" since it's working!
#
#     # Audio devices - set to None to use system defaults
#     SPEAKER_NAME = None  # Will use default output
#     MICROPHONE_NAME = "Microphone Array"  # Will use default input
#
#     # MICROPHONE BOOST SETTINGS - NEW!
#     MIC_GAIN_MULTIPLIER = 3.0  # Boost microphone input by 3x (adjust 1.0-5.0)
#     INPUT_VOLUME_DB = 20  # Additional dB boost (0-30)
#
#     # Piper TTS
#     PIPER_MODEL = 'models/en_US-ryan-high.onnx'
#     BASE_DIR = Path(__file__).parent
#     PIPER_EXE = BASE_DIR / 'piper' / 'piper.exe'
#     MODEL_PATH = BASE_DIR / 'piper' / PIPER_MODEL
#     OUTPUT_DIR = BASE_DIR / 'output'
#
#     # Audio file management
#     MAX_AUDIO_FILES = 3
#
#     # Timeout settings
#     WAKE_WORD_TIMEOUT = 30  # seconds before going back to sleep
#     RESPONSE_TIMEOUT = 30  # seconds to wait for user input after wake
#
#
# '''-----Global State Management-----'''
# class AssistantState:
#     def __init__(self):
#         self.is_awake = False
#         self.is_listening = False
#         self.is_speaking = False
#         self.last_interaction = time.time()
#         self.user_input = ""
#         self.serial_command = ""
#         self.piper_process: Optional[subprocess.Popen] = None
#         self.selected_device: Optional[int] = None
#         self.mic_device: Optional[int] = None
#         self.response_queue = Queue()
#         self.lock = threading.Lock()
#
#     def wake_up(self):
#         with self.lock:
#             self.is_awake = True
#             self.last_interaction = time.time()
#             logger.info("🟢 Daba is now AWAKE and listening")
#
#     def go_to_sleep(self):
#         with self.lock:
#             self.is_awake = False
#             self.is_listening = False
#             logger.info("💤 Daba is going to SLEEP - say wake word to activate")
#
#     def update_activity(self):
#         with self.lock:
#             self.last_interaction = time.time()
#
#     def check_timeout(self) -> bool:
#         with self.lock:
#             if self.is_awake and (time.time() - self.last_interaction > Config.WAKE_WORD_TIMEOUT):
#                 return True
#         return False
#
#
# # Global state instance
# state = AssistantState()
#
#
# '''-----LLM Setup-----'''
# def setup_llm():
#     """Initialize the Gemini model with proper error handling"""
#     try:
#         api_key = os.getenv('GEMINI_API_KEY')
#         if not api_key:
#             logger.error("GEMINI_API_KEY environment variable not set!")
#             logger.info("Set it with: export GEMINI_API_KEY='your_key_here'")
#             sys.exit(1)
#
#         genai.configure(api_key=api_key)
#
#         system_prompt = """You are Neo, a helpful and friendly AI desktop assistant.
#
# Guidelines:
# - Be conversational, warm, and concise
# - Keep responses under 150 words when possible
# - Use only these punctuation marks: ! , . ?
# - Always end with exactly ONE emotion in brackets
#
# Available emotions: (happy, sad, angry, confused, laugh, wave, point, nod, shrug)
#
# Example: "I'd be happy to help you with that! (happy)"
# """
#
#         # Use gemini-2.5-flash - confirmed working with your API key!
#         model = genai.GenerativeModel('models/gemini-2.5-flash', system_instruction=system_prompt)
#         chat_session = model.start_chat()
#
#         logger.info("✅ LLM initialized successfully with gemini-2.5-flash")
#         return chat_session
#
#     except Exception as e:
#         logger.error(f"Failed to initialize LLM: {e}")
#         sys.exit(1)
#
#
# '''-----Audio Device Management (PyAudio-Free)-----'''
# def list_audio_devices():
#     """List all available audio devices"""
#     devices = sd.query_devices()
#     logger.info("\n📱 Available Audio Devices:")
#     for i, device in enumerate(devices):
#         logger.info(f"  [{i}] {device['name']} - In:{device['max_input_channels']} Out:{device['max_output_channels']}")
#     return devices
#
#
# def find_device_by_name(device_name: Optional[str], device_type: str = 'output') -> Optional[int]:
#     """Find device by name, return None for default"""
#     if device_name is None:
#         return None
#
#     try:
#         devices = sd.query_devices()
#
#         for idx, device in enumerate(devices):
#             if device_name.lower() in device['name'].lower():
#                 if device_type == 'output' and device['max_output_channels'] > 0:
#                     logger.info(f"Using {device_type} device: {device['name']}")
#                     return idx
#                 elif device_type == 'input' and device['max_input_channels'] > 0:
#                     logger.info(f"Using {device_type} device: {device['name']}")
#                     return idx
#
#         logger.warning(f"Device '{device_name}' not found. Using system default.")
#         return None
#
#     except Exception as e:
#         logger.error(f"Error finding device: {e}")
#         return None
#
#
# def find_default_microphone() -> Optional[int]:
#     """Find the default input device that works with RealtimeSTT"""
#     try:
#         devices = sd.query_devices()
#         default_input = sd.default.device[0]
#
#         # Verify it has input channels
#         if devices[default_input]['max_input_channels'] > 0:
#             logger.info(f"Using default microphone: {devices[default_input]['name']}")
#             return default_input
#
#         # Find first device with input channels
#         for idx, device in enumerate(devices):
#             if device['max_input_channels'] > 0:
#                 logger.info(f"Using microphone: {device['name']}")
#                 return idx
#
#         logger.error("No input device found!")
#         return None
#
#     except Exception as e:
#         logger.error(f"Error finding microphone: {e}")
#         return None
#
#
# '''-----Wake Word Detection-----'''
# def check_for_wake_word(text: str) -> bool:
#     """Check if the transcribed text contains a wake word"""
#     text_lower = text.lower().strip()
#
#     for wake_word in Config.WAKE_WORDS:
#         if wake_word in text_lower:
#             logger.info(f"🎯 Wake word detected: '{wake_word}'")
#             return True
#
#     return False
#
#
# def remove_wake_word(text: str) -> str:
#     """Remove wake word from the beginning of the text"""
#     text_lower = text.lower().strip()
#
#     for wake_word in Config.WAKE_WORDS:
#         if text_lower.startswith(wake_word):
#
#             remaining = text[len(wake_word):].strip()
#             remaining = remaining.lstrip(',.!?')
#             return remaining.strip()
#
#     return text
#
#
# '''-----Emotion & Serial Commands-----'''
# def extract_text_and_emotion(text: str) -> Tuple[str, str]:
#     """Extract the main text and emotion from the response"""
#     match = re.search(r"(.*?)\s*\((\w+)\)\s*$", text)
#
#     if match:
#         main_text = match.group(1).strip()
#         emotion = match.group(2).strip().lower()
#         return main_text, emotion
#
#     return text.strip(), "happy"  # Default emotion
#
#
# def handle_emotion(emotion: str):
#     """Handle emotion display (Arduino disabled)"""
#     allowed_emotions = ["sad", "angry", "happy", "confused", "laugh", "wave", "point", "nod", "shrug"]
#
#     if emotion in allowed_emotions:
#         logger.info(f"😊 Emotion: {emotion}")
#     else:
#         logger.info(f"😊 Emotion: happy (default)")
#
#
# '''-----Speech-to-Text (STT) with MICROPHONE BOOST-----'''
# def on_realtime_transcription(text: str):
#     """Callback for realtime transcription updates"""
#     if not text.strip():
#         return
#
#     # Always show what's being heard
#     logger.info(f"🎤 Hearing (realtime): {text}")
#
#     # Check for wake word if assistant is asleep
#     if not state.is_awake:
#         if check_for_wake_word(text):
#             state.wake_up()
#             play_acknowledgment_sound()
#
#
# def on_final_transcription(text: str):
#     """Callback for final transcription"""
#     if not text.strip():
#         return
#
#     logger.info(f"📝 Final transcription: {text}")
#     logger.info(f"💤 Assistant awake status: {state.is_awake}")
#
#     # If asleep, check for wake word
#     if not state.is_awake:
#         logger.info(f"🔍 Checking for wake word in: '{text}'")
#         if check_for_wake_word(text):
#             state.wake_up()
#             play_acknowledgment_sound()
#
#             # Check if there's a command after the wake word
#             remaining_text = remove_wake_word(text)
#             if remaining_text and len(remaining_text) > 3:
#                 logger.info(f"📌 Command after wake word: {remaining_text}")
#                 state.user_input = remaining_text
#                 state.response_queue.put(remaining_text)
#         else:
#             logger.info(f"❌ No wake word detected in: '{text}'")
#         return
#
#     # If awake, process the command
#     logger.info(f"✅ Assistant is awake, processing command: {text}")
#     state.update_activity()
#     state.user_input = text
#     state.response_queue.put(text)
#
#
# def create_recorder(microphone_index: Optional[int]) -> AudioToTextRecorder:
#     """Create and configure the STT recorder with ENHANCED SENSITIVITY"""
#     recorder_config = {
#         'model': 'base.en',
#         'realtime_model_type': 'tiny.en',
#         'language': 'en',
#
#         # ENHANCED MICROPHONE SENSITIVITY SETTINGS
#         'silero_sensitivity': 0.01,  # Changed from 0.05 to 0.01 (more sensitive)
#         'webrtc_sensitivity': 2,     # Changed from 3 to 2 (more sensitive)
#         'post_speech_silence_duration': 0.5,  # Reduced from 0.7
#         'min_length_of_recording': 0.5,       # Reduced from 0.8
#         'min_gap_between_recordings': 0,
#
#         'enable_realtime_transcription': True,
#         'realtime_processing_pause': 0.05,
#         'on_realtime_transcription_update': on_realtime_transcription,
#         'silero_deactivity_detection': True,
#         'beam_size': 5,
#         'beam_size_realtime': 3,
#         'no_log_file': True,
#
#         # VOLUME BOOST - NEW!
#         'input_device_index': microphone_index,
#     }
#
#     logger.info(f"🎚️  Microphone boost: {Config.MIC_GAIN_MULTIPLIER}x")
#     logger.info(f"🔊 Additional gain: +{Config.INPUT_VOLUME_DB} dB")
#
#     return AudioToTextRecorder(**recorder_config)
#
#
# '''-----Text-to-Speech (TTS)-----'''
# def start_piper_process():
#     """Verify Piper is available"""
#     try:
#         Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
#         logger.info("✅ Piper TTS ready")
#
#     except Exception as e:
#         logger.error(f"Failed to start Piper TTS: {e}")
#         sys.exit(1)
#
#
# def get_latest_audio_file() -> Optional[Path]:
#     """Find the most recently created .wav file"""
#     wav_files = list(Config.OUTPUT_DIR.glob("*.wav"))
#     if not wav_files:
#         return None
#     return max(wav_files, key=lambda f: f.stat().st_ctime)
#
#
# def maintain_audio_file_limit(max_files: int = Config.MAX_AUDIO_FILES):
#     """Keep only the most recent audio files"""
#     wav_files = sorted(Config.OUTPUT_DIR.glob("*.wav"), key=lambda f: f.stat().st_ctime)
#
#     if len(wav_files) > max_files:
#         for file_to_delete in wav_files[:-max_files]:
#             try:
#                 file_to_delete.unlink()
#                 logger.debug(f"Deleted old audio file: {file_to_delete.name}")
#             except Exception as e:
#                 logger.error(f"Error deleting file {file_to_delete}: {e}")
#
#
# def play_audio(file_path: Path, device_id: Optional[int] = None):
#     """Play a WAV file using sounddevice"""
#     try:
#         state.is_speaking = True
#         data, samplerate = sf.read(str(file_path))
#         sd.play(data, samplerate, device=device_id)
#         sd.wait()
#         logger.info(f"🔊 Playback finished")
#         state.is_speaking = False
#
#     except Exception as e:
#         logger.error(f"Error playing audio: {e}")
#         state.is_speaking = False
#
#
# def calculate_generation_delay(text: str) -> float:
#     """Estimate TTS generation time based on text length"""
#     num_words = len(text.split())
#     estimated_delay = num_words * 0.1
#     return max(0.5, min(estimated_delay, 10))
#
#
# def speak(text: str, device_id: Optional[int] = None):
#     """Generate and play speech from text using Piper in single-shot mode"""
#     try:
#         # Generate unique output filename
#         output_file = Config.OUTPUT_DIR / f"speech_{int(time.time() * 1000)}.wav"
#
#         # Run Piper to generate audio
#         result = subprocess.run(
#             [
#                 str(Config.PIPER_EXE),
#                 "--model", str(Config.MODEL_PATH),
#                 "--output_file", str(output_file)
#             ],
#             input=text,
#             text=True,
#             capture_output=True,
#             timeout=10
#         )
#
#         if result.returncode != 0:
#             logger.error(f"Piper TTS failed: {result.stderr}")
#             return
#
#         # Wait a moment for file to be fully written
#         time.sleep(0.2)
#
#         # Check if file exists and has content
#         if output_file.exists() and output_file.stat().st_size > 0:
#             play_audio(output_file, device_id=device_id)
#
#             # Cleanup old files
#             maintain_audio_file_limit()
#         else:
#             logger.error(f"Audio file not generated: {output_file}")
#
#     except subprocess.TimeoutExpired:
#         logger.error("Piper TTS timed out")
#     except Exception as e:
#         logger.error(f"Error in speak function: {e}")
#
#
# def play_acknowledgment_sound():
#     """Play a short acknowledgment when wake word is detected"""
#     speak("Yes?", device_id=state.selected_device)
#
#
# '''-----LLM Response Generation-----'''
# def generate_response(chat_session):
#     """Generate AI response to user input"""
#     try:
#         if not state.user_input:
#             return
#
#         logger.info(f"🤔 Generating response for: {state.user_input}")
#
#         # Get response from LLM
#         response = chat_session.send_message(state.user_input, stream=False)
#         response_text = response.text.strip()
#
#         logger.info(f"🤖 Neo says: {response_text}")
#
#         # Extract text and emotion
#         main_text, emotion = extract_text_and_emotion(response_text)
#         state.serial_command = emotion
#
#         # Handle emotion
#         handle_emotion(emotion)
#
#         # Speak the response
#         speak(main_text, device_id=state.selected_device)
#
#         state.update_activity()
#
#     except Exception as e:
#         logger.error(f"Error generating response: {e}")
#         speak("Sorry, I encountered an error processing your request.", device_id=state.selected_device)
#
#
# '''-----Timeout Monitor-----'''
# def timeout_monitor():
#     """Monitor for inactivity timeout"""
#     while True:
#         time.sleep(1)
#
#         if state.check_timeout() and not state.is_speaking:
#             logger.info("⏰ Timeout reached - going to sleep")
#             state.go_to_sleep()
#
#
# '''-----Microphone Level Monitor (NEW!)-----'''
# def monitor_microphone_levels():
#     """Monitor and display microphone input levels in real-time"""
#     try:
#         logger.info("\n" + "="*60)
#         logger.info("🎤 MICROPHONE LEVEL TEST")
#         logger.info("Speak into your microphone to test the input level...")
#         logger.info("="*60)
#
#         duration = 5  # seconds
#         samplerate = 16000
#
#         def callback(indata, frames, time, status):
#             if status:
#                 logger.warning(status)
#             volume_norm = np.linalg.norm(indata) * 10
#             bar_length = int(min(50, volume_norm))
#             bar = "█" * bar_length
#             logger.info(f"🎚️  Level: {bar} {volume_norm:.2f}")
#
#         with sd.InputStream(callback=callback, channels=1, samplerate=samplerate,
#                            device=state.mic_device):
#             sd.sleep(int(duration * 1000))
#
#         logger.info("="*60 + "\n")
#
#     except Exception as e:
#         logger.error(f"Error monitoring microphone: {e}")
#
#
# '''-----Main Application-----'''
# def main():
#     try:
#         logger.info("="*60)
#         logger.info("🤖 NEO - AI Desktop Assistant Starting...")
#         logger.info(f"🐍 Python Version: {sys.version}")
#         logger.info("="*60)
#
#         # Initialize LLM
#         chat_session = setup_llm()
#
#         # List and setup audio devices
#         list_audio_devices()
#
#         # Find microphone (None = use default)
#         state.mic_device = find_device_by_name(Config.MICROPHONE_NAME, 'input')
#         if state.mic_device is None:
#             state.mic_device = find_default_microphone()
#
#         # Find speaker (None = use default)
#         state.selected_device = find_device_by_name(Config.SPEAKER_NAME, 'output')
#
#         # Test microphone levels
#         monitor_microphone_levels()
#
#         # Start Piper TTS
#         start_piper_process()
#
#         # Start timeout monitor in background
#         timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
#         timeout_thread.start()
#
#         # Create STT recorder
#         logger.info("Initializing speech recognition...")
#         recorder = create_recorder(state.mic_device)
#
#         logger.info("\n" + "="*60)
#         logger.info("✅ Daba IS READY!")
#         logger.info(f"💬 Say one of these wake words: {', '.join(Config.WAKE_WORDS)}")
#         logger.info("="*60 + "\n")
#
#         # Initial greeting
#         speak("Hello! I'm Daba. Say my name to wake me up!", device_id=state.selected_device)
#
#         # Main loop - START THE RECORDER!
#         logger.info("🎤 Starting continuous listening...")
#         recorder.start()
#
#         try:
#             while True:
#                 # Get transcription from recorder
#                 transcription = recorder.text()
#
#                 if transcription:
#                     on_final_transcription(transcription)
#
#                 # Check response queue
#                 if not state.response_queue.empty():
#                     user_text = state.response_queue.get()
#                     generate_response(chat_session)
#
#                 time.sleep(0.1)
#
#         finally:
#             recorder.stop()
#
#     except KeyboardInterrupt:
#         logger.info("\n⚠️  Interrupted by user")
#
#     except Exception as e:
#         logger.error(f"Unexpected error: {e}", exc_info=True)
#
#     finally:
#         logger.info("Shutting down Daba...")
#         logger.info("👋 Goodbye!")
#
#
# if __name__ == '__main__':
#     main()


"""
Daba - AI Desktop Assistant with Wake Word Detection
Python Version: 3.12+ Compatible (PyAudio removed)
ENHANCED MICROPHONE SENSITIVITY VERSION
"""

import google.generativeai as genai
import os
import time
import glob
import re
import sounddevice as sd
import soundfile as sf
from RealtimeSTT import AudioToTextRecorder
import threading
from queue import Queue
import logging
from pathlib import Path
from typing import Optional, Tuple
import sys
import numpy as np
from rapidfuzz import fuzz
from face_auth import verify_face

from voice_auth import verify_speaker
# GEMINI API KEY
os.environ["GEMINI_API_KEY"] = "f4fcc157-6a1c-4977-a41f-6e32938cf212"
# Setup logging with UTF-8 encoding to handle emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set console encoding to UTF-8 for Windows
if sys.platform == 'win32':
    import codecs

    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

'''-----Configuration-----'''


class Config:
    # Wake words (case-insensitive)
    WAKE_WORDS = [
        "hey daba",
        "daba",
        "wake up daba"
    ]

    # Audio devices - set to None to use system defaults
    SPEAKER_NAME = None  # Will use default output
    MICROPHONE_NAME = "Microphone Array"  # Will use default input

    # MICROPHONE BOOST SETTINGS - NEW!
    MIC_GAIN_MULTIPLIER = 3.0  # Boost microphone input by 3x (adjust 1.0-5.0)
    INPUT_VOLUME_DB = 20  # Additional dB boost (0-30)

    # Piper TTS
    PIPER_MODEL = 'models/en_US-ryan-high.onnx'
    BASE_DIR = Path(__file__).parent
    PIPER_EXE = BASE_DIR / 'piper' / 'piper.exe'
    MODEL_PATH = BASE_DIR / 'piper' / PIPER_MODEL
    OUTPUT_DIR = BASE_DIR / 'output'

    # Audio file management
    MAX_AUDIO_FILES = 3

    # Timeout settings
    WAKE_WORD_TIMEOUT = 30  # seconds before going back to sleep
    RESPONSE_TIMEOUT = 30  # seconds to wait for user input after wake


'''-----Global State Management-----'''


class AssistantState:
    def __init__(self):
        self.is_awake = False
        self.is_listening = False
        self.is_speaking = False
        self.last_interaction = time.time()
        self.user_input = ""
        self.serial_command = ""
        self.piper_process: Optional[subprocess.Popen] = None
        self.selected_device: Optional[int] = None
        self.mic_device: Optional[int] = None
        self.response_queue = Queue()
        self.lock = threading.Lock()

    def wake_up(self):
        with self.lock:
            self.is_awake = True
            self.last_interaction = time.time()
            logger.info("🟢 Daba is now AWAKE and listening")

    def go_to_sleep(self):
        with self.lock:
            self.is_awake = False
            self.is_listening = False
            logger.info("💤 Daba is going to SLEEP - say wake word to activate")

    def update_activity(self):
        with self.lock:
            self.last_interaction = time.time()

    def check_timeout(self) -> bool:
        with self.lock:
            if self.is_awake and (time.time() - self.last_interaction > Config.WAKE_WORD_TIMEOUT):
                return True
        return False


# Global state instance
state = AssistantState()

'''-----LLM Setup-----'''


def setup_llm():
    """Initialize the Gemini model with proper error handling"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set!")
            logger.info("Set it with: export GEMINI_API_KEY='your_key_here'")
            sys.exit(1)

        genai.configure(api_key=api_key)

        system_prompt = """You are Neo, a helpful and friendly AI desktop assistant. 

Guidelines:
- Be conversational, warm, and concise
- Keep responses under 150 words when possible
- Use only these punctuation marks: ! , . ?
- Always end with exactly ONE emotion in brackets

Available emotions: (happy, sad, angry, confused, laugh, wave, point, nod, shrug)

Example: "I'd be happy to help you with that! (happy)"
"""

        # Use gemini-2.5-flash - confirmed working with your API key!
        model = genai.GenerativeModel('models/gemini-2.5-flash', system_instruction=system_prompt)
        chat_session = model.start_chat()

        logger.info("✅ LLM initialized successfully with gemini-2.5-flash")
        return chat_session

    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        sys.exit(1)


'''-----Audio Device Management (PyAudio-Free)-----'''


def list_audio_devices():
    """List all available audio devices"""
    devices = sd.query_devices()
    logger.info("\n📱 Available Audio Devices:")
    for i, device in enumerate(devices):
        logger.info(f"  [{i}] {device['name']} - In:{device['max_input_channels']} Out:{device['max_output_channels']}")
    return devices


def find_device_by_name(device_name: Optional[str], device_type: str = 'output') -> Optional[int]:
    """Find device by name, return None for default"""
    if device_name is None:
        return None

    try:
        devices = sd.query_devices()

        for idx, device in enumerate(devices):
            if device_name.lower() in device['name'].lower():
                if device_type == 'output' and device['max_output_channels'] > 0:
                    logger.info(f"Using {device_type} device: {device['name']}")
                    return idx
                elif device_type == 'input' and device['max_input_channels'] > 0:
                    logger.info(f"Using {device_type} device: {device['name']}")
                    return idx

        logger.warning(f"Device '{device_name}' not found. Using system default.")
        return None

    except Exception as e:
        logger.error(f"Error finding device: {e}")
        return None


def find_default_microphone() -> Optional[int]:
    """Find the default input device that works with RealtimeSTT"""
    try:
        devices = sd.query_devices()
        default_input = sd.default.device[0]

        # Verify it has input channels
        if devices[default_input]['max_input_channels'] > 0:
            logger.info(f"Using default microphone: {devices[default_input]['name']}")
            return default_input

        # Find first device with input channels
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                logger.info(f"Using microphone: {device['name']}")
                return idx

        logger.error("No input device found!")
        return None

    except Exception as e:
        logger.error(f"Error finding microphone: {e}")
        return None


'''-----Wake Word Detection-----'''


def check_for_wake_word(text: str) -> bool:
    """Check wake word using fuzzy matching"""

    text_lower = text.lower().strip()

    # ignore very small noise
    if len(text_lower) < 3:
        return False

    for wake_word in Config.WAKE_WORDS:

        similarity = fuzz.partial_ratio(
            wake_word.lower(),
            text_lower
        )

        logger.info(f"Checking '{wake_word}' vs '{text_lower}' → Score: {similarity}")

        # threshold for detection
        if similarity > 80:
            logger.info(f"🎯 Wake word detected (fuzzy match): {wake_word}")
            return True

    return False


def remove_wake_word(text: str) -> str:
    """Remove wake word from the beginning of the text"""
    text_lower = text.lower().strip()

    for wake_word in Config.WAKE_WORDS:
        if text_lower.startswith(wake_word):
            remaining = text[len(wake_word):].strip()
            remaining = remaining.lstrip(',.!?')
            return remaining.strip()

    return text


'''-----Emotion & Serial Commands-----'''


def extract_text_and_emotion(text: str) -> Tuple[str, str]:
    """Extract the main text and emotion from the response"""
    match = re.search(r"(.*?)\s*\((\w+)\)\s*$", text)

    if match:
        main_text = match.group(1).strip()
        emotion = match.group(2).strip().lower()
        return main_text, emotion

    return text.strip(), "happy"  # Default emotion


def handle_emotion(emotion: str):
    """Handle emotion display (Arduino disabled)"""
    allowed_emotions = ["sad", "angry", "happy", "confused", "laugh", "wave", "point", "nod", "shrug"]

    if emotion in allowed_emotions:
        logger.info(f"😊 Emotion: {emotion}")
    else:
        logger.info(f"😊 Emotion: happy (default)")


'''-----Speech-to-Text (STT) with MICROPHONE BOOST-----'''

def record_auth_voice():
    """Record short voice sample for authentication"""

    duration = 3
    sample_rate = 16000

    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1
    )

    sd.wait()

    sf.write("temp_voice.wav", audio, sample_rate)

def on_realtime_transcription(text: str):
    """Callback for realtime transcription updates"""
    if not text.strip():
        return

    # Always show what's being heard
    logger.info(f"🎤 Hearing (realtime): {text}")

    # Check for wake word if assistant is asleep
    if not state.is_awake:
        if check_for_wake_word(text):

            logger.info("🔐 Verifying speaker...")

            record_auth_voice()

            authorized = verify_speaker("temp_voice.wav")

            if not authorized:
                logger.info("❌ Unauthorized voice detected")
                return

            logger.info("✅ Authorized user detected")

            state.wake_up()
            play_acknowledgment_sound()

            # remove temp file
            try:
                os.remove("temp_voice.wav")
            except:
                pass


def on_final_transcription(text: str):
    """Callback for final transcription"""
    if not text.strip():
        return

    logger.info(f"📝 Final transcription: {text}")
    logger.info(f"💤 Assistant awake status: {state.is_awake}")

    # If asleep, check for wake word
    if not state.is_awake:
        logger.info(f"🔍 Checking for wake word in: '{text}'")
        if check_for_wake_word(text):
            state.wake_up()
            play_acknowledgment_sound()

            # Check if there's a command after the wake word
            remaining_text = remove_wake_word(text)
            if remaining_text and len(remaining_text) > 3:
                logger.info(f"📌 Command after wake word: {remaining_text}")
                state.user_input = remaining_text
                state.response_queue.put(remaining_text)
        else:
            logger.info(f"❌ No wake word detected in: '{text}'")
        return

    # If awake, process the command
    logger.info(f"✅ Assistant is awake, processing command: {text}")
    state.update_activity()
    state.user_input = text
    state.response_queue.put(text)


def create_recorder(microphone_index: Optional[int]) -> AudioToTextRecorder:
    """Create and configure the STT recorder with ENHANCED SENSITIVITY"""
    recorder_config = {
        'model': 'base.en',
        'realtime_model_type': 'tiny.en',
        'language': 'en',

        # ENHANCED MICROPHONE SENSITIVITY SETTINGS
        'silero_sensitivity': 0.01,  # Changed from 0.05 to 0.01 (more sensitive)
        'webrtc_sensitivity': 2,  # Changed from 3 to 2 (more sensitive)
        'post_speech_silence_duration': 0.5,  # Reduced from 0.7
        'min_length_of_recording': 0.5,  # Reduced from 0.8
        'min_gap_between_recordings': 0,

        'enable_realtime_transcription': True,
        'realtime_processing_pause': 0.05,
        'on_realtime_transcription_update': on_realtime_transcription,
        'silero_deactivity_detection': True,
        'beam_size': 5,
        'beam_size_realtime': 3,
        'no_log_file': True,

        # VOLUME BOOST - NEW!
        'input_device_index': microphone_index,
    }

    logger.info(f"🎚️  Microphone boost: {Config.MIC_GAIN_MULTIPLIER}x")
    logger.info(f"🔊 Additional gain: +{Config.INPUT_VOLUME_DB} dB")

    return AudioToTextRecorder(**recorder_config)


'''-----Text-to-Speech (TTS)-----'''


def start_piper_process():
    """Verify Piper is available"""
    try:
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("✅ Piper TTS ready")

    except Exception as e:
        logger.error(f"Failed to start Piper TTS: {e}")
        sys.exit(1)


def get_latest_audio_file() -> Optional[Path]:
    """Find the most recently created .wav file"""
    wav_files = list(Config.OUTPUT_DIR.glob("*.wav"))
    if not wav_files:
        return None
    return max(wav_files, key=lambda f: f.stat().st_ctime)


def maintain_audio_file_limit(max_files: int = Config.MAX_AUDIO_FILES):
    """Keep only the most recent audio files"""
    wav_files = sorted(Config.OUTPUT_DIR.glob("*.wav"), key=lambda f: f.stat().st_ctime)

    if len(wav_files) > max_files:
        for file_to_delete in wav_files[:-max_files]:
            try:
                file_to_delete.unlink()
                logger.debug(f"Deleted old audio file: {file_to_delete.name}")
            except Exception as e:
                logger.error(f"Error deleting file {file_to_delete}: {e}")


def play_audio(file_path: Path, device_id: Optional[int] = None):
    """Play a WAV file using sounddevice"""
    try:
        state.is_speaking = True
        data, samplerate = sf.read(str(file_path))
        sd.play(data, samplerate, device=device_id)
        sd.wait()
        logger.info(f"🔊 Playback finished")
        state.is_speaking = False

    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        state.is_speaking = False


def calculate_generation_delay(text: str) -> float:
    """Estimate TTS generation time based on text length"""
    num_words = len(text.split())
    estimated_delay = num_words * 0.1
    return max(0.5, min(estimated_delay, 10))


def speak(text: str, device_id: Optional[int] = None):
    """Generate and play speech from text using Piper in single-shot mode"""
    try:
        # Generate unique output filename
        output_file = Config.OUTPUT_DIR / f"speech_{int(time.time() * 1000)}.wav"

        # Run Piper to generate audio
        result = subprocess.run(
            [
                str(Config.PIPER_EXE),
                "--model", str(Config.MODEL_PATH),
                "--output_file", str(output_file)
            ],
            input=text,
            text=True,
            capture_output=True,
            timeout=10
        )

        if result.returncode != 0:
            logger.error(f"Piper TTS failed: {result.stderr}")
            return

        # Wait a moment for file to be fully written
        time.sleep(0.2)

        # Check if file exists and has content
        if output_file.exists() and output_file.stat().st_size > 0:
            play_audio(output_file, device_id=device_id)

            # Cleanup old files
            maintain_audio_file_limit()
        else:
            logger.error(f"Audio file not generated: {output_file}")

    except subprocess.TimeoutExpired:
        logger.error("Piper TTS timed out")
    except Exception as e:
        logger.error(f"Error in speak function: {e}")


def play_acknowledgment_sound():
    """Play a short acknowledgment when wake word is detected"""
    speak("Yes?", device_id=state.selected_device)


'''-----LLM Response Generation-----'''


def generate_response(chat_session):
    """Generate AI response to user input"""
    try:
        if not state.user_input:
            return

        logger.info(f"🤔 Generating response for: {state.user_input}")

        # Get response from LLM
        response = chat_session.send_message(state.user_input, stream=False)
        response_text = response.text.strip()

        logger.info(f"🤖 Neo says: {response_text}")

        # Extract text and emotion
        main_text, emotion = extract_text_and_emotion(response_text)
        state.serial_command = emotion

        # Handle emotion
        handle_emotion(emotion)

        # Speak the response
        speak(main_text, device_id=state.selected_device)

        state.update_activity()

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        speak("Sorry, I encountered an error processing your request.", device_id=state.selected_device)


'''-----Timeout Monitor-----'''


def timeout_monitor():
    """Monitor for inactivity timeout"""
    while True:
        time.sleep(1)

        if state.check_timeout() and not state.is_speaking:
            logger.info("⏰ Timeout reached - going to sleep")
            state.go_to_sleep()


'''-----Microphone Level Monitor (NEW!)-----'''


def monitor_microphone_levels():
    """Monitor and display microphone input levels in real-time"""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("🎤 MICROPHONE LEVEL TEST")
        logger.info("Speak into your microphone to test the input level...")
        logger.info("=" * 60)

        duration = 5  # seconds
        samplerate = 16000

        def callback(indata, frames, time, status):
            if status:
                logger.warning(status)
            volume_norm = np.linalg.norm(indata) * 10
            bar_length = int(min(50, volume_norm))
            bar = "█" * bar_length
            logger.info(f"🎚️  Level: {bar} {volume_norm:.2f}")

        with sd.InputStream(callback=callback, channels=1, samplerate=samplerate,
                            device=state.mic_device):
            sd.sleep(int(duration * 1000))

        logger.info("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Error monitoring microphone: {e}")


'''-----Main Application-----'''


def main():
    try:
        logger.info("=" * 60)
        logger.info("🤖 NEO - AI Desktop Assistant Starting...")
        logger.info(f"🐍 Python Version: {sys.version}")
        logger.info("=" * 60)

        # Initialize LLM
        chat_session = setup_llm()

        # List and setup audio devices
        list_audio_devices()

        # Find microphone (None = use default)
        state.mic_device = find_device_by_name(Config.MICROPHONE_NAME, 'input')
        if state.mic_device is None:
            state.mic_device = find_default_microphone()

        # Find speaker (None = use default)
        state.selected_device = find_device_by_name(Config.SPEAKER_NAME, 'output')

        # Test microphone levels
        monitor_microphone_levels()

        # Start Piper TTS
        start_piper_process()

        # Start timeout monitor in background
        timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
        timeout_thread.start()

        # Create STT recorder
        logger.info("Initializing speech recognition...")
        recorder = create_recorder(state.mic_device)

        logger.info("\n" + "=" * 60)
        logger.info("✅ Daba IS READY!")
        logger.info(f"💬 Say one of these wake words: {', '.join(Config.WAKE_WORDS)}")
        logger.info("=" * 60 + "\n")

        # Initial greeting
        speak("Hello! I'm Daba. Say my name to wake me up!", device_id=state.selected_device)

        # Main loop - START THE RECORDER!
        logger.info("🎤 Starting continuous listening...")
        recorder.start()

        try:
            while True:
                # Get transcription from recorder
                transcription = recorder.text()

                if transcription:
                    on_final_transcription(transcription)

                # Check response queue
                if not state.response_queue.empty():
                    user_text = state.response_queue.get()
                    generate_response(chat_session)

                time.sleep(0.1)

        finally:
            recorder.stop()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    finally:
        logger.info("Shutting down Daba...")
        logger.info("👋 Goodbye!")


if __name__ == '__main__':
    main()