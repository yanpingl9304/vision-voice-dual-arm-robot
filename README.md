# 🍹 Unmanned Beverage Station: Vision-and-Voice-Driven Dual-Arm Robot
> **NCKU CSIE Capstone Project**  
> Advised by **Prof. Jenn-Jier Lien** | Department of Computer Science and Information Engineering, National Cheng Kung University  
> *Exhibited at Automation Taipei 2026 (台北國際自動化工業大展)*

---

## 📺 Demonstration Video

[![Watch the Demo Video](https://img.youtube.com/vi/zITnGl25jas/maxresdefault.jpg)](https://youtu.be/zITnGl25jas)

> 🔗 **Video Link:** [Watch the Full Demonstration on YouTube](https://youtu.be/zITnGl25jas)

---

## 📌 Project Overview

**Unmanned Beverage Station** is an intelligent robotic bartender system powered by **ROS 2**. It integrates real-time conversational AI, depth-sensing computer vision, and coordinated dual robotic arms to deliver a hands-free, interactive beverage ordering and preparation experience.

Users can order naturally using voice commands, watch an audio-synchronized interactive avatar respond in real time, and observe dual robotic arms autonomously detect containers, manipulate cups, and prepare drinks.

---

## 👤 My Role & Contributions

**Role:** Core Developer (Speech & Interaction Lead)

I designed and implemented the entire **Conversational AI & HMI Interaction Pipeline**, bridging user voice commands to high-level ROS 2 actions and visual feedback:

* **Speech Processing Pipeline:**
  * Implemented real-time wake-word detection for hands-free system activation.
  * Integrated **Google Cloud STT** (Speech-to-Text) and **Google Cloud TTS** (Text-to-Speech) for low-latency, accurate multi-turn voice interaction.
* **LLM Agent & Function Calling:**
  * Integrated **Google Gemini API** with native function calling to parse customer intent, handle order customizations, and autonomously dispatch structured task parameters via ROS 2 services (`SubmitDrinkOrder.srv`, `ExecuteDrinkTask.action`).
* **Live Avatar Lip-Sync Interaction:**
  * Connected generated speech audio streams with **VTube Studio** via WebSocket protocols to drive live avatar mouth tracking and facial expressions in real time.
* **HMI & System Coordination:**
  * Developed ROS 2 HMI nodes (`voice_interface_node.py`, `rqt_chat_plugin.py`) to manage audio sessions, conversation state transitions, and UI status updates.

---

## 🏗️ System Architecture

```text
[ User Voice Input ]
        │ (Wake Word / Audio Stream)
        ▼
[ Voice Interface Node ] ── Google Cloud STT ──► [ Gemini LLM Agent ]
        │                                                │
        │◄── Google Cloud TTS ◄──── (Function Calling) ──┘
        │
        ├──► WebSocket ──► [ VTube Studio Avatar (Lip-Sync) ]
        │
        └──► ROS 2 Services / Actions (`SubmitDrinkOrder`, `ExecuteDrinkTask`)
                     │
                     ▼
             [ Main Task Node ]
            ┌────────┴────────┐
            ▼                 ▼
[ Perception Pipeline ]   [ Dual-Arm Motion Planning ]
- YOLO Object Detection   - Trajectory Waypoints Execution
- Intel RealSense Depth   - Coordinated Cup Manipulation
- ArUco Marker Tracking
```

---

## 📦 Repository Structure

```text
.
├───drinks_robot
│   ├───config
│   ├───drink_robot
│   │   ├───hmi
│   │   │   └───__pycache__
│   │   ├───manipulation
│   │   ├───perception
│   │   │   └───__pycache__
│   │   └───__pycache__
│   ├───launch
│   ├───resource
│   │   └───WakeWord
│   ├───test
│   └───tmp_src
│       ├───cup_aruco
│       └───__MACOSX
│           └───cup_aruco
└───drinks_robot_interface
    ├───action
    └───srv
```

---

## 🛠️ Tech Stack

* **Robotics & Middleware:** ROS 2, Linux (Ubuntu)
* **Speech & Conversational AI:** Google Cloud Speech-to-Text, Google Cloud Text-to-Speech, openWakeWord, Google Gemini API
* **Avatar & HMI:** VTube Studio WebSocket API, PyQt / Rqt
* **Perception & Vision:** OpenCV, YOLO, Intel RealSense Depth Camera, ArUco Marker Tracking
* **Languages:** Python

---

## 👥 Team & Acknowledgments

* **Advisor:** Prof. Jenn-Jier Lien
* **Development Team:** National Cheng Kung University, Department of CSIE
  * **Speech & Interaction Lead:** YEN-PING LEE (李彥平)
  * **Vision & Motion Planning Collaborators:** NCKU Capstone Team Members
* **Exhibition:** Demonstrated live at **Automation Taipei 2026**
