from machine import Pin, ADC
import neopixel
import time

# ПИНЫ (СТРОГО СОХРАНЕНЫ)
PHOTO_PIN = 34      # фоторезистор
MIC_PIN = 35        # микрофон
PIR_PIN = 17        # PIR
BUTTON_PIN = 15     # кнопка на 14 (сигнал)
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
    fill((level, level // 2, level // 2))

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

# НАСТРОЙКИ ПОРОГОВ
LIGHT_THRESHOLD = 2500
MIC_THRESHOLD = 0	
NO_MOTION_TIMEOUT = 15

# Хранилище для сглаженной амплитуды
global_smooth_amplitude = 0
# Скорость затухания (чем ближе к 1.0, тем медленнее гаснет. Например: 0.85 - плавно, 0.5 - быстро)
FADE_COEFFICIENT = 0.88 

last_motion_time = time.time()

def read_light():
    return light_sensor.read()

def read_mic_level(samples=150):
    global global_smooth_amplitude
    
    min_val = 4095
    max_val = 0
    avg_sum = 0
    
    # Читаем физические данные с датчика
    for _ in range(samples):
        val = mic_sensor.read()
        avg_sum += val
        if val < min_val: min_val = val
        if val > max_val: max_val = val
        
    raw_amplitude = max_val - min_val
    avg = avg_sum // samples
    
    # ЛОГИКА ФИЛЬТРАЦИИ ПРОСАДОК:
    # Если датчик поймал звук громче, чем наше текущее сглаженное значение — мгновенно прыгаем вверх
    if raw_amplitude > global_smooth_amplitude:
        global_smooth_amplitude = raw_amplitude
    else:
        # Если датчик просел (выдал 0 или просто резко упал) — плавно уменьшаем старое значение
        global_smooth_amplitude = int(global_smooth_amplitude * FADE_COEFFICIENT)
        
    # Защита: если амплитуда упала совсем низко, принудительно обнуляем
    if global_smooth_amplitude < 10:
        global_smooth_amplitude = 0

    # Возвращаем вместо сырой амплитуды (raw_amplitude) нашу сглаженную (smooth_amplitude)
    return avg, global_smooth_amplitude


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

    # 1. Жесткие режимы (игнорируют датчики)
    if mode == MODE_OFF:
        return STATE_IDLE
    if mode == MODE_FOCUS:
        return STATE_FOCUS

    # Обновление таймера движения
    now = time.time()
    if motion_detected:
        last_motion_time = now

    # 2. Проверка движения (нет движения = IDLE)
    recently_seen_motion = (now - last_motion_time) < NO_MOTION_TIMEOUT
    if not recently_seen_motion:
        return STATE_IDLE

    # 3. Есть движение -> Проверка звука (MUSIC приоритетнее)
    sound_is_active = mic_amplitude > MIC_THRESHOLD
    if sound_is_active:
        return STATE_MUSIC

    # 4. Есть движение + тишина -> Проверка освещенности
    room_is_dark = light_value < LIGHT_THRESHOLD
    if room_is_dark:
        return STATE_AMBIENT

    # Есть движение, но светло и тихо
    return STATE_IDLE

def apply_state(state, mic_amplitude):
    def map_value(x, in_min, in_max, out_min, out_max):
        # Предотвращает выход за границы входного диапазона
        if x < in_min: x = in_min
        if x > in_max: x = in_max
        return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)
        
    if state == STATE_IDLE:
        led_off()
    elif state == STATE_AMBIENT:
        fill((255, 140, 40))   # теплый свет
    elif state == STATE_FOCUS:
        fill((120, 180, 255))  # холодный рабочий свет
    elif state == STATE_MUSIC:
        brightness = map_value(mic_amplitude, 50, 400, 10, 255)
        set_music_level(brightness)

print("Система запущена")

while True:
    handle_button()

    light_value = read_light()
    mic_avg, mic_amplitude = read_mic_level()
    motion_detected = pir.value() == 1

    state = choose_state(light_value, mic_amplitude, motion_detected)
    apply_state(state, mic_amplitude)
    
    print(
        "mode =", mode_names[mode],
        "| state =", state,
        "| light =", light_value,
        "| mic_amp =", mic_amplitude,
        "| pir =", int(motion_detected)
    )
    
    time.sleep_ms(50)  # Небольшая задержка для стабильности цикла

