# 🤖 Daba - AI Desktop Assistant

Daba is an advanced AI-powered desktop assistant developed using Python.  
It supports wake word detection, speech recognition, offline and online AI models, desktop automation, face authentication, emotion detection, and Arduino hardware integration.

This project was created as a Final Year Project for Bachelor of Technology in Computer Science Engineering.

---

# ✨ Features

- 🎤 Wake Word Detection
- 🗣️ Real-time Speech Recognition
- 🔊 Text-to-Speech using Piper TTS
- 🤖 Gemini AI Integration
- 📴 Offline AI using Ollama + TinyLlama
- 😀 Emotion Detection & Arduino Control
- 🔐 Face Authentication System
- 🎙️ Voice Authentication
- 📂 Open & Close Desktop Applications
- 🧠 Smart Fuzzy Wake Word Matching
- ⚡ Fast Realtime Response
- 🖥️ Desktop Automation
- 📁 File Searching System
- 🔌 Hardware Communication using Arduino

---

# 🛠️ Technologies Used

- Python 3.12
- Google Gemini API
- Ollama
- TinyLlama
- RealtimeSTT
- Piper TTS
- OpenCV
- face_recognition
- sounddevice
- pyserial
- RapidFuzz
- NumPy
- Arduino

---

# 📁 Project Structure

```bash
Daba-AI-Assistant/
│
├── main.py
├── Neo.py
├── register.py
├── face_auth.py
├── scan_open.py
├── ollama_test.py
├── test.gemini.py
├── harware.py
├── tet_hardware.py
│
├── output/
├── models/
├── piper/
│
├── user_faces.pkl
├── neo.log
├── README.md
```

---

# 🚀 Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/Daba-AI-Assistant.git

cd Daba-AI-Assistant
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate virtual environment:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

---

## 3️⃣ Install Required Libraries

```bash
pip install google-generativeai
pip install sounddevice
pip install soundfile
pip install RealtimeSTT
pip install rapidfuzz
pip install pyserial
pip install numpy
pip install opencv-python
pip install face_recognition
pip install pygetwindow
pip install requests
```

Or use:

```bash
pip install -r requirements.txt
```

---

# 🤖 Gemini API Setup

## Windows

```bash
set GEMINI_API_KEY=your_api_key
```

## Linux / Mac

```bash
export GEMINI_API_KEY=your_api_key
```

---

# 📴 Ollama Offline AI Setup

## Install Ollama

Download from:

https://ollama.com/

---

## Pull TinyLlama Model

```bash
ollama pull tinyllama
```

---

## Start Ollama

```bash
ollama serve
```

---

# 🔊 Piper TTS Setup

Download Piper TTS:

https://github.com/rhasspy/piper

Place these files inside the `piper/` folder:

```bash
piper/
 ├── piper.exe
 └── models/
      └── en_US-ryan-high.onnx
```

---

# 🔐 Face Authentication Setup

Run:

```bash
python register.py
```

This stores your face encodings for authentication.

---

# ▶️ Run Project

```bash
python main.py
```

or

```bash
python tet_hardware
```

---

# 🎤 Wake Words

Examples:

- Hey Daba
- Daba
- Wake up Daba

---

# 😴 Sleep Commands

Examples:

- Go to sleep
- Stop listening
- Bye
- Good night Daba

---

# 😀 Arduino Emotion Commands

The assistant can send emotion commands to Arduino.

Supported emotions:

- happy
- sad
- angry
- confused
- laugh
- wave
- nod
- shrug

These can control:

- LEDs
- Servo motors
- Robot face expressions
- Displays

---

# 📂 Desktop Automation Features

Daba can:

- Open applications
- Close applications
- Search files
- Open files
- Control desktop windows

Supported applications include:

- Chrome
- VS Code
- Spotify
- Discord
- VLC
- Edge
- Firefox
- Notepad
- Calculator

---

# 🧠 AI Modes

## 🌐 Online Mode

Uses:

- Google Gemini 2.5 Flash

## 📴 Offline Mode

Uses:

- Ollama
- TinyLlama

---

# 📸 Face Authentication

Built using:

- OpenCV
- face_recognition

Supports:

- Multiple face samples
- Real-time face verification
- Secure access control

---

# ⚡ Future Improvements

- GUI Interface
- Mobile App Integration
- Smart Home Control
- Multi-language Support
- AI Vision Features
- Memory System
- Better Voice Cloning
- Custom AI Training

---

# 👨‍💻 Author

Deepak Chandola
Aman Bhandari

---

# 📜 License

This project is developed for educational and research purposes.

---

# ⭐ Acknowledgements

- Google Gemini
- Ollama
- Piper TTS
- OpenCV
- RealtimeSTT
- Python Community

---
---

#  Harware_Code
will be shared soon !!!
---

# 📷 Demo and Screenshots


Example:
<img width="719" height="1600" alt="WhatsApp Image 2026-05-22 at 12 57 42 AM" src="https://github.com/user-attachments/assets/375fe184-2504-456f-902e-8471423c8430" />

https://github.com/user-attachments/assets/0d2cb48d-2f89-48ce-8d01-1a3da9f77a48


<img width="963" height="1280" alt="WhatsApp Image 2026-05-11 at 12 21 24 PM" src="https://github.com/user-attachments/assets/ca2ba901-153b-49c8-9659-f9d09cb2729b" />
<img width="963" height="1280" alt="WhatsApp Image 2026-05-11 at 12 19 37 PM" src="https://github.com/user-attachments/assets/7e2c8a93-2b1c-4470-bb31-a42df12a179f" />
<img width="719" height="1600" alt="WhatsApp Image 2026-05-11 at 12 18 12 PM" src="https://github.com/user-attachments/assets/fc82ac74-fcba-4dd2-93ad-2c90b12d5f1b" />
<img width="960" height="1280" alt="WhatsApp Image 2026-05-11 at 12 14 13 PM" src="https://github.com/user-attachments/assets/d413f3df-5cca-4514-90c9-0c104758392d" />

