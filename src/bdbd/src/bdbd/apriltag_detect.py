import rospy
from bdbd_common.srv import ObjectDetect, ObjectDetectResponse
from sensor_msgs.msg import CompressedImage
from bdbd_common.imageRectify import ImageRectify

from cv_bridge import CvBridge
from rospy import ServiceException
import apriltag
import cv2
import time
import numpy as np
try:
    from Queue import Queue
except:
    from queue import Queue

OBJECT_COUNT = 12 # number of objects to attempt to classify

service_queue = Queue()
detector = apriltag.Detector()
image_rectifiers = {}

def getCameraTopicBase(imageTopic):
    baseTopic = None
    offset = imageTopic.find('/image_')
    if offset >= 0:
        baseTopic = imageTopic[:offset]
    return baseTopic

def on_service_call(req):
    responseQueue = Queue()
    service_queue.put((req, responseQueue))
    response = responseQueue.get()
    return response

def main():
    rospy.init_node('apriltag_detect')
    rospy.Service('/bdbd/apriltagDetect', ObjectDetect, on_service_call)
    image_pub = rospy.Publisher('/bdbd/apriltagDetect/image_raw/compressed', CompressedImage, queue_size=1)

    cvBridge = CvBridge()

    while not rospy.is_shutdown():
        try:
            rospy.loginfo('waiting for service request')
            service_request = service_queue.get()
            print('got service request')
            start = time.time()

            service_msg = service_request[0]
            response_queue = service_request[1]
            if service_msg.image_topic:
                imageTopic = service_msg.image_topic
                image_msg = rospy.wait_for_message(imageTopic, CompressedImage)
            else:
                image_msg = service_msg.image

            # get rectifier appropriate for the image topic
            cameraTopicBase = getCameraTopicBase(imageTopic)
            if cameraTopicBase in image_rectifiers:
                print('Found image rect for base')
                imageRectify = image_rectifiers[cameraTopicBase]
            else:
                print('looking for image rect for base')
                try:
                    imageRectify = ImageRectify(cameraTopicBase, do_publish=True)
                except rospy.ROSException as exception:
                    rospy.logwarn('Cannot rectify, proceeding without: ({})'.format(exception))
                    imageRectify = None
            if imageRectify and imageRectify.info_msg.distortion_model != 'equidistant':
                imageRectify = None
            image_rectifiers[cameraTopicBase] = imageRectify
            if imageRectify:
                image = imageRectify.get(image_msg)
            else:
                print('no imageRectify')
                image = cvBridge.compressed_imgmsg_to_cv2(image_msg, desired_encoding='bgr8')
            print(image.shape)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = detector.detect(image)
            print('elapsed time {}'.format(time.time() - start))
            print('result\n', results)
            image_pub.publish(image_msg)

            if results:
                result = results[0]
                #for member in inspect.getmembers(result):
                #    print('model member {}'.format(member[0]))

                corners = result.corners
                print(corners)
            else:
                rospy.loginfo('no results')

            odr = ObjectDetectResponse()
            # match the response header to the request header for synchronization
            odr.header = service_msg.header
            odr.image = image_msg

            for result in results:
                odr.scores.append(result.decision_margin/100.)
                name = '{}_{}'.format(result.tag_family.decode('ascii'), result.tag_id)
                odr.class_names.append(name)
                odr.class_ids.append(result.tag_id)
                corners = result.corners.astype(np.uintc)
                print('xmin: {}'.format(corners[0][0]))
                odr.xmin.append(corners[0][0])
                odr.ymin.append(corners[0][1])
                odr.xmax.append(corners[2][0])
                odr.ymax.append(corners[2][1])

            response_queue.put(odr)

        except ServiceException:
            rospy.logwarn('Service Exception. Waiting for service')
            try:
                rospy.wait_for_service('/bdbd/objectDetect')
            except:
                print('Exception while waiting for service, exiting')
                break
            continue

if __name__ == '__main__':
    main()
