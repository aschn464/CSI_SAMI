import requests
import speech_recognition as sr
# from ollama import Client
# from ollama import generate
import os
import time
from gtts import gTTS
import pygame
from tempfile import NamedTemporaryFile 
import serial
import json
import threading

language = "en"

arduino_port='COM3', 
baud_rate=115200,
joint_config_file='Joint_config.json',
emote_file='Emote.json',
audio_folder='audio',
starting_voice='Matt',
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

joint_map = load_joint_config(joint_config_file)
emote_mapping = load_emote_mapping(emote_file)

mic_names = sr.Microphone.list_microphone_names()
url = "http://localhost:11434/api/chat"
SAVE_FILE = 'game_so_far.txt'
story_context = ""
full_story = ""

########################################################################
# load model
########################################################################
def init_model():
    requests.post(url,
        json={
            "model": "llama3.2:latest",
            "prompt": "load"
        }
                  )


########################################################################
# save game to text file
########################################################################
def save_game(context):
    text_to_speech("Would you like to save your game?")
    response = speech_to_text(mic_index)

    if response in {"yes"}:
        with open(SAVE_FILE, "w", encoding = "utf-8") as f:
            f.write(context)
        return
    
    else:
        return


########################################################################
# if save exists, load it
########################################################################
def load_game():
    saved = load_state()
    if saved and load_saved_game():
        return saved
    else:
        return None
    

########################################################################
# read previous save
########################################################################
def load_state():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return None

########################################################################
# prompt user to choose new or saved game
########################################################################
def load_saved_game():
    while True:
        user_choice = input("Previous game file found. Would you like to continue? (y/n) \n").strip().lower()
        if user_choice in {'y', 'yes'}:
            print("loading saved game... \n")
            return True
        elif user_choice in {'n', 'no'}:
            print ("Beginning new game... \n")
            return False
        else:
            print("Please enter 'yes' or 'no'!")



########################################################################
# 
########################################################################
def main():    
    global story_context
    global mic_index
    global full_story

    story_context = ""
    full_story = ""
    
    print("Available Microphones:")
    for i, name in enumerate(mic_names):
        print(f"{i}: {name}")
    mic_index = int(input("Enter the index of the microphone you want to use: "))

    init_game()
    
    ser = initialize_serial_connection()

    while True:
        try:
            result = game_loop(ser)
            if result == 0:
                break
        except KeyboardInterrupt:
            print("Exited by user")
            break
    

########################################################################
# Begin the game
########################################################################
def init_game():
    global story_context
    
    
    loaded = load_game()
    if loaded: 
        story_context = loaded
    else: 
        story_context = ""

    text_to_speech("Welcome to The Inn, a Collaborative Storytelling Setting. Say begin to start game. Say quit to exit.")



########################################################################
# 
########################################################################
def game_loop(ser):
    global story_context
    
    # get user input
    query = speech_to_text(mic_index)
    
    # check for quit or save
    if query in {"quit", "exit", "save", "save game"}:
        save_game(story_context)
        return 0

    # start measuring time
    start_time = time.time()

    # call transmit prompt
    response = transmit_prompt(query, story_context)

    # stop measuring time
    elapsed_time = time.time() - start_time
    print(f"(Response time: {elapsed_time:.1f}s)")

    
    # call text to speech
    t1 = threading.Thread(text_to_speech(response))
    t2 = threading.Thread(read_json("explaining.json"))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # add messages to full story
    story_context += f"Player: {query}\nNarrator:{response}"



########################################################################
# 
########################################################################
def speech_to_text(mic_index):
    r = sr.Recognizer()
    with sr.Microphone(device_index=mic_index) as source:
        r.adjust_for_ambient_noise(source)
        while True:
            print("Listening...")
            audio = r.listen(source)
            try:
                query = r.recognize_google(audio)
                print(query)
                return query
                #transmit_prompt(query)
            except sr.UnknownValueError:
                print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"API error: {e}")
    

########################################################################
# 
########################################################################
def transmit_prompt(prompt, story_context):
    full_story = f"{story_context}\nPlayer: {prompt}\nNarrator:"

    data = {
        "model": "llama3.2:latest",
        "messages": [
            {
                "role": "user",
                "content": full_story,
            }
        ],
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        print("Error during LLAMA call:", e)
        return "[Error]"
  
########################################################################
# 
########################################################################
def transmit_gesture(gesture):
    print(gesture)
  
########################################################################
# 
########################################################################
def text_to_speech(response):
    print(response)
    
    ttsobj = gTTS(text=response, lang=language, slow=False)
    with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        ttsobj.save(temp_file.name)
        filename = temp_file.name

    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.5)

    pygame.mixer.quit()
    os.remove(filename)

if __name__ == "__main__":
  main()

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

def get_joint_id(self, joint_name):
    return self.joint_map.get(joint_name, 0)
    
def read_json(ser, filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    for keyframe in data["Keyframes"]:
        # Process Audio if enabled.
        if keyframe.get("HasAudio") == "True":
            # Use "AudioClip" if provided; otherwise fall back to the "Expression" or a default.
            audio_clip = keyframe.get("AudioClip", keyframe.get("Expression", "default_audio"))
            print("Processing audio keyframe – playing:", audio_clip)
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
            send_joint_command(joint_ids, joint_angles, joint_time)
        time.sleep(keyframe.get("WaitTime", 1000) / 1000)

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
