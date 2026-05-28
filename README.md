# Gesture Vision 🖐️📸

Gesture Vision is an interactive, real-time webcam filter and media capture system powered by **OpenCV** and **MediaPipe Hand Tracking**. By using natural hand gestures, users can switch between a suite of premium visual filters, draw dynamic bounding boxes, and capture beautifully-filtered photos and videos without touching their keyboard or mouse.

---

## ✨ Features

### 🎨 12 Premium Real-Time Filters
Cycle through a broad array of custom visual styles:
- **GRAY** (Grayscale) & **THERMAL** (Jet color map)
- **INVERT** (Color negation) & **SKETCH** (Pencil drawing effect)
- **VINTAGE** (Sepia color transform) & **NEON** (High-intensity glow)
- **CARTOON** (Bilateral edge mask) & **MATRIX** (Laplacian digital edges)
- **GLITCH** (Chromatic aberration) & **MIRROR** (Horizontal symmetry)
- **POP_ART** (Quantized color palette)

### 📐 Dynamic Box Compositing
When **both hands** are detected in the webcam view, they form an interactive quadrilateral box. The active filter is seamlessly composited **only inside this box**, keeping the rest of the frame untouched.

### ✊ Gesture-Driven Capture Control
- **Filter Navigation**:
  - **Right Hand Pinch**: Cycle to the **next** filter.
  - **Left Hand Pinch**: Cycle to the **previous** filter.
- **Media Capturing** (using both hands simultaneously):
  - **Single Pinch (Both Hands)**: Starts a yellow 3-second countdown to save a **Photo** (`.png`).
  - **Double Pinch (Both Hands)**: Immediately upgrades the active countdown to record a **Video** (`.mp4`) for 5 seconds.
  - **Pinch During Recording**: Instantly stops the active recording and saves it early.

### 🎬 Pristine Capture Guarantee
All captured photos and videos are saved with the selected filter applied to the **entire frame**, and are completely free from hands, yellow box boundaries, countdown indicators, progress bars, or HUD overlays.

### 💎 Premium HUD Overlays
- **Color-Coded Circular Countdowns**: Yellow rings for photos, red rings for videos.
- **Pulsing Recording HUD**: Features a blinking red `REC` dot and remaining seconds indicator.
- **Dynamic Progress Bar**: A sleek progress bar rendered at the top of the screen showing recording progress.
- **Green Success Banner**: Confirms successful save and displays the exact filename on-screen.

---

## 🎮 Quick Reference Controls

| Gesture / Input | Action | Feedback |
| :--- | :--- | :--- |
| **Right Hand Pinch** | Switches to next filter | Green `"NEXT FILTER"` text |
| **Left Hand Pinch** | Switches to previous filter | Orange `"PREV FILTER"` text |
| **Pinch Both Hands Once** | Starts 3s Photo Countdown | Yellow countdown circle |
| **Pinch Both Hands Twice** | Upgrades to 3s Video Countdown | Red countdown circle |
| **Pinch Both Hands During Rec** | Stops and saves video early | Green `"SAVED: capture_...mp4"` banner |
| **Press Keyboard 'Q'** | Safely exits the application | Cleans up resources & closes windows |

---

## 🚀 Setup & Installation

### Prerequisites
Make sure you have Python 3.8+ installed on your system.

### 1. Clone & Navigate
```bash
git clone <repository-url>
cd Gesture-Vision-main
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python hand-ditaction.py
```

### 5. Spatial Media Editing Mode 🎞️
You can use hand gestures and real-time bounding boxes to dynamically filter and edit your pre-recorded photos and videos! Just pass the file path as an argument:
```bash
# Edit a pre-recorded video (loops automatically on screen):
python hand-ditaction.py path/to/my_video.mp4

# Edit a saved photo:
python hand-ditaction.py path/to/my_photo.jpg
```
A Picture-in-Picture (PiP) guide of your webcam will automatically render in the corner so you can easily position your hand gestures relative to the asset. Exported photos/videos will be clean, high-resolution, and perfectly filtered.

---

## 🛠️ Tech Stack
- **OpenCV**: Handles webcam input, real-time image transformations, video encoding, and window rendering.
- **MediaPipe Hands**: Real-time hand landmark tracking and gesture state analysis.
- **NumPy**: Throttles pixel-level array math for high-performance filter composition.
