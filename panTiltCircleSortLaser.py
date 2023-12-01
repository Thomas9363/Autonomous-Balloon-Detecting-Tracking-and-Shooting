import cv2
import numpy as np
import time 
from adafruit_servokit import ServoKit
import RPi.GPIO as GPIO

laser = 12
LED=21
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(laser, GPIO.OUT)
GPIO.setup(LED, GPIO.OUT) 
GPIO.output(laser, False)
GPIO.output(LED, False)
inTarget=0

kit = ServoKit(channels=16,address=0x40) # Initialize the PCA9685 servo controller
PAN_CHANNEL,TILT_CHANNEL  = 0, 1 # Channels for servo control

PAN_ANGLE_MIN, PAN_ANGLE_MAX = 5, 175 # Servo angles range of motion
TILT_ANGLE_MIN, TILT_ANGLE_MAX = 50, 120

pan_initial_angle=110.0 # Set the initial angles for servos
tilt_initial_angle=100.0
kit.servo[PAN_CHANNEL].angle = pan_initial_angle # Move servos to initial angles
kit.servo[TILT_CHANNEL].angle = tilt_initial_angle

cols, rows =352, 288 # Display window 640x480, 352x288 or 320x240

pan_angle = pan_initial_angle # servo initial position in degree
tilt_angle= tilt_initial_angle 
offset=cols//20 #one degree is about 22 pixel
#offset=cols//40
cap = cv2.VideoCapture(0) # Initialize the video capture
parm_1=90
parm_2=30
min_Radius=60
max_Radius=90
track=0
def onTrack1(val):
    global parm_1
    parm_1=val
    print('parm1',parm_1)
def onTrack2(val):
    global parm_2
    parm_2=val
    print('parm2',parm_2)
def onTrack3(val):
    global min_Radius
    min_Radius=val
    print('Sat High',min_Radius)
def onTrack4(val):
    global max_Radius
    max_Radius=val
    print('Sat High',max_Radius)
def onTrack5(val):
    global track
    track=val
    print('Track',track)
cv2.namedWindow('myTracker')
cv2.setWindowProperty('myTracker', cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_NORMAL)
cv2.createTrackbar('parm1','myTracker',90,130,onTrack1)
cv2.createTrackbar('parm2','myTracker',10,60,onTrack2)
cv2.createTrackbar('minRadius','myTracker',10,90,onTrack3)
cv2.createTrackbar('maxRadius','myTracker',90,200,onTrack4)
cv2.createTrackbar('tracking/fire','myTracker',0,1,onTrack5)
cap.set(3, cols)
cap.set(4, rows)

pTime = 0 #time tracking for FPS
cTime = 0
fps=0

while True:
    ret, frame = cap.read()
#    frame=cv2.flip(frame,1)
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # convert to grayscale
    img = cv2.medianBlur(img, 5) # apply a blur using the median filter
#     circles = cv2.HoughCircles(image=img, method=cv2.HOUGH_GRADIENT, dp=0.9, # find circles using Hough transform
#                         minDist=50, param1=110, param2=39, maxRadius=150)
    circles = cv2.HoughCircles(image=img, method=cv2.HOUGH_GRADIENT, dp=0.9, 
                            minDist=50, param1=parm_1, param2=parm_2,minRadius=min_Radius, maxRadius=max_Radius) # find circles

    if np.any(circles): # if find circles
#        print("------------------")
#        print("number of circles: ", len(circles[0, :]))
#         circles1=sorted(circles[0], key=lambda x:x[2],reverse=True) # sort circles
        circles1=sorted(circles[0], key=lambda x:x[2],reverse=True) # sort circles
        for co, i in enumerate(circles1, start=1):
            if co==1: # largest circle
                cv2.circle(frame,(i[0],i[1]),i[2],(0,0,255),2) # draw a red circle around
                circle_center_x=int(i[0])
                circle_center_y=int(i[1])
            else:
                cv2.circle(frame,(i[0],i[1]),i[2],(0,255,0),2) # other small circles draw green circles
            cv2.circle(frame,(i[0],i[1]),2,(0,0,255),3) # draw a red dot at the center
            if track==1:
                pan_error=circle_center_x-cols//2
                tilt_error=circle_center_y-rows//2

                if pan_error >offset:
                    pan_angle -= 0.3 #0.3
                if pan_error< -offset:
                    pan_angle += 0.3
                pan_angle = np.clip(pan_angle, PAN_ANGLE_MIN, PAN_ANGLE_MAX)    
                kit.servo[0].angle = pan_angle
#                print(circle_center_x, ",", "{0:.2f}".format(pan_angle))
                
                if tilt_error > offset:
                    tilt_angle += 0.3
                if tilt_error< -offset:
                    tilt_angle -= 0.3
                tilt_angle = np.clip(tilt_angle, TILT_ANGLE_MIN, TILT_ANGLE_MAX) 
                kit.servo[1].angle = tilt_angle

                if abs(pan_error)<offset and abs(tilt_error)<offset: 
                    inTarget=inTarget+1
                    if inTarget>40: #in target for a period of time, say 13 counts
                        GPIO.output(laser, True) # turn on laser and led on 
                        GPIO.output(LED, True)
                else:
                    inTarget=0 # reset target count if move out
                    GPIO.output(laser, False)
                    GPIO.output(LED, False)
            
                cv2.rectangle(frame,(cols//2-offset, rows//2-offset),(cols//2+offset, rows//2+offset),(0,255,255),1) #draw target
                cv2.line(frame, (circle_center_x, 0), (circle_center_x, rows), (0, 255, 255), 1) #draw moving cross (yellow)
                cv2.line(frame, (0, circle_center_y), (cols, circle_center_y), (0, 255, 255), 1) 
        
    cTime = time.time() # calculate and display FPS
    fps = 0.9*fps+0.1*(1/(cTime-pTime))
    pTime = cTime
    cv2.putText(frame, f"FPS : {int(fps)}", (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2) 
    
    cv2.imshow("Frame", frame) # Show the frame
    
    if cv2.waitKey(1) & 0xFF == ord('q'): # Break the loop when 'q' is pressed
        break

kit.servo[0].angle = pan_initial_angle  # Reset the servos to their initial positions before exiting the program
kit.servo[1].angle = tilt_initial_angle

cap.release() # Release the video capture and clean up
cv2.destroyAllWindows()
