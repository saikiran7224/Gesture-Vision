import math
import time
import sys
import os
import numpy as np
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

# Check if an input file is passed as a command-line argument for Spatial Editing mode
edit_mode = False
edit_type = None  # "image", "video", or None
edit_path = None
edit_img = None
edit_cap = None

if len(sys.argv) > 1:
    edit_path = sys.argv[1]
    if os.path.exists(edit_path):
        ext = os.path.splitext(edit_path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
            edit_img = cv2.imread(edit_path)
            if edit_img is not None:
                edit_mode = True
                edit_type = "image"
                print(f"Loaded image for Spatial Editing: {edit_path}")
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            edit_cap = cv2.VideoCapture(edit_path)
            if edit_cap.isOpened():
                edit_mode = True
                edit_type = "video"
                print(f"Loaded video for Spatial Editing: {edit_path}")
    if not edit_mode:
        print(f"Asset file invalid or not found: {edit_path}. Launching in standard Webcam mode.")

# Webcam is always initialized for hand tracking
cap = cv2.VideoCapture(0)
cv2.namedWindow("Hand Filter", cv2.WINDOW_NORMAL)

hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

filters          = ["None", "GRAY", "THERMAL", "INVERT", "SKETCH", "VINTAGE", "NEON", "CARTOON", "MATRIX", "GLITCH", "MIRROR", "POP_ART"]
current_filter   = 0
last_switch_time = 0
cooldown         = 1.0


# Image capture configuration
last_capture_time         = 0.0
capture_cooldown          = 2.0
feedback_start_time       = 0.0
capture_feedback_duration = 1.5
last_captured_filename    = ""

# Countdown capture settings
countdown_active          = False
countdown_start_time      = 0.0
countdown_duration        = 3.0
capture_mode              = "photo"  # "photo" or "video"

# Video recording configuration
recording_active          = False
recording_start_time      = 0.0
recording_duration        = 10.0     # Record for 10 seconds
video_writer              = None
video_filename            = ""

# Filter switch feedback overlay configuration
filter_switch_text        = ""
filter_switch_time        = 0.0
filter_switch_duration    = 1.2      # Show feedback for 1.2 seconds
filter_switch_color       = (0, 255, 0)

# Pinch detection helper
prev_both_pinching        = False




def get_px(landmark, w, h):
    return int(landmark.x * w), int(landmark.y * h)


def apply_filter(frame, name):
    """Return a fully-filtered copy of frame."""
    if name == "GRAY":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    elif name == "THERMAL":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    elif name == "INVERT":
        return cv2.bitwise_not(frame)

    elif name == "SKETCH":
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        inv     = 255 - gray
        blur    = cv2.GaussianBlur(inv, (21, 21), 0)
        invblur = 255 - blur
        sketch  = cv2.divide(gray, invblur, scale=256.0)
        return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    elif name == "VINTAGE":
        kernel = np.array([[0.272, 0.534, 0.131],
                           [0.349, 0.686, 0.168],
                           [0.393, 0.769, 0.189]])
        return np.clip(cv2.transform(frame, kernel), 0, 255).astype(np.uint8)

    elif name == "NEON":
        b, g, r = cv2.split(frame)
        r = cv2.addWeighted(r, 1.5, g, -0.5, 0)
        b = cv2.addWeighted(b, 1.5, g, -0.5, 0)
        g = cv2.multiply(g, 0.3)
        return cv2.merge([b, g, r])

    elif name == "CARTOON":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                      cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(frame, 9, 300, 300)
        return cv2.bitwise_and(color, color, mask=edges)

    elif name == "MATRIX":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Laplacian(gray, cv2.CV_8U, ksize=5)
        matrix_frame = np.zeros_like(frame)
        matrix_frame[:, :, 1] = edges 
        return matrix_frame

    elif name == "GLITCH":
        glitch = frame.copy()
        glitch[:, 12:, 2] = frame[:, :-12, 2]
        glitch[:, :-12, 0] = frame[:, 12:, 0]
        return glitch

    elif name == "MIRROR":
        h, w, _ = frame.shape
        half_w = w // 2
        left_half = frame[:, :half_w]
        right_half = cv2.flip(left_half, 1)
        return np.hstack((left_half, right_half))

    elif name == "POP_ART":
        n_colors = 4
        div = 256 // n_colors
        return (frame // div) * div

    return frame.copy()   # "None" -> identical copy


# apply_filter_in_box was removed as per the requirement to apply filters to the whole frame on pinch.


# Main loop
while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape  # webcam dimensions for tracking

    # Read and setup the target editing canvas
    if edit_mode:
        if edit_type == "image":
            asset_frame = edit_img.copy()
        else:  # edit_type == "video"
            ret_vid, asset_frame = edit_cap.read()
            if not ret_vid or asset_frame is None:
                # Loop the video automatically
                edit_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_vid, asset_frame = edit_cap.read()
            if asset_frame is None:
                asset_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        target_h, target_w, _ = asset_frame.shape
        clean_frame = asset_frame.copy()
        canvas = asset_frame
    else:
        target_h, target_w, _ = frame.shape
        clean_frame = frame.copy()
        canvas = frame

    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    left_hand  = None
    right_hand = None

    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_lm, handedness in zip(results.multi_hand_landmarks,
                                        results.multi_handedness):
            label = handedness.classification[0].label
            # Labels are mirrored because we flipped the frame
            if label == "Left":
                right_hand = hand_lm
            else:
                left_hand  = hand_lm

            # If not in edit mode, main screen landmark drawing is disabled to keep the feed completely clean.

            # Gesture analysis coordinates scaled by webcam space for resolution stability
            thumb_tip = hand_lm.landmark[4]
            index_tip = hand_lm.landmark[8]

            tx_w, ty_w = int(thumb_tip.x * w), int(thumb_tip.y * h)
            ix_w, iy_w = int(index_tip.x * w), int(index_tip.y * h)

            now = time.time()
            dist_index_webcam = math.hypot(ix_w - tx_w, iy_w - ty_w)

            # RIGHT HAND -> NEXT FILTER
            if label == "Left":   # mirrored camera -> actual right hand
                if dist_index_webcam < 50 and (now - last_switch_time) > cooldown:
                    current_filter = (current_filter + 1) % len(filters)
                    last_switch_time = now
                    filter_switch_text = f"NEXT: {filters[current_filter]}"
                    filter_switch_time = now

            # LEFT HAND -> PREVIOUS FILTER
            else:   # mirrored camera -> actual left hand
                if dist_index_webcam < 50 and (now - last_switch_time) > cooldown:
                    current_filter = (current_filter - 1) % len(filters)
                    last_switch_time = now
                    filter_switch_text = f"PREV: {filters[current_filter]}"
                    filter_switch_time = now

    # Track pinch states for filter activation and media capturing
    left_pinching = False
    right_pinching = False

    if left_hand:
        l_thumb = left_hand.landmark[4]
        l_index = left_hand.landmark[8]
        lx_tw, ly_tw = get_px(l_thumb, w, h)
        lx_iw, ly_iw = get_px(l_index, w, h)
        dist_left = math.hypot(lx_iw - lx_tw, ly_iw - ly_tw)
        left_pinching = dist_left < 50

    if right_hand:
        r_thumb = right_hand.landmark[4]
        r_index = right_hand.landmark[8]
        rx_tw, ry_tw = get_px(r_thumb, w, h)
        rx_iw, ry_iw = get_px(r_index, w, h)
        dist_right = math.hypot(rx_iw - rx_tw, ry_iw - ry_tw)
        right_pinching = dist_right < 50

    any_pinching = left_pinching or right_pinching
    both_pinching = left_pinching and right_pinching

    # Apply filter to the whole frame at all times
    selected = filters[current_filter]
    if selected != "None":
        canvas = apply_filter(clean_frame, selected)
    else:
        canvas = clean_frame.copy()

    # Draw hand landmarks only when NOT pinching to keep preview clean during gestures
    if not any_pinching and results.multi_hand_landmarks and not edit_mode:
        for hand_lm in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(canvas, hand_lm, mp_hands.HAND_CONNECTIONS)

    # Render a premium pill feedback overlay at the top for filter switching
    now = time.time()
    if now - filter_switch_time < filter_switch_duration:
        overlay = canvas.copy()
        (t_w, t_h), _ = cv2.getTextSize(filter_switch_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        pad_x, pad_y = 20, 10
        cv2.rectangle(overlay, 
                      (target_w // 2 - t_w // 2 - pad_x, 40 - t_h - pad_y),
                      (target_w // 2 + t_w // 2 + pad_x, 40 + pad_y),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, canvas, 0.5, 0, canvas)
        
        cv2.putText(canvas, filter_switch_text, 
                    (target_w // 2 - t_w // 2, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, lineType=cv2.LINE_AA)

    # Detect edge-triggered pinch event (transition from not-pinching to pinching)
    pinch_event = both_pinching and not prev_both_pinching
    prev_both_pinching = both_pinching

    now = time.time()
    if pinch_event:
        if not countdown_active and not recording_active:
            if (now - last_capture_time) > capture_cooldown:
                countdown_active = True
                countdown_start_time = now
                capture_mode = "photo"
                print("First pinch detected: starting photo countdown...")
        elif countdown_active and capture_mode == "photo":
            # Upgrade photo countdown to video recording!
            capture_mode = "video"
            countdown_start_time = now  # Reset the 3-second countdown for video!
            print("Second pinch detected: upgrading to video countdown!")
        elif recording_active:
            # Pinching during recording stops it early
            recording_active = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None
            last_capture_time = now
            feedback_start_time = now
            last_captured_filename = video_filename
            print("Pinch detected during recording: stopping video early!")

    # Write clean filtered frames to the video file before overlays are drawn
    if recording_active and video_writer is not None:
        if selected != "None":
            video_frame = apply_filter(clean_frame, selected)
        else:
            video_frame = clean_frame.copy()
        video_writer.write(video_frame)

    # Process Countdown Capture
    if countdown_active:
        elapsed = now - countdown_start_time
        if elapsed >= countdown_duration:
            countdown_active = False
            last_capture_time = now
            if capture_mode == "photo":
                # Capture clean photo
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.png"
                if selected != "None":
                    photo_frame = apply_filter(clean_frame, selected)
                else:
                    photo_frame = clean_frame.copy()
                cv2.imwrite(filename, photo_frame)
                feedback_start_time = now
                last_captured_filename = filename
                print(f"Captured and saved image as: {filename}")
            else:
                # Start video recording
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                video_filename = f"capture_{timestamp}.mp4"
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(video_filename, fourcc, 20.0, (target_w, target_h))
                recording_active = True
                recording_start_time = now
                print(f"Started recording video: {video_filename}")
        else:
            # Draw beautiful semi-transparent circular countdown overlay
            remaining = int(math.ceil(countdown_duration - elapsed))
            center = (target_w // 2, target_h // 2)
            radius = 60
            
            overlay_color = (0, 255, 255) if capture_mode == "photo" else (0, 0, 255)
            overlay = canvas.copy()
            cv2.circle(overlay, center, radius, (0, 0, 0), -1)
            cv2.circle(overlay, center, radius, overlay_color, 4)
            cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)
            
            # Center the countdown digit
            txt = str(remaining)
            (t_w, t_h), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 2.5, 7)
            text_x = center[0] - t_w // 2
            text_y = center[1] + t_h // 2
            cv2.putText(canvas, txt, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 2.5, overlay_color, 7)

            # Draw a banner indicating what we are capturing
            label_text = "PHOTO COUNTDOWN" if capture_mode == "photo" else "VIDEO COUNTDOWN"
            (l_w, l_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.putText(canvas, label_text, (center[0] - l_w // 2, center[1] - radius - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, overlay_color, 2)

    # Process Active Video Recording
    if recording_active:
        elapsed_rec = now - recording_start_time
        if elapsed_rec >= recording_duration:
            # Stop recording automatically when duration is reached
            recording_active = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None
            last_capture_time = now
            feedback_start_time = now
            last_captured_filename = video_filename
            print(f"Recorded and saved video as: {video_filename}")
        else:
            # Draw a pulsing red REC indicator and seconds remaining
            blink = int(now * 2) % 2 == 0
            dot_color = (0, 0, 255) if blink else (50, 50, 50)
            cv2.circle(canvas, (30, 40), 10, dot_color, -1)
            
            remaining_rec = max(0.0, recording_duration - elapsed_rec)
            cv2.putText(canvas, f"REC {remaining_rec:.1f}s", (50, 47),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Premium progress bar at the top
            bar_width = int((remaining_rec / recording_duration) * (target_w - 200))
            cv2.rectangle(canvas, (180, 32), (target_w - 20, 42), (50, 50, 50), cv2.FILLED)
            cv2.rectangle(canvas, (180, 32), (180 + bar_width, 42), (0, 0, 255), cv2.FILLED)

    # HUD
    cv2.putText(canvas, "Right Pinch=Next  Left Pinch=Prev  2xPinch=Video  Q=Quit",
                (10, target_h - 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.45, (150, 150, 150), 1)

    # Show capture feedback overlay if within feedback duration
    if now - feedback_start_time < capture_feedback_duration:
        cv2.rectangle(canvas, (10, 10), (target_w - 10, 50), (0, 255, 0), cv2.FILLED)
        cv2.putText(canvas, f"SAVED: {last_captured_filename}", (20, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Render Picture-in-Picture (PiP) Guide Overlay for webcam hand tracking in Edit Mode
    if edit_mode:
        pip_h = 120
        pip_w = 160
        pip_frame = frame.copy()
        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(pip_frame, hand_lm, mp_hands.HAND_CONNECTIONS)
        pip_resized = cv2.resize(pip_frame, (pip_w, pip_h))
        # Embed in the top-right corner of the canvas
        canvas[10:10+pip_h, target_w-pip_w-10:target_w-10] = pip_resized
        # Draw a beautiful neon border around the PiP preview
        cv2.rectangle(canvas, (target_w-pip_w-11, 9), (target_w-9, 10+pip_h+1), (255, 255, 0), 1, lineType=cv2.LINE_AA)
        cv2.putText(canvas, "LIVE GUIDE", (target_w-pip_w-10, 10+pip_h+18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, lineType=cv2.LINE_AA)

    cv2.imshow("Hand Filter", canvas)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


if video_writer is not None:
    video_writer.release()

if edit_cap is not None:
    edit_cap.release()

cap.release()
cv2.destroyAllWindows()