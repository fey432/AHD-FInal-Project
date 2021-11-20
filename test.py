from flask import Flask, render_template, request, Response
import socket
from threading import Thread
import netifaces as ni
import cv2
import numpy

frame = None

def updateFrame(feed):
    global frame
    frame = feed

    
def func1(i):
    print("func1: " + str(i))

app = Flask(__name__)
app.secret_key = b'notSoSecret'
@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get('action1') == 'VALUE1':
            text = request.form.get('textbox')
            func1(1)
            print(text)
            pass
        elif request.form.get('action2') == 'VALUE2':
            func1(2)
            pass
        else:
            pass
    elif request.method == 'GET':
        return render_template('index.html')

    return render_template("index.html")

def gen_frames(frames):
    ret, buffer = cv2.imencode('.jpg',frames)
    frames = buffer.tobytes()
    yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frames + b'\r\n')  # concat frame one by one and show result

#FIXME: update frames for the webpage
@app.route('/video_feed')
def video_feed():
    while True:
        global frame
        return Response(gen_frames(frame), mimetype = 'multipart/x-mixed-replace; boundary=frame')

def startWebServer():
    #Grab local IP from Wireless Network
    ni.ifaddresses('wlan0')
    ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    #Create Web Server
    kwargs = {'host':ip, 'port': 8080, 'threaded': True, 'use_reloader': False, 'debug': False}
    flaskThread = Thread(target=app.run, daemon = True, kwargs = kwargs).start()
