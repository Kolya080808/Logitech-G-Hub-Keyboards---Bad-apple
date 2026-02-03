import cv2
import time
import ctypes
import numpy as np
from ffpyplayer.player import MediaPlayer


DLL_PATH = r"C:\Program Files\LGHUB\sdks\sdk_legacy_led_x64.dll" #CHANGE THIS
VIDEO_FILE = "bad_apple.mp4"
IS_TKL_KEYBOARD = True

try:
    led_dll = ctypes.cdll.LoadLibrary(DLL_PATH)
    if not led_dll.LogiLedInit():
        print("Error: Failed to initialize SDK. Check G HUB.")
        exit()
    time.sleep(1)
except Exception as e:
    print(f"DLL load error: {e}")
    exit()


def find_keyboard():
    print("\n--- DEVICE CALIBRATION ---")
    print("I will light up devices with red color one by one.")
    print("Press 'y' and Enter if the KEYBOARD lights up.")
    print("Press Enter to try the next one.\n")

    found_device = None

    test_codes = [
        (0x0, "Keyboard (Type 0)"),
        (0x1, "Keyboard (Type 1)"),
        (0x2, "Keyboard (Type 2)"),
        (0x3, "Keyboard (Per Key RGB)"),
        (0x4, "Mouse"),
        (0xFF, "All Devices")
    ]

    for code, name in test_codes:
        print(f"Testing code {code} ({name})...")

        led_dll.LogiLedSetTargetDevice(ctypes.c_int(0xFF))
        led_dll.LogiLedSetLighting(ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(0))
        time.sleep(0.2)

        led_dll.LogiLedSetTargetDevice(ctypes.c_int(code))
        led_dll.LogiLedSetLighting(ctypes.c_int(100), ctypes.c_int(0), ctypes.c_int(0))

        user_input = input(f"Is the keyboard red? (y/Enter): ").strip().lower()

        if user_input == 'y':
            found_device = code
            print(f"Great! Using device code: {found_device}")
            led_dll.LogiLedSetLighting(ctypes.c_int(0), ctypes.c_int(100), ctypes.c_int(0))
            time.sleep(0.5)
            break

    led_dll.LogiLedSetTargetDevice(ctypes.c_int(0xFF))
    led_dll.LogiLedSetLighting(ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(0))

    return found_device


user32 = ctypes.windll.user32
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)


def fit_to_screen(frame):
    h, w = frame.shape[:2]
    scale = min(SCREEN_WIDTH / w, SCREEN_HEIGHT / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
    x_offset = (SCREEN_WIDTH - new_w) // 2
    y_offset = (SCREEN_HEIGHT - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return canvas


def play_bad_apple(video_path, device_code):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Failed to open video file.")
        return

    player = MediaPlayer(video_path)

    window_name = "Bad Logitech G Pro K/DA"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    LOGI_WIDTH = 21 # CHANGE THIS 
    LOGI_HEIGHT = 6 # CHANGE THIS
    EFFECTIVE_WIDTH = 17 if IS_TKL_KEYBOARD else 21

    led_dll.LogiLedSetTargetDevice(ctypes.c_int(device_code))

    try:
        while True:
            audio_frame, val = player.get_frame()
            ret, frame = cap.read()

            if not ret:
                break

            video_t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            audio_t = player.get_pts()

            if val != 'eof' and audio_frame is not None and video_t > audio_t:
                time.sleep(video_t - audio_t)

            if val != 'eof' and audio_frame is not None and (audio_t - video_t) > 0.1:
                continue

            fullscreen_frame = fit_to_screen(frame)
            cv2.imshow(window_name, fullscreen_frame)

            kb_frame_small = cv2.resize(frame, (EFFECTIVE_WIDTH, LOGI_HEIGHT), interpolation=cv2.INTER_AREA)

            if IS_TKL_KEYBOARD:
                black_padding = np.zeros((LOGI_HEIGHT, LOGI_WIDTH - EFFECTIVE_WIDTH, 3), dtype=np.uint8)
                final_kb_frame = np.hstack((kb_frame_small, black_padding))
            else:
                final_kb_frame = kb_frame_small

            kb_frame_bgra = cv2.cvtColor(final_kb_frame, cv2.COLOR_BGR2BGRA)
            bitmap_data = kb_frame_bgra.flatten().astype(np.uint8)

            led_dll.LogiLedSetLightingFromBitmap(bitmap_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)))

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cap.release()
        player.close_player()
        cv2.destroyAllWindows()
        led_dll.LogiLedShutdown()


if __name__ == "__main__":
    target_device = find_keyboard()

    if target_device is not None:
        print(f"Starting Bad Apple on device {target_device}...")
        play_bad_apple(VIDEO_FILE, target_device)
    else:

        print("No keyboard selected. Exiting.")
