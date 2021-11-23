#region imports
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QRect, QSize, QObject, QEvent
import sys, cv2, time, threading, schedule, test
import subprocess as sp
from multiprocessing import Process
import numpy as np
#import netifaces as ni
import GPIO_Test

blob_threshold = 50

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
        self.detector_params.filterByArea = True
        self.detector_params.maxArea = 1500
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
        face = classifier.detectMultiScale(gray_frame, 1.3, 5)
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
        eyes = classifier.detectMultiScale(gray_frame, 1.3, 5) # detect eyes
        width = np.size(img, 1) # get face frame width
        height = np.size(img, 0) # get face frame height
        left_eye = None
        left_ew = [0,0,0,0]
        right_eye = None
        right_ew = [0,0,0,0]
        for (x, y, w, h) in eyes:
            if y > height / 2:
                pass
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
        img = cv2.erode(img,None,2)
        img = cv2.dilate(img,None,4)
        img = cv2.medianBlur(img,3)
        keypoints = detector.detect(img)
        return keypoints

    def run(self):
        # capture from web cam
        cap = cv2.VideoCapture(0)        
        cap.set(3, 1280) # set video width
        cap.set(4, 720) # set video height

        while (self._run_flag):
            #Read images from Camera
            ret, img = cap.read()
            img = cv2.flip(img,1)
            cv2.rectangle(img,(self.fw[0],self.fw[1]),(self.fw[0]+self.fw[2],self.fw[1]+self.fw[3]),(255,255,0),2) 
            cv2.rectangle(img,(self.ew[0][0]+self.fw[0],self.ew[0][1]+self.fw[1]),(self.ew[0][0]+self.fw[0]+self.ew[0][2],self.ew[0][1]+self.fw[1]+self.ew[0][3]),(255,0,255),2) 
            cv2.rectangle(img,(self.ew[1][0]+self.fw[0],self.ew[1][1]+self.fw[1]),(self.ew[1][0]+self.fw[0]+self.ew[1][2],self.ew[1][1]+self.fw[1]+self.ew[1][3]),(255,0,255),2) 
            cv2.circle(img, (self.ew[0][0]+self.fw[0]+self.ep[0][0],self.ew[0][1]+self.fw[1]+self.ep[0][1]), 10, (0,0,255), 10) 
            cv2.circle(img, (self.ew[1][0]+self.fw[0]+self.ep[1][0],self.ew[1][1]+self.fw[1]+self.ep[1][1]), 10, (0,0,255), 10)
                
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
                            #eye = self.cut_eyebrows(eye)
                            keypoints = self.blob_process(eye, blob_threshold, self.detector)
                            for keypoint in keypoints:
                                self.ep[self.eyenum] = [int(keypoint.pt[0]),int(keypoint.pt[1])]
                                #print(self.ep[self.eyenum])
                        self.eyenum = self.eyenum+1
                
                    #Determine if person blinked (right now only depened on eye detection, eye tracking is not working great)
                    #print(self.eye_flag)
                    match self.State:
                        case "NOT_DETECTED":
                            if (sum(self.eye_flag)>1):
                                self.State = "DETECTED"
                        case "DETECTED":
                            if (sum(self.eye_flag)<2):
                                iter = 1
                                prev_eye_flag = self.eye_flag
                                self.State = "BLINKING"
                        case "BLINKING":
                            if(iter>4):
                                print("lost eye detection")
                                self.State = "NOT_DETECTED"
                            else:
                                if((sum(self.eye_flag)-sum(prev_eye_flag))<1):
                                    iter = iter+1
                                else:
                                    if(iter<3):
                                        if(prev_eye_flag[0]==0 and prev_eye_flag[0]==0):
                                            print("blink detected")
                                        elif(prev_eye_flag[0]==0):
                                            print("left wink detected")
                                        else:
                                            print("right wink detected")
                                    else: 
                                        if(prev_eye_flag[0]==0 and prev_eye_flag[0]==0):
                                            print("long blink detected")
                                        elif(prev_eye_flag[0]==0):
                                            print("long left wink detected")
                                        else:
                                            print("long right wink detected")
                                    self.State = "DETECTED"
                        case _:
                            self.State = "DETECTED"
                            
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
        self.image_label.setPixmap(qt_img)
    
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

    def __init__(self):
        super().__init__()
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
        self.left_layout_1 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_1)
        self.left_layout_2 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_2)
        self.left_layout_3 = QHBoxLayout()
        self.left_layout_vertical.addLayout(self.left_layout_3)

        self.button_1 = QPushButton()
        self.button_1.setText("1")
        self.button_2 = QPushButton()
        self.button_2.setText("2")
        self.button_3 = QPushButton()
        self.button_3.setText("3")

        self.left_layout_2.addWidget(self.button_1)
        self.left_layout_2.addWidget(self.button_2)
        self.left_layout_2.addWidget(self.button_3)

        self.button_4 = QPushButton()
        self.button_4.setText("4")
        self.button_5 = QPushButton()
        self.button_5.setText("5")
        self.button_6 = QPushButton()
        self.button_6.setText("6")

        self.left_layout_3.addWidget(self.button_4)
        self.left_layout_3.addWidget(self.button_5)
        self.left_layout_3.addWidget(self.button_6)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(100)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.changeThreshold)
        self.left_layout_1.addWidget(self.slider)
        
        #Create the Label that Holds the Image
        self.image_label = QLabel(self.right_side)
        self.image_label.setGeometry(QRect(0,0,640,360))
        #self.image_label.setAlignment(Qt.AlignCenter)
        #Creates the Video Capture Thread
        self.thread = VideoThread()
        #Connects the signal to the update_image slot
        self.thread.change_pixmap_signal.connect(self.update_image)
        #Start the Thread
        self.thread.start()
        

if __name__ == "__main__":
    #Creates an Application
    app = QApplication(sys.argv)
    a = App()
    a.show()
    #test.startWebServer()
    app.exec_()
    GPIO_Test.__del__()
