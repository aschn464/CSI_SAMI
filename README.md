# CSI_SAMI
Collaborative Storytelling Interaction (CSI) system for the [SAMI robot](https://github.com/shareresearchteam/SAMI-Robot). The team at CSI - Corvallis aims to create an immersive, AI generated, role playing game (RPG) using a custom humanoid robot. 

# Project Info
Table of Contents for easy page location:
1. [What We Aim To Do](#what-we-aim-to-do)
2. [Who Is This SAMI Robot](#who-is-this-sami-robot)
3. [How It Came Together](#how-it-came-together)
4. [What Are TTRPG and MUD Games?](#what-are-ttrpg-and-mud-games)
5. [Iterations](#iterations)
6. [Making it Work Together](#making-it-work-together)
7. [Initial Refinement](#initial-refinement)
8. [Additional Refinement](#additional-refinement)
9. [Final Product](#final-product)

# What We Aim To Do
As mentioned above, CSI-Corvallis aims to create an immersive, AI generated RPG using a custom humanoid robot, but what does that really mean? For our project we wanted to create an entire pipeline for the robot to actively receive, process and output information in a way that is interactive for the user. We instructed our robot to receive an audio line while gesturing that it is listening, process the information while doing a thinking pose, then speak back a response while gesturing an applicable response. This whole system allows for a seamless experience using our robot. 

# Who Is This SAMI Robot?
[SAMI (Social Animated Mechanical Interlocutor)](https://github.com/shareresearchteam/SAMI-Robot) is a robot developed at OSU as part of an NIH grant. SAMI was designed to be cost effective with a (comparatively) simplified design so that it can be used as a test bed for different research projects.

# How It Came Together
The project began as a design exploration for the ROB 421 Applied Robotics course at Oregon State University. The initial assignment was to integrate LLM functionality into the SAMI robot system, allowing the user to "converse" with the robot. We used the assignment as an opportunity to explore the development of an LLM-based roleplaying game, with elements of the TTRPG and MUD games that we enjoy playing ourselves. Our prototype had so much potential that we decided to develop it into our final project for the course. You can view our design iterations and our final project demonstration. 

We believe this system has potential to not only bring a fun game to the SAMI robot but also to provide an accessible solo gaming experience in various environments. Roleplaying games can have benefits from enhancing creativity to supplementing cognitive development, and CSI SAMI has the potential to be an accessible option for players in nontraditional or isolated settings.

# What Are TTRPG and MUD Games?
### TTRPG (Table-Top Role Playing Game)
A genre of game where a user creates and controls a character and uses this character to interact with the world. These interactions are facilitated by another player called the "dungeon Master (DM)". Interactions are guided by a set of rules which define the mechanics of interactions and combat. TTRPGs are perhaps best known by the popular game "Dungeons & Dragons".

### MUD (Multi-User Dungeon)
An early example of online, multiplayer game which was usually text-based and allowed the user to explore and interact with the game world and other characters. These games were often set in fantasy or science fiction environments.

# Iterations
For the initial exploration, the team identified two primary challenges:
1. Working with an AI model to develop prompts and story setting
2. Developing a speech-> prompt pipeline

### Choosing an AI Model
After consultation with classmates and instructors who had previous LLM experience, the team decided to utilize with the llama3.2 3B Large Language Model through the Ollama framework. We then worked to engineer a prompt that would strike a balance of "immersive story experience" and "simplicity"; we wanted the story to be engaging but not take the LLM too much time to generate. We also sought to create a "persistent story" where the LLM would remember what had come before and be able to meaningfully develop a story.

### Speech to Text Pipeline
We knew we wanted a player to be able to speak to the robot, convert that players speech to text to feed the LLM, then have to robot speak the text-response back to the player. To accomplish this, the team utilized the following tool sets:
- pygame
- gTTS
- speech_recognition
- pyaudio

# Making it Work Together
The next challenge the team faced was integrating our LLM and speech to response pipeline into a single file. As developed, we could play our game by typing commands into the terminal, and we could speak into a microphone and generate text and vice versa, but we needed to combine all this functionality into a single program. Luckily, we had implemented most of these as actions as individual functions which proved relatively straight forward to combine into a single program.

# Initial Refinement
Now that we had a single program that would allow the user to play our game with SAMI, we began the process of refining the experience:

### Introduce Save State
Most RPG games are played over multiple sessions. As such, we developed the ability for players to save the game so that they might restart from that point at a later date.

### Gesture Integration and Multi-Threading
Our initial code design was single-thread execution: i.e. every action would execute linearly. This early iteration limited interactivity as each process would have to complete before the next one could begin. The first step in creating a more interactive experience was developing multi-threading capability so that several process could be executed simultaneously: namely, gesturing when speaking.

### Additional Behavior Development
If we were giving Sami the ability to gesticulate while talking, we wanted a library of potential gestures to choose from. For an earlier assignment, each member of the team had developed several behaviors for the SAMI robot, and although several of these were easily modified to fit their new use, we also wanted several other.

Check out our [Emotes](https://github.com/aschn464/CSI_SAMI/tree/main/emotes) folder for custom expressive movements, informative media, and associated JSON files.

### Costume Design
If SAMI was going to be telling a story, we wanted them to look the part. The team also began work on several 3-printable costume elements for the robot to wear. Check out the [Accessories]() folder for fantasy-based 3D-printable props.

# Additional Refinement
As the project progressed, we continued to iterate and add additional functionalities, as well as streamlining the existing interaction cycle. Improvements included:
- Integrating an inventory system as a game mechanic, in which the player has a saved set of items that they can access and use throughout the story.
- Adding additional props and costuming to enhance engagement.
- Developing a feature that summarizes past messages in order to reduce response times without sacrificing story integrity.
- Refining the gesture integration process to ensure robot embodiment through synced movements and expressions.

# Final Product
### CSI Final Functionality
- Complete speech to text to speech pipeline - users are able to speak directly to SAMI, and SAMI will speak back to them.

- Optional text-only mode - for users with accessibility conflicts, CSI now has an optional text-only version that doesn't utilize the speech to text to speech pipeline.

- Gesture during interaction - SAMI now performs gestures when listening to the player, when thinking of their response, and when telling their part of the story.

- Story tracking - the entire story is stored in a text file for later reference if desired. Additionally, older interactions are shortened and added to an ongoing "story summary". This summary is used when requesting a response from the LLM instead of the full story in order to keep LLM response generation times to a minimum.

- Interactive inventory system - players are now able to add, remove, and use items they find during their game.

- Accessories - SAMI can now dress for the occasion!

[View our Portfolio website for additional media!](https://sites.google.com/oregonstate.edu/rob421-portfolio/home)
