# speak text from mqtt
import rospy
try:
    from Queue import Queue
except:
    from queue import Queue

import os
import traceback
import speech_recognition as sr
from rerecognizer import ReRecognizer
import json
import pyaudio
import threading
from bdbd.msg import AngledText
from audio_common_msgs.msg import AudioData

RATE = 1.0

def indexFromName(pa, name):
    devices = []
    for i in range(pa.get_device_count()):
        device = pa.get_device_info_by_index(i)

        if name in device['name'].lower():
            rospy.loginfo('Alsa input device: ' + device['name'])
            return i
        devices.append(device['name'])

    log.error("Could not find input device, available devices: " + str(devices))
    raise ValueError('device not found')

def main():

    continueThread = True
    def getVoice():
        while continueThread:
            angle = -1
            try:
                with mic as source:
                    # r.adjust_for_ambient_noise(source)
                    audio, angle = r.listen(source)
                    #print(audio.get_wav_data()[0:40])
                    rospy.loginfo('Sound heard at angle: ' + str(angle))
                    if audiopub.get_num_connections() > 0:
                        audiopub.publish(audio.get_wav_data())
                    text = recognizer(audio, credentials_json=google_key)
                    rospy.loginfo('we heard statement: ' + text)
                    voiceQueue.put([text, angle])
            except sr.UnknownValueError:
                rospy.loginfo('sound not recognized as speech')
                voiceQueue.put(['', angle])
            except:
                rospy.logwarn('Error in getVoice')
                rospy.logerror(traceback.format_exc())
                break

    rospy.init_node('hearit')
    textpub = rospy.Publisher('hearit/angled_text', AngledText, queue_size=10)
    audiopub = rospy.Publisher('audio', AudioData, queue_size=10)

    pa = pyaudio.PyAudio()
    device = indexFromName(pa, 'respeaker')
    mic = sr.Microphone(device_index=device)
    r = ReRecognizer()
    recognizer = r.recognize_google_cloud
    google_key = ''
    with open('/home/kent/secrets/stalwart-bliss-270019-7159f52eb443.json', 'r') as f:
        google_key = f.read()
    assert google_key, 'Google API read failed' 

    voiceQueue = Queue()
    voiceThread = threading.Thread(target=getVoice)
    voiceThread.daemon = True
    voiceThread.start()

    rospy.loginfo('hearit entering main loop')
    while voiceThread.is_alive() and not rospy.is_shutdown():
        try:
            if not voiceQueue.empty():
                statement, angle = voiceQueue.get()
                textpub.publish(statement, angle)
            rospy.sleep(RATE)
        except:
            rospy.logerror(traceback.format_exc())
            break

    continueThread = False

if __name__ == '__main__':
    main()