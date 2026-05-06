from machine import Pin, ADC
import neopixel
import time

# ПИНЫ
PHOTO_PIN = 34      # фоторезистор
MIC_PIN = 35        # микрофон
PIR_PIN = 17        # PIR
BUTTON_PIN = 15     # кнопка
LED_PIN = 25        # 6812 RGB

NUM_LEDS = 4

# ДАТЧИКИ
light_sensor = ADC(Pin(PHOTO_PIN))
light_sensor.atten(ADC.ATTN_11DB)
light_sensor.width(ADC.WIDTH_12BIT)

mic_sensor = ADC(Pin(MIC_PIN))
mic_sensor.atten(ADC.ATTN_11DB)
mic_sensor.width(ADC.WIDTH_12BIT)

pir = Pin(PIR_PIN, Pin.IN)
button = Pin(BUTTON_PIN, Pin.IN)

# LED
np = neopixel.NeoPixel(Pin(LED_PIN), NUM_LEDS)

def fill(color):
    for i in range(NUM_LEDS):
        np[i] = color
    np.write()

def led_off():
    fill((0, 0, 0))

def set_music_level(level):
    level = max(0, min(255, level))
    fill((level, 40, level // 2))

# РЕЖИМЫ
MODE_AUTO = 0
MODE_FOCUS = 1
MODE_OFF = 2

mode_names = {
    MODE_AUTO: "AUTO",
    MODE_FOCUS: "FOCUS",
    MODE_OFF: "OFF"
}

STATE_IDLE = "IDLE"
STATE_AMBIENT = "AMBIENT"
STATE_MUSIC = "MUSIC"
STATE_FOCUS = "FOCUS"

mode = MODE_AUTO
last_button_time = 0
button_was_pressed = False

# порог темноты надо будет подстроить по реальным значениям
LIGHT_THRESHOLD = 2500
MIC_THRESHOLD = 150
NO_MOTION_TIMEOUT = 15

last_motion_time = time.time()

def read_light():
    return light_sensor.read()

def read_mic_level(samples=40):
    values = []
    for _ in range(samples):
        values.append(mic_sensor.read())
        time.sleep_ms(2)

    avg = sum(values) / len(values)
    amplitude = max(values) - min(values)
    return int(avg), int(amplitude)

def handle_button():
    global mode, last_button_time, button_was_pressed

    now = time.ticks_ms()
    pressed = (button.value() == 1)
    if pressed and not button_was_pressed:
        if time.ticks_diff(now, last_button_time) > 250:
            mode = (mode + 1) % 3
            last_button_time = now
            print("Режим ->", mode_names[mode])

    button_was_pressed = pressed

def choose_state(light_value, mic_amplitude, motion_detected):
    global last_motion_time

    now = time.time()

    if motion_detected:
        last_motion_time = now

    if mode == MODE_OFF:
        return STATE_IDLE

    if mode == MODE_FOCUS:
        return STATE_FOCUS

    room_is_dark = light_value < LIGHT_THRESHOLD
    sound_is_active = mic_amplitude > MIC_THRESHOLD
    recently_seen_motion = (now - last_motion_time) < NO_MOTION_TIMEOUT

    if not recently_seen_motion:
        return STATE_IDLE

    if sound_is_active:
        return STATE_MUSIC

    if room_is_dark:
        return STATE_AMBIENT

    return STATE_IDLE

def apply_state(state, mic_amplitude):
    if state == STATE_IDLE:
        led_off()

    elif state == STATE_AMBIENT:
        fill((255, 140, 40))   # теплый свет

    elif state == STATE_FOCUS:
        fill((120, 180, 255))  # холодный рабочий свет

    elif state == STATE_MUSIC:
        level = min(255, 40 + mic_amplitude // 4)
        set_music_level(level)

print("Система запущена")

while True:
    handle_button()

    light_value = read_light()
    mic_avg, mic_amplitude = read_mic_level()
    motion_detected = pir.value() == 1

    ## state = choose_state(light_value, mic_amplitude, motion_detected)
    state = STATE_FOCUS
    apply_state(state, mic_amplitude)
    
    print(
        "mode =", mode_names[mode],
        "| state =", state,
        "| light =", light_value,
        "| mic_avg =", mic_avg,
        "| mic_amp =", mic_amplitude,
        "| pir =", int(motion_detected)
    )
    
    ## time.sleep(0.2)
    
    print(button.value())
    ## time.sleep(0.1)
