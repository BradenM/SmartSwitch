import utime as time
import network
from micropython import const
from machine import Pin
from servo import Servo
import gc
from hcsr04 import HCSR04
import ujson
import blynklib
gc.collect()

# Load Secrets
with open('secrets.json') as s:
    secrets = ujson.loads(s.read())
    WIFI = secrets['WIFI']
    BLYNK_CFG = secrets['BLYNK']

# Servo Def
light_servo_pin = Pin(14)
fan_servo_pin = Pin(15)
light_servo = Servo(light_servo_pin)
fan_servo = Servo(fan_servo_pin)

# Servo Constants
SWITCH_HIGH = const(130)
SWITCH_LOW = const(50)
SWITCH_HOME = const(90)
light_servo.write_angle(SWITCH_HOME)
fan_servo.write_angle(SWITCH_HOME)

# Blynk Msgs
CONNECT_PRINT_MSG = '[Blynk] Connected!'
DISCONNECT_PRINT_MSG = '[Blynk] Disconnected!'

# Ultrasonic Sensor
usonic = HCSR04(trigger_pin=5, echo_pin=4)
SONIC_READ = []
SONIC_TIMEOUT = 0


def connect_wifi():
    '''Connect to Wifi'''
    ssid = WIFI['ssid']
    passwd = WIFI['passwd']
    wifi = network.WLAN(network.STA_IF)
    if wifi.isconnected():
        print("Connected to %s" % ssid)
        get_wifi()
        return wifi
    print("Connecting to %s..." % ssid)
    wifi.active(True)
    wifi.connect(ssid, passwd)
    while not wifi.isconnected():
        pass
    print("Wifi Connected Successfully")
    return get_wifi()


def get_wifi():
    '''Returns Wifi Config Info'''
    wifi = network.WLAN(network.STA_IF)
    if not wifi.isconnected():
        return connect_wifi()
    print("IP: %s" % wifi.ifconfig()[0])
    return wifi


# Setup
connect_wifi()
print("Connecting to Blynk @ %s:%s" % (BLYNK_CFG['server'], BLYNK_CFG['port']))
blynk = blynklib.Blynk(
    BLYNK_CFG['token'], server=BLYNK_CFG['server'], port=8443)


@blynk.handle_event("connect")
def connect_handler():
    print(CONNECT_PRINT_MSG)


@blynk.handle_event("disconnect")
def disconnect_handler():
    print(DISCONNECT_PRINT_MSG)


@blynk.handle_event('write V0')
def handle_toggle_light(pin, value):
    val = int(value[0])
    return toggle(light_servo, val)


@blynk.handle_event('write V1')
def handle_toggle_fan(pin, value):
    val = int(value[0])
    return toggle(fan_servo, val)


@blynk.handle_event('read V2')
def handle_read_sig_strength(pin):
    wifi = get_wifi()
    strength = abs(wifi.status('rssi'))
    blynk.virtual_write(pin, strength)


@blynk.handle_event('read V3')
def handle_read_ip_addr(pin):
    wifi = get_wifi()
    ip_addr = wifi.ifconfig()[0]
    blynk.virtual_write(pin, ip_addr)


def get_servo_states(servo):
    global SWITCH_HIGH, SWITCH_LOW
    if servo is light_servo:
        return (SWITCH_LOW, SWITCH_HIGH)
    return (SWITCH_HIGH, SWITCH_LOW)


def toggle(servo, val):
    global SWITCH_HOME
    HIGH, LOW = get_servo_states(servo)
    switch_to = HIGH
    if not val:
        switch_to = LOW
        servo.state = 0
        print("Turning off")
    else:
        servo.state = 1
        print("Turning On")
    servo.write_angle(switch_to)
    time.sleep_ms(250)
    servo.write_angle(SWITCH_HOME)
    time.sleep_ms(250)
    servo.write_us(0)


def get_sonic():
    global SONIC_READ, usonic
    dist = usonic.distance_mm()
    if(dist >= 400):
        return None
    if len(SONIC_READ) >= 15:
        SONIC_READ.pop(0)
    SONIC_READ.append(dist)


def eval_sonic():
    global SONIC_READ, SONIC_TIMEOUT
    gc.collect()
    if SONIC_TIMEOUT > 0:
        SONIC_TIMEOUT -= 1
        print("Sonic Timed Out @", SONIC_TIMEOUT)
        return None
    if len(SONIC_READ) < 15:
        return None
    sonic_avg = int(sum(SONIC_READ) / len(SONIC_READ))
    if sonic_avg <= 300 and sonic_avg >= 150:
        if blynk.connected():
            blynk.virtual_write(0, int(not light_servo.state))
        SONIC_TIMEOUT = 20
        SONIC_READ = []
        return toggle(light_servo, not light_servo.state)
    if sonic_avg <= 100 and sonic_avg >= 0:
        if blynk.connected():
            blynk.virtual_write(1, int(not fan_servo.state))
        SONIC_TIMEOUT = 20
        SONIC_READ = []
        return toggle(fan_servo, not fan_servo.state)


while True:
    blynk.run()
    get_sonic()
    eval_sonic()
