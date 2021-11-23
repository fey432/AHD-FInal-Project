'''
test_video.py
Author(s): Raymond Fey
This python code is used to update the video feed on the Flask
Web Server without the need or refreshing (use_reloader = True)
'''

from flask import Flask, render_template, Response
import cv2
import netifaces as ni

app = Flask(__name__)

# for local webcam use cv2.VideoCapture(0)
camera = cv2.VideoCapture(1)

def gen_frames():  # generate frame by frame from camera
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result


@app.route('/video_feed')
def video_feed():
    #Video streaming route. Put this in the src attribute of an img tag
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index_2():
    """Video streaming home page."""
    return render_template('index2.html')


if __name__ == '__main__':
    ni.ifaddresses('wlan0')
    ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    #Create Web Server
    app.run(debug = False, port = 8081, host = ip, use_reloader = True )