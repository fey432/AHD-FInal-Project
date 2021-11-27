'''
test.py
Author(s): Raymond Fey
This python code is to create the Flask Web Server and
control the web page interactions
'''

from flask import Flask, render_template, request, Response, redirect
import socket
from threading import Thread
import netifaces as ni
import cv2
import numpy as np
import GPIO_Test, mailbox
from datetime import datetime

#Global Variables
frame = None

def updateFrame(feed):
    global frame
    frame = feed

    
def func1(i):
    print("func1: " + str(i))

app = Flask(__name__, static_folder = 'static')
app.secret_key = b'notSoSecret'
@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get('action1') == 'VALUE1':
            func1(1)
            pass
        elif request.form.get('action2') == 'VALUE2':
            func1(2)
            pass
        elif request.form.get('send') == "send":
            text = request.form.get('message_area')
            mailbox.put_message_remote(text)
            print(text)
        else:
            pass
    elif request.method == 'GET':
        return render_template('index.html', comment_temp = GPIO_Test.get_Temperature_text(1), comment_time = datetime.now().strftime("%H:%M"), comment_humidity = GPIO_Test.get_humidity_text(), comment_pressure = GPIO_Test.get_pressure_text())

    return render_template("index.html", comment_temp = GPIO_Test.get_Temperature_text(1), comment_time = datetime.now().strftime("%H:%M"), comment_humidity = GPIO_Test.get_humidity_text(), comment_pressure = GPIO_Test.get_pressure_text())



@app.route('/iot' ,methods =['GET','POST'])
def iot():
    if request.method == "POST":
        if request.form.get('LED') == 'LED':
            GPIO_Test.toggle_LED(26)
            pass
        elif request.form.get('LED_2') == 'LED_2':
            GPIO_Test.toggle_LED(19)
            pass
        elif request.form.get('LED_3') == 'LED_3':
            GPIO_Test.toggle_LED(13)
        elif request.form.get('TEMP') == "TEMP":
            temp = request.form.get('temp_slider')
            GPIO_Test.set_Temperature(temp)
    else:
        return render_template('iot.html', comment_1 = GPIO_Test.get_LED_Status_text(26), comment_2 = GPIO_Test.get_LED_Status_text(19), comment_3 = GPIO_Test.get_LED_Status_text(13), comment_curr_temp = GPIO_Test.get_Temperature())

    return render_template('iot.html', comment_1 = GPIO_Test.get_LED_Status_text(26), comment_2 = GPIO_Test.get_LED_Status_text(19), comment_3 = GPIO_Test.get_LED_Status_text(13), comment_curr_temp = GPIO_Test.get_Temperature())


@app.route('/about' ,methods =['GET','POST'])
def about():
    return render_template("about.html")

def gen_frames(frames):
    while True:
        frames = frames.copy()
        ret, buffer = cv2.imencode('.jpg',frames)
        frames_2 = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frames_2 + b'\r\n\r\n')  # concat frame one by one and show result

#FIXME: update frames for the webpage
@app.route('/video_feed')
def video_feed():
    global frame
    return Response(gen_frames(frame), mimetype = 'multipart/x-mixed-replace; boundary=frame')

def startWebServer():
    #Grab local IP from Wireless Network
    ni.ifaddresses('wlan0')
    ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    #Create Web Server
    kwargs = {'host':ip, 'port': 8080, 'threaded': True, 'use_reloader': False, 'debug': False}
    flaskThread = Thread(target=app.run, daemon =True, kwargs = kwargs).start()
