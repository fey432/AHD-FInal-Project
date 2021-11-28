'''
GPIO_test.py
Author(s): Raymond Fey
This python code is to interact with the GPIO and I2C
devices connected to the Raspberry Pi
'''
import RPi.GPIO as GPIO
import board, busio
from adafruit_bme280 import basic as adafruit_bme280


def __del__():
    GPIO.cleanup()

def get_LED_Status(pin):
    return GPIO.input(pin)

def get_LED_Status_text(pin):
    if(get_LED_Status(pin)):
        return "On"
    else:
        return "Off"

def set_LED(pin):
    GPIO.output(pin, GPIO.HIGH)

def clear_LED(pin):
    GPIO.output(pin, GPIO.LOW)

def toggle_LED(pin):
    if(get_LED_Status(pin)):
        clear_LED(pin)
    else:
        set_LED(pin)

def get_Temperature_text(F_C):
    print(sensor.temperature)
    if F_C:
        return str("{:.1f}".format(sensor.temperature * 1.8 + 32)) + "°F"
    else:
        return str(sensor.temperature) + "°C"

def get_humidity_text():
    return str("{:.1f}".format(sensor.humidity))

def get_pressure_text():
    return str(int(sensor.pressure))

def set_Temperature(temp):
    global curr_set_temp
    curr_set_temp = temp

def get_Temperature():
    global curr_set_temp
    print(curr_set_temp)
    return curr_set_temp

#Main
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(19,GPIO.OUT)
GPIO.setup(13,GPIO.OUT)
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)
print(sensor.temperature)
curr_set_temp = 78