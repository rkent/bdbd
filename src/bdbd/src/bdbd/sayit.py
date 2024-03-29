#!/usr/bin/env python
import rospy
from std_msgs.msg import String, Bool
from bdbd_common.srv import SpeechCommand, SpeechCommandResponse
try:
    from Queue import Queue
except:
    from queue import Queue
from espeakng import ESpeakNG
from bdbd.libpy.googleTTS import GoogleTTS
import traceback

#ENGINE = 'espeak-ng'
ENGINE = 'google'

PERIOD = 0.1 # update rate in seconds

class SayIt():
    def __init__(self):
        self._espeak = ESpeakNG(voice='en-gb-x-gbclan')
        self._googleTTS = GoogleTTS()
        self._espeak.volume = 40
        rospy.init_node('sayit')
        self._sub = rospy.Subscriber('sayit/text', String, self.on_sayit_text)
        self._talkingPub = rospy.Publisher('sayit/talking', Bool, queue_size=10)
        self._service = rospy.Service('sayit', SpeechCommand, self.on_service_call)
        self._queue = Queue()

    def on_sayit_text(self, msg):
        text = msg.data
        rospy.loginfo('Request to say: ' + text)
        self._queue.put([text, None])

    def on_service_call(self, req):
        if req.command == 'say':
            responseQueue = Queue()
            self._queue.put([req.detail, responseQueue])
            response = responseQueue.get()
            return(response)
        else:
            return('invalid')

    def run(self):
        while not rospy.is_shutdown():
            try:
                while not self._queue.empty():
                    # don't let requests accumulate
                    while self._queue.qsize() > 2:
                        text, responseQueue = self._queue.get()
                        if responseQueue:
                            responseQueue.put('skipped')

                    text, responseQueue = self._queue.get()
                    rospy.loginfo('Saying:' + text)
                    self._talkingPub.publish(True)
                    if ENGINE == 'google':
                        self._googleTTS.say(text)
                    else:
                        self._espeak.say(text, sync=True)
                    self._talkingPub.publish(False)
                    if responseQueue:
                        responseQueue.put('done')
                    rospy.loginfo('Done saying it')
            except:
                rospy.logerr_once(traceback.format_exc())

            rospy.sleep(PERIOD)

def main():
    sayit = SayIt()
    sayit._queue.put(['This is BDBD robot', None])
    sayit.run()

if __name__ == '__main__':
    main()