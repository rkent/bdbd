# chat with user
import rospy

import os
import traceback
from std_msgs.msg import String
from bdbd.msg import SpeechAction
from bdbd_common.srv import SpeechCommand
from bdbd.libpy.cleverbot import Cleverbot
from bdbd_common.srv import Dialog
from bdbd_common.doerRequest import DoerRequest
import rosservice

doerRequest = DoerRequest()

class Chatbot():
    def __init__(self):
        self.cleverbot = Cleverbot()
        try:
            doerRequest.ensure_doer('/bdbd/dialog', 'service', timeout=30.0)
        except:
            rospy.logwarn('chat failed to start dialog, maybe just a timeout')
        self.bdbdDialog = rospy.ServiceProxy('/bdbd/dialog', Dialog)

    def __call__(self, statement):
        try:
            useDialog = rosservice.get_service_list().count('/bdbd/dialog') > 0
            if useDialog:
                rospy.loginfo('asking dialog for response to <{}>'.format(statement))
                saying = self.bdbdDialog(statement, "").response
                rospy.loginfo('bdbd/dialog response is {}'.format(saying))
            else:
                rospy.loginfo('asking cleverbot for response to <{}>'.format(statement))
                response = self.cleverbot.getReply(statement)
                rospy.loginfo('cleverbot response is <{}>'.format(response))
                saying = "Sorry, brain freeze"
                if response['status_code'] == 200:
                    saying = response['output'].encode('ascii', 'ignore')
                else:
                    rospy.logwarn('cleverbot response code {}'.format(response['status_code']))
            return saying
        except:
            rospy.logerr('Error from chatbot: {}'.format(traceback.format_exc()))
            return "Sorry, error"
            
def main():

    def action_cb(msg):
        command = msg.command.lower()
        if command not in ['chat', 'chatservice']:
            return
        statement = msg.detail
        rospy.loginfo('chat will reply to <{}>'.format(statement))
        try:
            saying = chatbot(statement)
            if command == 'chat':
                sayit_pub.publish(saying)
            else:
                return saying
        except:
            rospy.logerr('Error from action_cb: {}'.format(traceback.format_exc()))
        

    rospy.init_node('chat')
    chatbot = Chatbot()
    rospy.loginfo('{} starting with PID {}'.format(os.path.basename(__file__), os.getpid()))
    doerRequest.Subscriber('/bdbd/speechResponse/action', SpeechAction, action_cb)
    rospy.Service('chat', SpeechCommand, action_cb)
    sayit_pub = rospy.Publisher('sayit/text', String, queue_size=10)

    rospy.spin()

if __name__ == '__main__':
    main()