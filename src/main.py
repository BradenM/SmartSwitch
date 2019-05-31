from micropython import const
import network
import utime as time
from machine import Pin
from servo import Servo
import blynklib
import ujson

# Load Secrets
with open('secrets.json') as s:
    secrets = ujson.loads(s.read())
    WIFI = secrets['WIFI']
    BLYNK_CFG = secrets['BLYNK']

# Servo Def
servo_pin = Pin(15)
servo = Servo(servo_pin)

# Servo Constants
SWITCH_HIGH = const(130)
SWITCH_LOW = const(50)
SWITCH_HOME = const(90)
SWITCH_STATE = True
servo.write_angle(SWITCH_HOME)

CONNECT_PRINT_MSG = '[Blynk] Connected!'
DISCONNECT_PRINT_MSG = '[Blynk] Disconnected!'


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
def handle_toggle(pin, value):
    global SWITCH_HIGH, SWITCH_LOW, SWITCH_HOME
    val = int(value[0])
    switch_to = SWITCH_HIGH
    if not val:
        switch_to = SWITCH_LOW
        print("Turning off")
    else:
        print("Turning On")
    servo.write_angle(switch_to)
    time.sleep_ms(250)
    servo.write_angle(SWITCH_HOME)
    time.sleep_ms(250)
    servo.write_us(0)


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


while True:
    blynk.run()
