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

language = "en"

os.environ["OLLAMA_MODELS"] = os.path.abspath("ollama/models")
conversation_history = ""

arduino_port='COM6'
baud_rate=115200
joint_config_file='Joint_config.json'
emote_file='Emote.json'
audio_folder='audio'
starting_voice='Matt'
audio_file_encoding='.mp3'

with open(joint_config_file, 'r') as file:
    config = json.load(file)
joint_map = {}
for joint in config["JointConfig"]:
    joint_map[joint["JointName"]] = joint["JointID"]

full_joint_config = None
emote_mapping = None
with open(joint_config_file, 'r') as f:
    full_joint_config = json.load(f)['JointConfig']
full_joint_map = {joint['JointName']: joint for joint in full_joint_config}
with open(emote_file, 'r') as file:
    data = json.load(file)
    emote_mapping = data["Emotes"]

#print(joint_map)
#print(full_joint_config)
#print(emote_mapping)

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

def go_home(ser):
        print("Resetting Gesture")
        joint_ids = [joint['JointID'] for joint in full_joint_config]
        home_angles = [joint['HomeAngle'] for joint in full_joint_config]
        send_joint_command(ser, joint_ids, home_angles, 1)

def main():
    print("Available Microphones:")
    for i, name in enumerate(mic_names):
        print(f"{i}: {name}")
    mic_index = int(input("Enter the index of the microphone you want to use: "))
    
    ser = initialize_serial_connection()
    
    while True:
        try:
            query = speech_to_text(mic_index)
            print(query)
            response = transmit_prompt(query)
            print(response)
            stop_event = Event()
            t1 = threading.Thread(target=text_to_speech, args=(response,))
            t2 = threading.Thread(target=read_json, args=(ser, "explaining.json", stop_event))
            t1.start()
            t2.start()
            t1.join()
            stop_event.set()
            time.sleep(0.05)
            t2.join()

            go_home(ser)
        except KeyboardInterrupt:
            print("Exited by user.")
            break

    close_connection(ser)

def speech_to_text(mic_index):
    r = sr.Recognizer()
    with sr.Microphone(device_index=mic_index) as source:
        r.adjust_for_ambient_noise(source)
        while True:
            print("Listening...")
            audio = r.listen(source)
            try:
                return r.recognize_google(audio)
            except sr.UnknownValueError:
                print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"API error: {e}")


def transmit_prompt(prompt):
    global conversation_history
    print("Sending prompt to model...")

    conversation_history += f"User: {prompt}\nNarrator:"

    request = generate(model='llama_mud', prompt=conversation_history)
    response = request['response'].strip()

    conversation_history += f" {response}\n"

    return response



def text_to_speech(response):
    from tempfile import NamedTemporaryFile
    import atexit

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
    print("Done Reading")




if __name__ == "__main__":
  main()
