from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import numpy as np

# Initialize encoder
encoder = VoiceEncoder()

# Load owner's voice sample
owner_wav = preprocess_wav(Path("your own audio wav file"))
owner_embedding = encoder.embed_utterance(owner_wav)

def verify_speaker(audio_file):
    """
    Compare incoming voice with owner's voice
    """

    test_wav = preprocess_wav(Path(audio_file))
    test_embedding = encoder.embed_utterance(test_wav)

    similarity = np.dot(owner_embedding, test_embedding)

    print(f"Voice similarity score: {similarity}")

    if similarity > 0.75:
        print("✅ Authorized user")
        return True
    else:
        print("❌ Unauthorized user")
        return False
