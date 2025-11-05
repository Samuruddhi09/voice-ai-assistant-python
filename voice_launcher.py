import speech_recognition as sr
import subprocess
import difflib
import time
import requests
import webbrowser
import os

WAKE_WORDS = ["hey bunny", "hi bunny", "hello bunny", "dear bunny"]

FLASK_URL = "http://127.0.0.1:5000"
UI_URL = "http://127.0.0.1:5000/"  

def flask_running():
    try:
        requests.get(FLASK_URL, timeout=0.3)
        return True
    except:
        return False

def launch_flask():
    print("🚀 Starting Flask backend...")
    subprocess.Popen(["python", "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

def open_ui():
    print("🌐 Opening Bunny UI...")
    
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    #  open as chrome app window
    if os.path.exists(chrome_path):
        subprocess.Popen([chrome_path, f"--app={UI_URL}"])
    else:
        webbrowser.open(UI_URL)

def launch_bunny():
    if not flask_running():
        launch_flask()
    open_ui()

def listen_for_hotword():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎧 Listening for 'Hey Bunny'...")
    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source)

        try:
            heard = recognizer.recognize_google(audio).lower()
            print(f"🗣️ Heard: {heard}")

            #  fuzzy match wake word
            match = difflib.get_close_matches(heard, WAKE_WORDS, n=1, cutoff=0.7)
            if match:
                print(f"Wake word recognized: {match[0]}")
                launch_bunny()
                return

        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"⚠️ Voice Error: {e}")

if __name__ == "__main__":
    listen_for_hotword()
