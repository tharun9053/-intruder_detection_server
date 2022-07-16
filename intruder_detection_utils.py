from keras.models import load_model
import numpy as np
import cv2
import os
import queue
import multiprocessing

class MakePredictions:
    def __init__(self):
        self.frames = []
        self.model = load_model('/home/ec2-user/intruder_detection/Armed-Injured-and-other-Suspicious-Activity-Recognition-using-Drone-Surveillance/slowfast_finalmodel.hd5')
    
    def add_frame(self, data,  img_size = 224):
        frame_bin = data.strip(b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n').strip(b'\r\n')
        frame = np.frombuffer(frame_bin, dtype=np.uint8)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        frame = cv2.resize(frame, (img_size, img_size))
        self.frames.append(frame)
    
    def clear_frames(self):
        self.frames = []

    def predict(self, nb_frames = 25, img_size = 224):
        
        X = np.array(self.frames[:nb_frames])/255.0
        X = np.reshape(X, (1, nb_frames, img_size, img_size, 3))
        print("Starting prediction")
        predictions = self.model.predict(X)
        print(predictions)
        preds = predictions.argmax(axis = 1)
        return preds[0] == 7, predictions[0,preds[0]]


def make_predictions(maker):
    return maker.predict()