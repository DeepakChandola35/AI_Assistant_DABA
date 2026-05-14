import subprocess

OLLAMA_PATH = r"C:\Users\deepa\AppData\Local\Programs\Ollama\ollama.exe"
MODEL_NAME = "tinyllama"   # you can change to "tinyllama" if needed


def test_ollama():
    try:
        print("🚀 Testing Ollama...\n")

        # ✅ Non-interactive call (IMPORTANT FIX)
        result = subprocess.run(
            [
                OLLAMA_PATH,
                "run",
                MODEL_NAME,
                "Hello, how are you?"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        print("🔢 Return Code:", result.returncode)

        print("\n📤 STDOUT (Response):")
        print(result.stdout.strip() if result.stdout else "EMPTY")

        print("\n⚠️ STDERR (Errors):")
        print(result.stderr.strip() if result.stderr else "NONE")

        # ✅ Final check
        if result.returncode == 0 and result.stdout.strip():
            print("\n✅ SUCCESS: Ollama is WORKING perfectly!")
        else:
            print("\n❌ FAILURE: Ollama is NOT working correctly!")

    except subprocess.TimeoutExpired:
        print("\n⏳ ERROR: Ollama timed out (model too slow or not loaded)")
    except FileNotFoundError:
        print("\n❌ ERROR: Ollama executable not found (check path)")
    except Exception as e:
        print("\n❌ UNKNOWN ERROR:")
        print(e)


if __name__ == "__main__":
    test_ollama()