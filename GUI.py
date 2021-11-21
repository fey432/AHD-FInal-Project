#region imports
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QRect, QSize, QObject, QEvent
import sys, cv2, time, threading, schedule
import subprocess as sp
from multiprocessing import Process
import numpy as np
import imutils
import dlib
from flask import Flask, render_template, request, Response
import socket
import netifaces as ni
import test

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

    def detect_eyes(img,classifier):
        gray_frame = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        eye_cascade_2 = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        eyes = eye_cascade_2.detectMultiScale(gray_frame,1.3,5)

    def cut_eyebrows(img):
        height, width = img.shape[:2]
        eyebrow_h = int(height/4)
        img = img[eyebrow_h:height,0:width]
        return img

    def blob_process(img,detector):
        gray_frame = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        _,img = cv2.threshold(gray_frame,42,255,cv2.THRESH_BINARY)
        img = cv2.erode(img,None,iteration=2)
        img = cv2.dilate(img,None,iteration=4)
        img = cv2.medianBlur(img,5)
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
            test.updateFrame(img)
            if ret:
                self.change_pixmap_signal.emit(img)

            #Detect Faces
            if self.count > 10:
                gray_picture = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray_picture,1.1,5)
                #Draw the rectangle around face
                for (x,y,w,h) in faces:
                    cv2.rectangle(img,(x,y),(x+w,y+h),(255,255,0),2)
                    #Display starting x,y points with width and height
                    print("face")
                    print(x,y,w,h)
                #FIXME: coding error with gray_face
                # gray_face = gray_picture[faces.y:faces.y+int(faces.h/2),faces.x:faces.x+faces.w]
                # face = img[face.y:face.y+face.h,face.x:face.x+face.w]
                # eyes = self.eye_cascade.detectMultiScale(gray_face)
                # for (ex,ey,ew,eh) in eyes:
                #     cv2.rectangle(face,(ex,ey),(ex+ew,ey+eh),(0,255,255),2)
                #     print("eyes")
                #     print(ex,ey,ew,eh)

                #FIXME: fix the cut_eyebrows part
                # eye = self.cut_eyebrows(eyes)
                # keypoints = self.blob_process(eye,self.detector)
                # cv2.drawKeypoints(eye,keypoints,eye,(0,0,255))
                # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS

                self.count = 0                  

            self.count = self.count+1

            #cv2.imshow('my image',img)
 
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


        self.button_1 = QPushButton()
        self.button_1.setText("1")
        self.button_2 = QPushButton()
        self.button_2.setText("2")
        self.button_3 = QPushButton()
        self.button_3.setText("3")

        self.left_layout_1.addWidget(self.button_1)
        self.left_layout_1.addWidget(self.button_2)
        self.left_layout_1.addWidget(self.button_3)

        self.button_4 = QPushButton()
        self.button_4.setText("4")
        self.button_5 = QPushButton()
        self.button_5.setText("5")
        self.button_6 = QPushButton()
        self.button_6.setText("6")

        self.left_layout_2.addWidget(self.button_4)
        self.left_layout_2.addWidget(self.button_5)
        self.left_layout_2.addWidget(self.button_6)
        
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
    test.startWebServer()
    app.exec_()
