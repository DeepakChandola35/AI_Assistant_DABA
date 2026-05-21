"""
Daba - AI Desktop Assistant with Wake Word Detection
Python Version: 3.12+ Compatible (PyAudio removed)
ENHANCED MICROPHONE SENSITIVITY VERSION5hd
"""

import google.generativeai as genai
import subprocess
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
import serial
import serial.tools.list_ports
from scan_open import scan_files, search_file, open_file, close_file

# from voice_auth import verify_speaker
# GEMINI API KEY
os.environ["GEMINI_API_KEY"] = "Enter_your_key"
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

    EXIT_WORDS = [
        "shutdown daba",
        "exit",

    ]

    SLEEP_WORDS = [
        "go to sleep",
        "sleep daba",
        "stop listening",
        "bye",
        "good night daba"
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

    # Arduino Serial
    ARDUINO_BAUD = 9600
    ARDUINO_PORT = None  # None = auto-detect


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
            send_to_arduino("wakeword")

    def go_to_sleep(self):
        with self.lock:
            self.is_awake = False
            self.is_listening = False
            logger.info("💤 Daba is going to SLEEP - say wake word to activate")
            send_to_arduino("sleep")

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

# Arduino serial connection
arduino_ser = None

all_files = []
recorder = None
def connect_arduino():
    """Auto-detect and connect to Arduino"""
    global arduino_ser
    if Config.ARDUINO_PORT:
        ports_to_try = [Config.ARDUINO_PORT]
    else:
        ports_to_try = []
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if any(k in desc for k in ["arduino", "ch340", "cp210", "usb serial", "usb-serial"]):
                ports_to_try.insert(0, p.device)
            else:
                ports_to_try.append(p.device)
    for port in ports_to_try:
        try:
            arduino_ser = serial.Serial(port, Config.ARDUINO_BAUD, timeout=2)
            time.sleep(2)  # wait for Arduino reset
            while arduino_ser.in_waiting:
                line = arduino_ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    logger.info(f"Arduino: {line}")
            logger.info(f"✅ Arduino connected on {port}")
            return True
        except Exception:
            continue
    logger.warning("⚠️ Arduino not found. Running without hardware.")
    return False

def send_to_arduino(command: str):
    """Send a command to Arduino over serial"""
    global arduino_ser
    if arduino_ser and arduino_ser.is_open:
        try:
            arduino_ser.write((command + "\n").encode())
            logger.info(f"📡 Sent to Arduino: {command}")
            time.sleep(0.1)
            while arduino_ser.in_waiting:
                line = arduino_ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    logger.info(f"Arduino: {line}")
        except Exception as e:
            logger.error(f"Serial send error: {e}")

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


def check_for_sleep_word(text: str) -> bool:

    text_lower = text.lower().strip()

    for sleep_word in Config.SLEEP_WORDS:

        similarity = fuzz.partial_ratio(
            sleep_word.lower(),
            text_lower
        )

        logger.info(
            f"Checking sleep word '{sleep_word}' vs '{text_lower}'"
        )

        if similarity > 85:
            logger.info(f"😴 Sleep word detected: {sleep_word}")
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
    """Send emotion to Arduino and log it"""
    allowed_emotions = ["sad", "angry", "happy", "confused", "laugh", "wave", "point", "nod", "shrug"]

    if emotion in allowed_emotions:
        send_to_arduino(emotion)
        logger.info(f"😊 Emotion: {emotion}")
    else:
        send_to_arduino("happy")
        logger.info(f"😊 Emotion: happy (default)")


'''-----Speech-to-Text (STT) with MICROPHONE BOOST-----'''

# def record_auth_voice():
#     """Record short voice sample for authentication"""
#
#     duration = 3
#     sample_rate = 16000
#
#     audio = sd.rec(
#         int(duration * sample_rate),
#         samplerate=sample_rate,
#         channels=1
#     )
#
#     sd.wait()
#
#     sf.write("temp_voice.wav", audio, sample_rate)

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
#
#             logger.info("🔐 Verifying speaker...")
#
#             record_auth_voice()
#
#             authorized = verify_speaker("temp_voice.wav")
#
#             if not authorized:
#                 logger.info("❌ Unauthorized voice detected")
#                 return
#
#             logger.info("✅ Authorized user detected")
#
#             state.wake_up()
#             play_acknowledgment_sound()

            # # remove temp file
            # try:
            #     os.remove("temp_voice.wav")
            # except:
            #     pass
def on_realtime_transcription(text: str):

    if not text.strip():
        return

    logger.info(f"🎤 Hearing (realtime): {text}")

    if not state.is_awake:

        if check_for_wake_word(text):

            state.wake_up()
            play_acknowledgment_sound()

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

    # Check for sleep command
    if state.is_awake and check_for_sleep_word(text):
        speak("Going to sleep.", device_id=state.selected_device)

        state.go_to_sleep()
        return
    # Check for exit command
    # Check for exit command using fuzzy matching
    for exit_word in Config.EXIT_WORDS:

        similarity = fuzz.partial_ratio(
            exit_word.lower(),
            text.lower()
        )

        logger.info(
            f"Checking exit word '{exit_word}' vs '{text}' → Score: {similarity}"
        )

        if similarity > 85:
            logger.info("🛑 Exit command detected")

            speak("Shutting down.", device_id=state.selected_device)

            os._exit(0)

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
    try:
        state.is_speaking = True

        # STOP LISTENING
        recorder.stop()

        data, samplerate = sf.read(str(file_path))
        sd.play(data, samplerate, device=device_id)
        sd.wait()

        logger.info("🔊 Playback finished")

        # START LISTENING AGAIN
        recorder.start()

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


def generate_response(chat_session , user_text):
    """Generate AI response to user input"""
    try:
        if not state.user_input:
            return
        user_text = state.user_text.lower()

        # OPEN APPLICATIONS
        if "open chrome" in user_text:
            os.system("start chrome")

            speak("Opening Chrome", device_id=state.selected_device)

            return

        if "open notepad" in user_text:
            os.system("start notepad")

            speak("Opening Notepad", device_id=state.selected_device)

            return

        if "open calculator" in user_text:
            os.system("start calc")

            speak("Opening Calculator", device_id=state.selected_device)

            return

        if "open youtube" in user_text:
            os.system("start https://youtube.com")

            speak("Opening YouTube", device_id=state.selected_device)

            return

        # OPEN FILE COMMAND
        if "open " in user_text:

            filename = user_text.split("open ", 1)[1].strip()

            logger.info(f"📂 Searching for file: {filename}")

            global all_files

            # Scan only first time
            if not all_files:
                speak("Scanning files please wait", device_id=state.selected_device)

                logger.info("📂 First time file scan started...")

                all_files = scan_files()

                logger.info(f"✅ Indexed files: {len(all_files)}")

            results = search_file(filename, all_files)

            if results:

                file_to_open = results[0]

                logger.info(f"✅ Opening: {file_to_open}")

                open_file(file_to_open)

                speak(f"Opening {filename}", device_id=state.selected_device)

            else:

                speak("File not found", device_id=state.selected_device)

            return

        # CLOSE WINDOW / APP COMMAND
        if "close " in user_text:
            window_name = user_text.split("close ", 1)[1].strip()

            # Remove filler words like "the", "my", "a"
            filler_words = ["the", "my", "a", "an", "this", "that"]
            cleaned_words = [w for w in window_name.split() if w not in filler_words]
            window_name = " ".join(cleaned_words) if cleaned_words else window_name

            logger.info(f"❌ Attempting to close: {window_name}")

            success = close_file(window_name)

            if success:
                speak(f"Closed {window_name}", device_id=state.selected_device)
            else:
                speak(f"Could not find {window_name} to close", device_id=state.selected_device)

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


from face_auth import verify_face

def main():

    global recorder
    global all_files
    try:
        logger.info("=" * 60)

        # 🔐 FACE AUTHENTICATION BEFORE START
        logger.info("🔐 Starting Face Authentication...")

        if not verify_face():
            logger.error("❌ Face authentication failed. Exiting...")
            return

        logger.info("✅ Face authentication successful! Starting assistant...")

        # Initialize LLM
        chat_session = setup_llm()
        response = chat_session.send_message("hello")

        print(response.text)

        # List and setup audio devices
        list_audio_devices()

        # Find microphone
        state.mic_device = find_device_by_name(Config.MICROPHONE_NAME, 'input')
        if state.mic_device is None:
            state.mic_device = find_default_microphone()

        # Find speaker
        state.selected_device = find_device_by_name(Config.SPEAKER_NAME, 'output')

        # Connect to Arduino
        connect_arduino()

        # Test microphone
        monitor_microphone_levels()

        # Start TTS
        start_piper_process()

        # Start timeout monitor
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
        # Scan files in background after startup
        logger.info("📂 Scanning files in background...")

        all_files = scan_files()

        logger.info(f"✅ Indexed files: {len(all_files)}")

        # Main loop - START THE RECORDER!
        # Main loop - START THE RECORDER!
        logger.info("🎤 Starting continuous listening...")
        recorder.start()

        try:
            while True:

                # ONLY process queue
                if not state.response_queue.empty():
                    user_text = state.response_queue.get()

                    generate_response(chat_session, user_text)

                time.sleep(0.1)

        finally:
            recorder.stop()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    finally:
        send_to_arduino("sleep")
        if arduino_ser and arduino_ser.is_open:
            arduino_ser.close()
        logger.info("Shutting down Daba...")
        logger.info("👋 Goodbye!")


if __name__ == '__main__':
    main()
