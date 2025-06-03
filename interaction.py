import speech_recognition as sr
# from ollama import Client
from ollama import generate
import os
import time
from gtts import gTTS
import pygame
from tempfile import NamedTemporaryFile
import serial
import json
import threading
from threading import Event
import random


language = "en"

os.environ["OLLAMA_MODELS"] = os.path.abspath("ollama/models")
conversation_history = ""

dir_path = "emotes"

available_emotes = []
for json_file in [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]:
    available_emotes.append("emotes/"+json_file)
    print("emotes/"+json_file)

arduino_port='COM3'
baud_rate=115200
joint_config_file='Joint_config.json'
emote_file='Emote.json'
audio_folder='audio'
starting_voice='Matt'
audio_file_encoding='.mp3'

def load_joint_config(joint_config_file):
    with open(joint_config_file, 'r') as file:
        config = json.load(file)
    joint_map = {}
    for joint in config["JointConfig"]:
        joint_map[joint["JointName"]] = joint["JointID"]
    return joint_map

def load_emote_mapping(emote_file):
    with open(emote_file, 'r') as file:
        data = json.load(file)
    return data["Emotes"]

with open(joint_config_file, 'r') as file:
    config = json.load(file)
joint_map = {}
for joint in config["JointConfig"]:
    joint_map[joint["JointName"]] = joint["JointID"]

print(joint_map)

emote_mapping = load_emote_mapping(emote_file)

full_joint_config = None
with open(joint_config_file, 'r') as f:
    full_joint_config = json.load(f)['JointConfig']
full_joint_map = {joint['JointName']: joint for joint in full_joint_config}

mic_names = sr.Microphone.list_microphone_names()
url = "http://localhost:11434/api/chat"
SAVE_FILE = 'game_so_far.txt'
story_context = ""
full_story = ""
ser = None

########################################################################
# connect to robot controller
########################################################################
def initialize_serial_connection():
    try:
        ser = serial.Serial(arduino_port, baud_rate, timeout=1)
        time.sleep(2)
        print("Serial connection established.")
        packet = [0x3C, 0x50, 0x01, 0x45, 0x3E]
        ser.write(bytearray(packet))
        print("Sent packet:", bytearray(packet))
        if ser.in_waiting > 0:
            msg = ser.readline().decode()
            print("Arduino response:", msg)
        return ser
    except serial.SerialException as e:
        print("Error connecting to Arduino:", e)

def close_connection(ser):
    if ser:
        ser.close()
        print("Serial connection closed.")

def send_joint_command(ser, joint_ids, joint_angles, joint_time):
    if len(joint_ids) != len(joint_angles):
        raise ValueError("Mismatch in joint IDs and angles.")
    packet = [0x3C, 0x4A, joint_time]
    for jid, angle in zip(joint_ids, joint_angles):
        packet.extend([jid, angle])
    packet.append(0x3E)
    ser.write(bytearray(packet))
    print("Sent joint command:", bytearray(packet))

def send_emote(ser, emote_id):
    packet = [0x3C, 0x45, emote_id, 0x3E]
    ser.write(bytearray(packet))
    print("Sent emote command:", bytearray(packet))
    time.sleep(1)

def get_joint_id(joint_name):
    return joint_map.get(joint_name, 0)
    
def read_json(ser, filename, stop_event):
    print("Running gesture: " + str(filename))
    with open(filename, 'r') as file:
        data = json.load(file)
    for keyframe in data["Keyframes"]:
        if stop_event.is_set():
            print("Stopping gesture early.")
            break

        # Process Audio if enabled.
        #if keyframe.get("HasAudio") == "True":
            # Use "AudioClip" if provided; otherwise fall back to the "Expression" or a default.
            # audio_clip = keyframe.get("AudioClip", keyframe.get("Expression", "default_audio"))
            # print("Processing audio keyframe – playing:", audio_clip)
            #audio_manager.send_audio(audio_clip)
        # Process Emote if enabled.
        if keyframe.get("HasEmote") == "True":
            expression = keyframe.get("Expression", "Neutral")
            emote_value = emote_mapping.get(expression, 0)
            send_emote(ser, emote_value)
        # Process Joint Commands if enabled.
        if keyframe.get("HasJoints") == "True":
            joint_ids = []
            joint_angles = []
            joint_time = keyframe.get("JointMoveTime", 1)
            for joint in keyframe["JointAngles"]:
                joint_ids.append(get_joint_id(joint["Joint"]))
                joint_angles.append(joint["Angle"])
            send_joint_command(ser, joint_ids, joint_angles, joint_time)
        time.sleep(keyframe.get("WaitTime", 1000) / 1000)

def get_gesture(response):
    #model = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base")
    #emotion = model(response)    
    #print(emotion)
    #return available_emotes[random.randint(0, len(available_emotes) - 1)]
    return available_emotes[1]

def do_actions(ser, response):
        stop_event = Event()
        t1 = threading.Thread(target=text_to_speech, args=(response,))
        t2 = threading.Thread(target=read_json, args=(ser, get_gesture(response), stop_event))
        t1.start()
        t2.start()
        t1.join()
        stop_event.set()
        time.sleep(0.05)
        t2.join()
        t1 = None
        t2 = None
        read_json(ser, "home.json", Event())

def main():
    print("Available Microphones:")
    for i, name in enumerate(mic_names):
        if "mic" in name.lower():
            print(f"{i}: {name}")
    mic_index = int(input("Enter the index of the microphone you want to use: "))
    
    while True:
        try:
            ser = initialize_serial_connection()
            stop_event = Event()
            t3 = threading.Thread(target=read_json, args=(ser, "Listening.json", stop_event))
            t3.start()
            query = speech_to_text(mic_index)
            stop_event.set()
            time.sleep(0.05)
            t3.join()
            t3 = None

            print('\033[F' + '\033[1m' + "You say: " + '\033[0m' + query + '\033[K' + '\n', end='\033[K')

            stop_event = Event()
            t4 = threading.Thread(target=read_json, args=(ser, "Thinking.json", stop_event))
            t4.start()
            response = transmit_prompt(query)
            stop_event.set()
            time.sleep(0.05)
            t4.join()
            t4 = None

            print('\033[1m' + "SAMI says: " + '\033[0m' + response + '\033[K')
            
            do_actions(ser, response)

            time.sleep(1.05)
            close_connection(ser)
            ser = None

        except KeyboardInterrupt:
            print('\x1B[3m' + "Exited by user." + '\x1B[0m' + '\033[K')
            break



def speech_to_text(mic_index):
    r = sr.Recognizer()
    with sr.Microphone(device_index=mic_index) as source:
        r.adjust_for_ambient_noise(source)
        failures = 0
        while True:
            print("Listening...")
            audio = r.listen(source)
            try:
                return r.recognize_google(audio)
            except sr.UnknownValueError:
                failures = failures + 1
                print("Could not understand audio. Current failures: " + str(failures), end='\033[F')
            except sr.RequestError as e:
                print(f"API error: {e}")


def transmit_prompt(prompt):
    global conversation_history
    print("Sending prompt to model...", end='\r')

    conversation_history += f"User: {prompt}\nNarrator:"

    request = generate(model='llama_mud', prompt=conversation_history)
    response = request['response'].strip()

    conversation_history += f" {response}\n"

    return response



def text_to_speech(response):
    ttsobj = gTTS(text=response, lang=language, slow=False)
    with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        ttsobj.save(temp_file.name)
        filename = temp_file.name

    try:
        pygame.mixer.quit()
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.5)

    finally:
        pygame.mixer.music.stop()
        pygame.mixer.quit()

        for _ in range(10):
            try:
                os.remove(filename)
                break
            except PermissionError:
                time.sleep(0.2)




if __name__ == "__main__":
  main()
