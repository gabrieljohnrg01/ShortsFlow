# 🎬 ShortsFlow

An AI-powered system designed to automate the entire lifecycle of YouTube Shorts creation—from script writing and voiceover generation to asset fetching, video editing, and final uploading.

## 🚀 Features

- **Brainstorming & Scripting**: Generates engaging, viral scripts using **Google Gemini**.
- **Natural Voiceovers**: Converts scripts into high-quality narration using **Edge-TTS**.
- **Smart Asset Fetching**: Automatically downloads relevant vertical videos from **Pexels**.
- **Automated Editing**: Compiles script, voice, and visuals into a polished 9:16 video using **MoviePy**.
- **YouTube Integration**: Uploads the finished video directly to your channel via the **YouTube Data API**.
- **Fully Autonomous Scheduling**: Built-in 24/7 background scheduler (`scheduler.py`) to post weekly content on autopilot.
- **Space Management**: Built-in cleanup system that keeps your storage lean by retaining only the last 5 projects.

## 🛠️ Prerequisites

- Python 3.8+
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)
- **YouTube Data API Credentials**: Follow the [YouTube Setup Guide](youtube_setup.md) to generate your `client_secrets.json` file.

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd "Default Template"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Configuration (`config.py`)

Open `config.py` and set your preferences:

```python
GEMINI_KEY = "your-google-gemini-api-key"
VOICE = "en-US-ChristopherNeural" # Choose an Edge-TTS voice
TOPIC = "your-topic-here" # The subject for your next video
```

## 🏃 Usage

You can run the system in two ways:

### 1. Autonomous Weekly Scheduler (Recommended)
Run the script continuously in the background to automatically upload specific topics at scheduled times.
```bash
python scheduler.py
```

### 2. Manual One-Off Generation
Generate a single video immediately using the default `TOPIC` defined in `config.py`.
```bash
# Using the batch file
start.bat

# Or using Python directly
python main.py
```

The system will create a timestamped folder in `assets/` for each new project.

## 📂 Project Structure

- `main.py`: The central orchestrator of the automation workflow.
- `scheduler.py`: 24/7 daemon that manages the weekly posting schedule.
- `config.py`: Configuration file for API keys, voices, and default fallback topics.
- `script_gen.py`: Handles AI script generation and visual planning.
- `voice_gen.py`: Manages text-to-speech generation and whisper alignment.
- `video_fetch.py`: Searches and downloads relevant vertical video assets.
- `editor.py`: The video editing engine that renders the final MP4.
- `uploader.py`: Handles the YouTube upload process.
- `assets/`: Directory where project-specific files and rendered videos are stored.

## 🧹 Cleanup System

To prevent disk space issues, the system automatically monitors the `assets/` folder. When the number of projects exceeds 10, it triggers a cleanup, keeping only the 5 most recent project folders.
