import sounddevice as sd
import soundfile as sf
from voice_auth import verify_speaker

duration = 5
sample_rate = 16000

def record_test_voice():

    print("🎤 Speak now for authentication...")

    audio = sd.rec(int(duration * sample_rate),
                   samplerate=sample_rate,
                   channels=1)

    sd.wait()

    sf.write("temp_voice.wav", audio, sample_rate)

    print("Recording complete")

def main():

    record_test_voice()

    authorized = verify_speaker("temp_voice.wav")

    if authorized:
        print("Daba: Hello Deepak! How can I help you?")
    else:
        print("Daba: Sorry, I don't recognize your voice.")

if __name__ == "__main__":
    main()