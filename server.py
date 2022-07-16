import flask
from flask import Flask
from flask_socketio import SocketIO
from flask_socketio import Namespace, emit
from flask_socketio import join_room, leave_room
import time
from firebase_admin import messaging, initialize_app
from collections import deque
import queue
import os
import intruder_detection_utils

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@socketio.on('connect', namespace='/android')
def connect(auth):
    print("Android device connected")
    join_room('android_room')
    

@socketio.on('disconnect', namespace='/android')
def disconnect():
    leave_room('android_room')
    print("Android device disconnected")

@socketio.on('firebase_token', namespace='/android')
def on_token_recieved(token):
    global iot_namespace
    iot_namespace.token = token
    print("Token recieved: ", token)

class WriteableQueue(deque):

    def __init__(self, *args, **kwargs):
        super().__init__(self,maxlen=35, *args, **kwargs)

    def write(self, data):
        if data:
            self.append(data)

    def __iter__(self):
        return iter(self.popleft, None)

    def popleft(self):
        if(len(self) > 0):
            return super().popleft()
        else:
            return None

    def close(self):
        self.append(None)

def send_intruder_notif(probability):
    android_config = messaging.AndroidConfig(priority="high")
    message = messaging.Message(
        topic='DisconnectNotification',
        notification=messaging.Notification(
            title = "Intruder Detected",
            body = f"Intruder detected with confidence {probability}%"
        ),
        android=android_config,
        
    )
    print(messaging.send(message))

def send_disconnect_notif():
    android_config = messaging.AndroidConfig(priority="high")
    message = messaging.Message(
        topic='DisconnectNotification',
        notification=messaging.Notification(
            title = "Detection device disconnected",
            body = "Intruder detection IOT device has disconnected"
        ),
        android=android_config,
        
    )
    print(messaging.send(message))

class IOTNamespace(Namespace):
    buff = WriteableQueue()


    def on_start_pinging(self):
        self.stream = queue.Queue()
        maker = intruder_detection_utils.MakePredictions()
        while True:
            emit('failsafe_ping', namespace='/iot')
            print("Quering")
            time.sleep(10)
            try:
                if(len(self.buff) > 25):
                    bufftirator = iter(self.buff)
                    for _ in range(25):
                        maker.add_frame(next(bufftirator))
                    
                    is_normal, probablilty = intruder_detection_utils.make_predictions(maker)
                    if(not is_normal):
                        send_intruder_notif(probablilty)
                res = self.stream.get_nowait()
            except StopIteration:
                pass
            except queue.Empty:
                time.sleep(2)
                try:
                    res = self.stream.get_nowait()
                except queue.Empty:
                    print("Client Disconnected!!")
                    send_disconnect_notif()
                    break
            maker.clear_frames()
            time.sleep(10)

    def on_connect(self):
        print("Client connected")
        

    def on_failsafe_response(self):
        print("Response recieved")
        self.stream.put(True)

    def on_stream_footage(self,data):
        self.buff.write(data)
        # emit('footage_view',data,namespace='/android',to='android_room')



@app.route('/iot_footage_view')
def footage_view():
    global iot_namespace
    return flask.Response(iot_namespace.buff,
    content_type='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/ec2-user/intruder_detection/intruder-detection-41636-firebase-adminsdk-a3r61-30407664de.json"
    initialize_app()
    global iot_namespace
    iot_namespace = IOTNamespace('/iot')
    socketio.on_namespace(iot_namespace)
    socketio.run(app,host="0.0.0.0", port=80)
    