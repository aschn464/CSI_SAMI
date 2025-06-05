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
import subprocess
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import queue
from queue import Empty

language = "en"

os.environ["OLLAMA_MODELS"] = os.path.abspath("ollama/models")
conversation_history = ""

arduino_port='COM6'
baud_rate=115200
joint_config_file='config/Joint_config.json'
emote_file='config/Emote.json'
audio_folder='audio'
starting_voice='Matt'
audio_file_encoding='.mp3'

dir_path = "emotes"
available_emotes = []
for json_file in [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]:
    available_emotes.append("emotes/"+json_file)
    print("emotes/"+json_file)

with open(emote_file, 'r') as file:
    data = json.load(file)
emote_mapping = data["Emotes"]

with open(joint_config_file, 'r') as file:
    config = json.load(file)
joint_map = {}
for joint in config["JointConfig"]:
    joint_map[joint["JointName"]] = joint["JointID"]

full_joint_config = None
with open(joint_config_file, 'r') as f:
    full_joint_config = json.load(f)['JointConfig']
full_joint_map = {joint['JointName']: joint for joint in full_joint_config}

qL = queue.Queue()
qR = queue.Queue()

print(available_emotes)
print(emote_mapping)
print(joint_map)
print(full_joint_config)
print(full_joint_map)

mic_names = sr.Microphone.list_microphone_names()
print("Available Microphones:")
for i, name in enumerate(mic_names):
    print(f"{i}: {name}")
mic_index = int(input("Enter the index of the microphone you want to use: "))

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
    #print("Sent joint command: ", bytearray(packet))
    qR.put(["Joint", str(bytearray(packet))])

def send_emote(ser, emote_id):
    packet = [0x3C, 0x45, emote_id, 0x3E]
    ser.write(bytearray(packet))
    #print("Sent emote command: ", bytearray(packet))
    qR.put(["Emote", str(bytearray(packet))])
    time.sleep(1)

def get_joint_id(joint_name):
    return joint_map.get(joint_name, 0)
    
def read_json(ser, filename, stop_event):
    print("Running gesture: " + str(filename))
    qR.put(["Action", "Running gesture: " + str(filename)])
    with open(filename, 'r') as file:
        data = json.load(file)
    for keyframe in data["Keyframes"]:
        if stop_event.is_set():
            print("Stopping gesture early.")
            break
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


class GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSI")
        self.geometry("800x500")

        self.paused = tk.BooleanVar(value=False)
        
        self._create_widgets()
        self._layout_widgets()

        self.console_left.tag_config("bold_red", foreground="red", font=("bold"))
        self.console_left.tag_config("bold_blue", foreground="blue", font=("bold"))

        self.console_right.tag_config("Emote", foreground="red", wrap=None)
        self.console_right.tag_config("Joint", foreground="blue", wrap=None)
        self.console_right.tag_config("Action", font=("bold"))


    def _create_widgets(self):
        # Row 1: Title Label
        self.title_label = tk.Label(self, text="CSI SAMI CONSOLE", font=("Arial", 16, "bold"))

        # Row 2: Dropdown menu
        self.dropdown_var = tk.StringVar()
        self.dropdown_menu = ttk.Combobox(self, textvariable=self.dropdown_var, state="readonly")
        self.dropdown_menu['values'] = mic_names
        self.dropdown_menu.current(0)
        self.switch = ttk.Checkbutton(self, text="Pause", variable=self.paused, command=self.toggle_pause)

        # Row 3: Two side-by-side consoles
        self.console_left = ScrolledText(self, wrap=tk.WORD, width=50, height=20, bg="#FDFDFD", font=("Segoe UI", 12))
        self.console_right = ScrolledText(self, wrap=None, width=50, height=20, bg="#FDFDFD", font=("Segoe UI", 12))

        # Example: insert starter text
        self.console_left.insert(tk.END, "Dialogue Log...\n")
        self.console_right.insert(tk.END, "Console Log...\n")

    def insert_console_left(self, message):
        self.console_left.insert(tk.END, time.strftime("%H:%M:%S ", time.localtime(time.time())), "bold")
        if message[0] == "LLM":
            self.console_left.insert(tk.END, "SAMI says: ", "bold_red")
            self.console_left.insert(tk.END, message[1] + '\n')
        elif message[0] == "user":
            self.console_left.insert(tk.END, "You say: ", "bold_blue")
            self.console_left.insert(tk.END, message[1] + '\n')
        else:
            pass
        self.console_left.see('end')

    def insert_console_right(self, message):
        self.console_right.insert(tk.END, time.strftime("%H:%M:%S ", time.localtime(time.time())), "bold")
        if message[0] == "Emote" or message[0] == "Joint":
            self.console_right.insert(tk.END, "Sent " + message[0] + " command: ", message[0])
            self.console_right.insert(tk.END, message[1] + '\n')
        if message[0] == "Action":
            self.console_right.insert(tk.END, message[1] + '\n', message[0])
        else:
            pass
        self.console_right.see('end')

    def _layout_widgets(self):
        # Grid layout with uniform rows
        self.grid_rowconfigure(2, weight=1)  # row 3 stretches vertically
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.title_label.grid(row=0, column=0, columnspan=2, pady=10)
        self.dropdown_menu.grid(row=1, column=0, pady=5, sticky="ew", padx=20)
        self.switch.grid(row=1, column=1)
        self.console_left.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.console_right.grid(row=2, column=1, padx=(10, 20), pady=10, sticky="nsew")

    def toggle_pause(self):
        self.pause = self.paused.get()

    def check_queue(self):
        try:
            while True:
                self.insert_console_left(qL.get_nowait())
        except Empty:
            pass
        try:
            while True:
                self.insert_console_right(qR.get_nowait())
        except Empty:
            pass
        self.after(50, self.check_queue)


def gameloop(exit_flag, paused):
    while not exit_flag.is_set():
        ser = initialize_serial_connection()
        while paused.get():
            pass
        if not exit_flag.is_set():
            stop_event = Event()
            emote_thread = threading.Thread(target=read_json, args=(ser, "config/Listening.json", stop_event))
            emote_thread.start()
            query = speech_to_text(mic_index)
            stop_event.set()
            time.sleep(0.05)
            emote_thread.join()

            print('\033[F' + '\033[1m' + "You say: " + '\033[0m' + query + '\033[K' + '\n', end='\033[K')
            qL.put(["user", query])
        while paused.get():
            pass
        if not exit_flag.is_set():
            stop_event = Event()
            emote_thread = threading.Thread(target=read_json, args=(ser, "config/Thinking.json", stop_event))
            emote_thread.start()
            response = transmit_prompt(query)
            stop_event.set()
            time.sleep(0.05)
            emote_thread.join()

            print('\033[1m' + "SAMI says: " + '\033[0m' + response + '\033[K')
            qL.put(["LLM", response])
        while paused.get():
            pass
        if not exit_flag.is_set():
            stop_event = Event()
            emote_thread = threading.Thread(target=read_json, args=(ser, get_gesture(response), stop_event))
            emote_thread.start()
            text_to_speech(response)        
            stop_event.set()
            time.sleep(0.05)
            emote_thread.join()

        read_json(ser, "config/home.json", Event())
        time.sleep(1.05)

        close_connection(ser)
        ser = None

def main():
    exit_flag = Event()
    app = GUI()
    MUD_thread = threading.Thread(target=gameloop,args=(exit_flag,app.paused))
    MUD_thread.start()
    try:
        app.after(50, app.check_queue)
        app.mainloop()
    except KeyboardInterrupt:
        print('\x1B[3m' + "Exited by user." + '\x1B[0m' + '\033[K')
        qR.put(["Action", "Exited by user."])
        exit_flag.set()
        MUD_thread.join()

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
    qR.put(["Action", "Sending prompt to model..."])

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
