import RPi.GPIO as GPIO
import time

#Constants
GPIO_LED_PIN = 26

def __init__():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_LED_PIN, GPIO.OUT)

def __del__():
    GPIO.cleanup()

def get_LED_Status():
    return GPIO.input(GPIO_LED_PIN)

def set_LED():
    GPIO.output(GPIO_LED_PIN, GPIO.HIGH)

def clear_LED():
    GPIO.output(GPIO_LED_PIN, GPIO.LOW)
