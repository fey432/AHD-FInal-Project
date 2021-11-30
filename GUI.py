'''
GUI.py
Author(s): Raymond Fey, Javier Garcia, Ifeanyi Anyika

Roles:
    -Front-End Design: Raymond Fey
    -Face & Eye Detection: Javier Garcia and Ifeanyi Anyika
    
This python code is to core script to run the GUI on the Raspberry Pi,
start the Web Server, and capture image frames and detect the face and eyes.
'''
#region imports
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QRect, QSize, QObject, QEvent, QTimer
import sys, cv2, time, threading, schedule
import subprocess as sp
from multiprocessing import Process
import numpy as np
import netifaces as ni
from pynput import keyboard
import GPIO_Test, test, mailbox

blob_threshold = 50
eye_blob = np.zeros((300,200,3), dtype=np.uint8)
msg = "No Updates..."
index = 0
#=====================Scheduler Tools=========================
def run_continuously(interval=1):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run

class WebServer(QThread):
    def __init__(self):
        test.startWebServer()


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.App = App
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.detector_params = cv2.SimpleBlobDetector_Params()
        self.detector_params.filterByArea = False
        self.detector_params.minArea = 50
        self.detector_params.filterByCircularity = False
        self.detector_params.minCircularity = 0.1
        self.detector_params.filterByInertia = False
        self.detector_params.minInertiaRatio = 0.1
        self.detector = cv2.SimpleBlobDetector_create(self.detector_params)
        self.count = 0
        self.fw = [0,0,0,0]
        self.ew = [[0,0,0,0],[0,0,0,0]]
        self.eyenum = 0
        self.ep = [[0,0],[0,0]]
        self.StateList = {"NOT_DETECTED":0,"DETECTED":1,"CENTERED":2,"MOVING":3,"BLINKING":4}
        self.State = "NOT_DETECTED"
        
                
    def detect_faces(self,img, classifier):
        gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face = classifier.detectMultiScale(gray_frame, 1.05, 3)
        if len(face) > 1:
            biggest = (0, 0, 0, 0)
            for i in face:
                if i[3] > biggest[3]:
                    biggest = i
            biggest = np.array([i], np.int32)
        elif len(face) == 1:
            biggest = face
        else:
            return None, [0,0,0,0]
        for (x, y, w, h) in biggest:
            frame = img[y:y + h, x:x + w]
        return frame, [x,y,w,h]

    def detect_eyes(self,img,classifier):
        gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        eyes = classifier.detectMultiScale(gray_frame, 1.2, 3) # detect eyes
        width = np.size(img, 1) # get face frame width
        height = np.size(img, 0) # get face frame height
        left_eye = None
        left_ew = [0,0,0,0]
        right_eye = None
        right_ew = [0,0,0,0]
        for (x, y, w, h) in eyes:
            if ((y<height/4) or (y>height/2)):
                pass
            else:
                eyecenter = x + w / 2  # get the eye center
                if eyecenter < width * 0.5:
                    left_eye = img[y:y + h, x:x + w]
                    left_ew = [x,y,w,h]
                else:
                    right_eye = img[y:y + h, x:x + w]
                    right_ew = [x,y,w,h]
        return [left_eye, right_eye], [left_ew, right_ew]

    def cut_eyebrows(self,img):
        height, width = img.shape[:2]
        eyebrow_h = int(height/4)
        img = img[eyebrow_h:height-eyebrow_h,0:width]
        return img

    def blob_process(self,img,threshold,detector):
        gray_frame = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        _,img = cv2.threshold(gray_frame,threshold,255,cv2.THRESH_BINARY)
        img = cv2.erode(img,None,10)
        img = cv2.dilate(img,None,10)
        img = cv2.medianBlur(img,3)
        keypoints = detector.detect(img)
        return img,keypoints

    def run(self):
        # capture from web cam
        #cap = cv2.VideoCapture(0)        
        cap = cv2.VideoCapture(0)        
        cap.set(3, 1280) # set video width
        cap.set(4, 720) # set video height
        cap.set(15,-3) # set exposure

        while (self._run_flag):
            '''
            Read images from Camera
            '''
            #region
            ret, img = cap.read()
            img = cv2.flip(img,1)
            cv2.rectangle(img,(self.fw[0],self.fw[1]),(self.fw[0]+self.fw[2],self.fw[1]+self.fw[3]),(255,255,0),2) 
            cv2.rectangle(img,(self.ew[0][0]+self.fw[0],self.ew[0][1]+self.fw[1]),(self.ew[0][0]+self.fw[0]+self.ew[0][2],self.ew[0][1]+self.fw[1]+self.ew[0][3]),(255,0,255),2) 
            cv2.rectangle(img,(self.ew[1][0]+self.fw[0],self.ew[1][1]+self.fw[1]),(self.ew[1][0]+self.fw[0]+self.ew[1][2],self.ew[1][1]+self.fw[1]+self.ew[1][3]),(255,0,255),2) 
            cv2.circle(img, (self.ew[0][0]+self.fw[0]+self.ep[0][0],self.ew[0][1]+self.fw[1]+self.ep[0][1]), 10, (0,0,255), 10) 
            cv2.circle(img, (self.ew[1][0]+self.fw[0]+self.ep[1][0],self.ew[1][1]+self.fw[1]+self.ep[1][1]), 10, (0,0,255), 10)
            #endregion

            if ret:
                self.change_pixmap_signal.emit(img)

            #Detect Faces
            if self.count > 9:
                self.ew = [[0,0,0,0],[0,0,0,0]]
                self.eyenum = 0
                self.ep = [[0,0],[0,0]]
                self.eye_flag = [0,0]
                face,self.fw = self.detect_faces(img, self.face_cascade)
                if face is not None:
                    eyes,self.ew = self.detect_eyes(face, self.eye_cascade)
                    for eye in eyes:
                        if eye is not None:
                            self.eye_flag[self.eyenum] = 1
                            eye = self.cut_eyebrows(eye)
                            global eye_blob
                            eye_blob,keypoints = self.blob_process(eye, blob_threshold, self.detector)
                            print(len(keypoints))
                            for keypoint in keypoints:
                                self.ep[self.eyenum] = [int(keypoint.pt[0]),int(keypoint.pt[1])]
                                print(self.ep[self.eyenum])
                        self.eyenum = self.eyenum+1
                
                    #Determine if person blinked (right now only depened on eye detection, eye tracking is not working great)
                    #print(self.eye_flag)
                    if (self.State == "NOT_DETECTED"):
                        if (sum(self.eye_flag)>1):
                            self.State = "DETECTED"
                    elif (self.State == "DETECTED"):
                        if (sum(self.eye_flag)<2):
                            iter = 1
                            prev_eye_flag = self.eye_flag
                            self.State = "BLINKING"
                    elif (self.State == "BLINKING"):
                        if(iter>3):
                            print("lost eye detection")
                            self.State = "NOT_DETECTED"
                        else:
                            if((sum(self.eye_flag)-sum(prev_eye_flag))<1):
                                iter = iter+1
                            else:
                                if(iter<2):
                                    if(prev_eye_flag[0]==0 and prev_eye_flag[1]==0):
                                        print("blink detected")
                                    elif(prev_eye_flag[0]==0):
                                        print("left wink detected")
                                    else:
                                        print("right wink detected")
                                else: 
                                    if(prev_eye_flag[0]==0 and prev_eye_flag[1]==0):
                                        print("long blink detected")
                                    elif(prev_eye_flag[0]==0):
                                        print("long left wink detected")
                                    else:
                                        print("long right wink detected")
                                self.State = "DETECTED"
                    else:
                        self.State = "DETECTED"
                else:
                    self.State = "NOT_DETECTED"
                            
                self.count = 0 
            self.count = self.count+1
            test.updateFrame(img)
 
        cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        #self.wait() 
        #.wait may cause a hang up from the OS
        

class App(QWidget):

    @pyqtSlot(np.ndarray)
    def update_image(self,cv_img):
        """Updates the image_label with a new opencv image"""
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label1.setPixmap(qt_img)
        qt_eye = self.convert_cv_qt(eye_blob)
        self.image_label2.setPixmap(qt_eye)
    
    def convert_cv_qt(self,cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 360, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
    
    def changeThreshold(self,value):
        global blob_threshold
        blob_threshold = value

    def get_Temp_Slider(self):
        self.temp_value.setText(str(self.temp_slider.value()))

    def get_Threshold_Slider(self):
        self.threshold_label.setText(str(self.slider.value()))

    def updateMsg(self):
        global msg
        self.msg_text.setPlainText(mailbox.get_message_client())

    def updateTemp(self):
        self.temp_slider.setValue(int(GPIO_Test.get_Temperature()))

    def move_up(self):
        global index

        set_widget = self.nav_v_content.itemAt(index).widget()
        set_widget.setStyleSheet("border: none;")
        if(index > 0):
            index = index - 1
            set_widget = self.nav_v_content.itemAt(index).widget()
            set_widget.setStyleSheet("border: 1px solid rgb(255,0,0);")
        elif(index == 0):
            set_widget = self.nav_v_content.itemAt(index).widget()
            set_widget.setStyleSheet("border: 1px solid rgb(255,0,0);")
  
    
    def move_down(self):
        global index

        set_widget = self.nav_v_content.itemAt(index).widget()
        set_widget.setStyleSheet("border: none;")
        if(index < 4):
            index = index + 1
            set_widget = self.nav_v_content.itemAt(index).widget()
            set_widget.setStyleSheet("border: 1px solid rgb(255,0,0);")
        elif(index == 4):
            set_widget = self.nav_v_content.itemAt(index).widget()
            set_widget.setStyleSheet("border: 1px solid rgb(255,0,0);")

    def select(self):
        global index
        if(index == 4):
            mailbox.put_message_client("Client Requests Assistance")

    def on_press(self,key):
        if(key.char == '1'):
            self.move_up()
        elif(key.char == '2'):
            self.move_down()
        elif(key.char =='3'):
            self.select()
            print("selected")
        else:
            print("other")


    def __init__(self):
        super().__init__()
        '''
        Create the base layer of the application
        '''
        stop_run_continously = run_continuously()
        #region
        #StyleSheets
        shadow = QGraphicsDropShadowEffect()
        shadow2 = QGraphicsDropShadowEffect()
        shadow3 = QGraphicsDropShadowEffect()
        shadow4 = QGraphicsDropShadowEffect()
        shadow5 = QGraphicsDropShadowEffect()
        shadow6 = QGraphicsDropShadowEffect()

        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0,60))
        shadow.setOffset(1)
        shadow2.setBlurRadius(20)
        shadow2.setColor(QColor(0,0,0,60))
        shadow2.setOffset(1)
        shadow3.setBlurRadius(20)
        shadow3.setColor(QColor(0,0,0,60))
        shadow3.setOffset(1)
        shadow4.setBlurRadius(20)
        shadow4.setColor(QColor(0,0,0,60))
        shadow4.setOffset(1)
        shadow5.setBlurRadius(20)
        shadow5.setColor(QColor(0,0,0,60))
        shadow5.setOffset(1)
        shadow6.setBlurRadius(20)
        shadow6.setColor(QColor(0,0,0,60))
        shadow6.setOffset(1)


        #Create a Widget
        self.setWindowTitle("AHD Final Project")
        self.disply_width = 1280
        self.display_height = 720
        self.resize(self.disply_width, self.display_height)
        self.setMaximumSize(QSize(1280, 720))
        self.setMinimumSize(QSize(1280, 720))
        
        self.window = QWidget(self)
        #Create the panes
        self.layout = QHBoxLayout(self.window)
        self.left_side = QWidget()
        self.left_side.setMinimumSize(QSize(640,720))
        self.right_side = QWidget()
        self.right_side.setMinimumSize(QSize(640,720))

        self.layout.addWidget(self.left_side)
        self.layout.addWidget(self.right_side)

        self.left_layout_vertical = QVBoxLayout(self.left_side)
        self.left_layout_vertical.setSpacing(20)
        self.left_layout_1 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_1)
        self.left_layout_2 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_2)
        self.left_layout_3 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_3)
        self.left_layout_4 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_4)
        #endregion

        '''
        Create the LED Controls
        '''
        #region
        self.light_widget = QWidget()
        self.left_layout_2.addWidget(self.light_widget)
        #Create VBox
        self.light_v_layout = QVBoxLayout(self.light_widget)
        #Create Title
        self.light_title_widget = QWidget()
        self.light_v_layout.addWidget(self.light_title_widget)
        self.light_title = QLabel(self.light_title_widget)
        self.light_title.setText("Lighting Control")
        #Create the Buttons
        self.button_1 = QPushButton()
        self.button_1.setText("Toggle LED")
        self.button_1.clicked.connect(lambda: GPIO_Test.toggle_LED(26))
        self.button_2 = QPushButton()
        self.button_2.setText("Toggle LED 2")
        self.button_2.clicked.connect(lambda: GPIO_Test.toggle_LED(19))
        self.button_3 = QPushButton()
        self.button_3.setText("Toggle LED 3")
        self.button_3.clicked.connect(lambda: GPIO_Test.toggle_LED(13))
        #Create the horizontal button arrangement
        self.light_h_widget = QWidget()
        self.light_h_layout = QHBoxLayout(self.light_h_widget)
        self.light_v_layout.addWidget(self.light_h_widget)
        self.light_h_widget.setMinimumHeight(80)
        self.light_h_layout.addWidget(self.button_1)
        self.light_h_layout.addWidget(self.button_2)
        self.light_h_layout.addWidget(self.button_3)

        #Set Styles
        self.light_v_layout.setContentsMargins(0,0,0,0)
        self.light_v_layout.setSpacing(0)
        self.light_widget.setStyleSheet("background-color: rgb(255,255,255);")
        self.light_widget.setGraphicsEffect(shadow3)
        self.light_title_widget.setStyleSheet("background-color: rgb(106,180,172);")
        self.light_title_widget.setMaximumHeight(90)
        self.light_title.setStyleSheet("color: rgb(255,255,255);")
        self.light_title.setFont(QFont('PibotoLt',15))
        self.light_title.setGeometry(QRect(25,35,500,50))
        #endregion

        '''
        Create Temperature Controls
        '''
        #region
        self.temp_widget = QWidget()
        self.left_layout_3.addWidget(self.temp_widget)

        #Create VBox
        self.temp_v_layout = QVBoxLayout(self.temp_widget)

        #Create Title
        self.temp_title_widget = QWidget()
        self.temp_v_layout.addWidget(self.temp_title_widget)
        self.temp_title = QLabel(self.temp_title_widget)
        self.temp_title.setText("Temperature Control")
        self.temp_title.setFont(QFont('PibotoLt',15))

        #Put slider at top and value
        self.temp_slider_widget = QWidget()
        self.temp_slider_widget.setMaximumHeight(60)
        self.temp_v_layout.addWidget(self.temp_slider_widget)
        self.temp_slider_layout = QHBoxLayout(self.temp_slider_widget)
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setFocusPolicy(Qt.StrongFocus)
        self.temp_slider.setMinimum(0)
        self.temp_slider.setMaximum(100)
        self.temp_slider.setMaximumWidth(400)
        self.temp_slider.setMinimumWidth(400)
        self.temp_slider.setValue(GPIO_Test.get_Temperature())
        self.temp_slider.setTickInterval(1)
        self.temp_slider_layout.addWidget(self.temp_slider, alignment = Qt.AlignHCenter)
        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.updateTemp)
        self.temp_timer.start(5000)
       
        #Put button at bottom
        self.button_4 = QPushButton()
        self.button_4.setText("Set Temperature")
        self.button_4.clicked.connect(lambda: GPIO_Test.set_Temperature(self.temp_slider.value()))
        self.temp_v_layout.addWidget(self.button_4)

        #Create Temperature Label
        self.temp_label_widget = QWidget()
        self.temp_slider_layout.addWidget(self.temp_label_widget)
        self.temp_value = QLabel(self.temp_label_widget)
        self.temp_label_widget.setMaximumWidth(40)
        self.temp_value.setText(str(GPIO_Test.get_Temperature()))
        self.temp_value.setFont(QFont('PibotoLt', 10))
        self.temp_value.move(0,10)
        self.temp_slider.valueChanged.connect(self.get_Temp_Slider)

        #Set Styles
        self.temp_v_layout.setContentsMargins(0,0,0,0)
        self.temp_v_layout.setSpacing(0)
        self.temp_widget.setStyleSheet("background-color: rgb(255,255,255);")
        self.temp_widget.setGraphicsEffect(shadow2)
        self.temp_title_widget.setStyleSheet("background-color: rgb(106,180,172);")
        self.temp_title_widget.setMaximumHeight(100)
        self.temp_title.setStyleSheet("color: rgb(255,255,255);")
        self.temp_title.setFont(QFont('PibotoLt',15))
        self.temp_title.setGeometry(QRect(25,35,500,50))
        #endregion
        
        '''
        Create the message box and command list
        '''
        #region
        #Create the Hbox for messages and command list
        self.msg_command_widget = QWidget()
        self.left_layout_4.addWidget(self.msg_command_widget)
        self.msg_command_layout = QHBoxLayout(self.msg_command_widget)
        self.msg_command_layout.setSpacing(20)

        #Create the V Box for the messages
        self.msg_widget = QWidget()
        self.msg_command_layout.addWidget(self.msg_widget)
        self.msg_widget.setStyleSheet("background-color: rgb(255,255,255);")
        self.msg_widget.setGraphicsEffect(shadow4)
        self.msg_v_layout = QVBoxLayout(self.msg_widget)

        #Create message title
        self.msg_title_widget = QWidget()
        self.msg_title_widget.setStyleSheet("background-color: rgb(106,180,172);")
        self.msg_title_widget.setMaximumHeight(60)
        self.msg_v_layout.addWidget(self.msg_title_widget)
        self.msg_v_layout.setContentsMargins(0,0,0,0)
        self.msg_v_layout.setSpacing(0)
        self.msg_title = QLabel(self.msg_title_widget)
        self.msg_title.setText("Messages")
        self.msg_title.setStyleSheet("color: rgb(255,255,255);")
        self.msg_title.setFont(QFont('PibotoLt', 15))
        self.msg_title.setGeometry(QRect(25,0,500,50))

        #Create the message area
        self.msg_text_widget = QWidget()
        self.msg_text_widget.setMinimumHeight(100)
        self.msg_text = QTextEdit(self.msg_text_widget)
        self.msg_text.setMinimumWidth(300)
        self.msg_v_layout.addWidget(self.msg_text_widget)
        self.msg_text.setReadOnly(True)
        self.msg_text.setFont(QFont('PibotoLt', 10))
        self.msg_text.setPlainText("No Updates...")
        self.msg_timer = QTimer()
        self.msg_timer.timeout.connect(self.updateMsg)
        self.msg_timer.start(2000)



        #Creaet the Command List
        #Create the V Box for the cmd
        self.cmd_widget = QWidget()
        self.msg_command_layout.addWidget(self.cmd_widget)
        self.cmd_widget.setStyleSheet("background-color: rgb(255,255,255);")
        self.cmd_widget.setGraphicsEffect(shadow5)
        self.cmd_v_layout = QVBoxLayout(self.cmd_widget)

        #Create cmd title
        self.cmd_title_widget = QWidget()
        self.cmd_title_widget.setStyleSheet("background-color: rgb(106,180,172);")
        self.cmd_title_widget.setMaximumHeight(100)
        self.cmd_v_layout.addWidget(self.cmd_title_widget)
        self.cmd_v_layout.setContentsMargins(0,0,0,0)
        self.cmd_v_layout.setSpacing(0)
        self.cmd_title = QLabel(self.cmd_title_widget)
        self.cmd_title.setText("Command List")
        self.cmd_title.setStyleSheet("color: rgb(255,255,255);")
        self.cmd_title.setFont(QFont('PibotoLt', 15))
        self.cmd_title.setGeometry(QRect(25,0,500,50))

        #Create the cmd area
        self.cmd_text_widget = QWidget()
        self.cmd_text_widget.setMinimumHeight(100)
        self.cmd_text = QTextEdit(self.cmd_text_widget)
        self.cmd_text.setMinimumWidth(300)
        self.cmd_v_layout.addWidget(self.cmd_text_widget)
        self.cmd_text.setReadOnly(True)
        self.cmd_text.setFont(QFont('PibotoLt', 10))
        self.cmd_text.setPlainText("Single Blink")
        #endregion

        '''
        Create the Threshold Slider for Eye Detection
        '''
        #region
        self.threshold_widget = QWidget()
        self.left_layout_1.addWidget(self.threshold_widget)
        #Create VBox
        self.threshold_v_layout = QVBoxLayout(self.threshold_widget)
        #Create Title
        self.threshold_title_widget = QWidget()
        self.threshold_v_layout.addWidget(self.threshold_title_widget)
        self.threshold_title = QLabel(self.threshold_title_widget)
        self.threshold_title.setText("Eye Detection Threshold Control")
        
        #Create the HBox Layout
        self.threshold_slider_widget = QWidget()
        self.threshold_slider_widget.setMaximumHeight(80)
        self.threshold_h_layout = QHBoxLayout(self.threshold_slider_widget)
        self.threshold_v_layout.addWidget(self.threshold_slider_widget)

        #Put Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximumWidth(400)
        self.slider.setMinimumWidth(400)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(15)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.changeThreshold)
        self.threshold_h_layout.addWidget(self.slider, alignment=Qt.AlignHCenter)

        #Create Threshold Label
        self.threshold_label_widget = QWidget()
        self.threshold_h_layout.addWidget(self.threshold_label_widget)
        self.threshold_label = QLabel(self.threshold_label_widget)
        self.threshold_label.setFont(QFont('PibotoLt',10))
        self.threshold_label_widget.setMaximumWidth(70)
        self.threshold_label.move(0,15)
        self.threshold_label.setMinimumWidth(70)
        self.threshold_label.setText("15")
        self.slider.valueChanged.connect(self.get_Threshold_Slider)


        #Set Styles
        self.threshold_v_layout.setContentsMargins(0,0,0,0)
        self.threshold_v_layout.setSpacing(0)
        self.threshold_widget.setStyleSheet("background-color: rgb(255,255,255);")
        self.threshold_widget.setGraphicsEffect(shadow)
        self.threshold_title_widget.setStyleSheet("background-color: rgb(106,180,172);")
        self.threshold_title_widget.setMaximumHeight(90)
        self.threshold_title.setStyleSheet("color: rgb(255,255,255);")
        self.threshold_title.setFont(QFont('PibotoLt',15))
        self.threshold_title.setGeometry(QRect(25,35,500,50))
        
        #endregion

        '''
        Create the Video Feed
        '''
        #region
        #Create the Label that Holds the Image
        self.image_label1 = QLabel(self.right_side)
        self.image_label1.setGeometry(QRect(0,0,640,360))
        self.image_label2 = QLabel(self.right_side)
        self.image_label2.setGeometry(QRect(0,361,640,360))
        #self.image_label.setAlignment(Qt.AlignCenter)
        #Creates the Video Capture Thread
        self.thread = VideoThread()
        #Connects the signal to the update_image slot
        self.thread.change_pixmap_signal.connect(self.update_image)
        #Start the Thread
        self.thread.start()
        #endregion

        '''
        Create the Menu Navigation Menu
        '''
        #Create the Widget
        self.nav_widget = QWidget(self.right_side)
        self.nav_widget.setGeometry(QRect(275, 371, 325,330))
        self.nav_widget.setStyleSheet("background-color: rgb(250,255,255);")
        self.nav_widget.setGraphicsEffect(shadow6)
        self.nav_v_layout = QVBoxLayout(self.nav_widget)
        self.nav_title_widget = QWidget()
        self.nav_title_widget.setStyleSheet("background-color: rgb(106,180,172);")
        self.nav_title_widget.setMaximumHeight(60)
        self.nav_v_layout.addWidget(self.nav_title_widget)
        self.nav_v_layout.setContentsMargins(0,0,0,0)
        self.nav_v_layout.setSpacing(0)
        self.nav_title = QLabel(self.nav_title_widget)
        self.nav_title.setText("Commands")
        self.nav_title.setStyleSheet("color: rgb(255,255,255);")
        self.nav_title.setFont(QFont('PibotoLt', 15))
        self.nav_title.setGeometry(QRect(30,0,500,50))

        self.nav_content_widget = QWidget()
        self.nav_v_layout.addWidget(self.nav_content_widget)

        self.nav_v_content = QVBoxLayout(self.nav_content_widget)
        self.nav_option_1 = QLabel()
        self.nav_option_1.setText("Option 1")
        self.nav_option_1.setAlignment(Qt.AlignCenter)
        self.nav_v_content.addWidget(self.nav_option_1)
        self.nav_option_2 = QLabel()
        self.nav_option_2.setText("Option 2")
        self.nav_option_2.setAlignment(Qt.AlignCenter)
        self.nav_v_content.addWidget(self.nav_option_2)
        self.nav_option_3 = QLabel()
        self.nav_option_3.setText("Option 3")
        self.nav_option_3.setAlignment(Qt.AlignCenter)
        self.nav_v_content.addWidget(self.nav_option_3)
        self.nav_option_4 = QLabel()
        self.nav_option_4.setText("Option 4")
        self.nav_option_4.setAlignment(Qt.AlignCenter)
        self.nav_v_content.addWidget(self.nav_option_4)
        self.nav_option_5 = QLabel()
        self.nav_option_5.setText("Request Help")
        self.nav_option_5.setAlignment(Qt.AlignCenter)
        self.nav_v_content.addWidget(self.nav_option_5)

        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()




if __name__ == "__main__":
    #Creates an Application

    app = QApplication(sys.argv)
    a = App()
    a.show()
    test.startWebServer()
    app.exec_()
    GPIO_Test.__del__()
