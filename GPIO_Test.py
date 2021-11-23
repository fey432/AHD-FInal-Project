import RPi.GPIO as GPIO
import board, busio, adafruit_bno055


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

#Main
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(19,GPIO.OUT)
GPIO.setup(13,GPIO.OUT)
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bno055.BNO055_I2C(i2c)
print(sensor.temperature)