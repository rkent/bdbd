# Common geometry methods
D_TO_R = 3.1415926535 / 180. # degrees to radians

import tf
import math
import rospy
from geometry_msgs.msg import Quaternion, PoseStamped, PointStamped

def poseDistance(pose1, pose2):
    # calculate the distance between two PoseStamped types in the same frame
    if pose1.header.frame_id != pose2.header.frame_id:
        raise RuntimeError('poses must be in the same frame')
    p1 = pose1.pose.position
    p2 = pose2.pose.position
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def poseTheta(pose1, pose2):
    # calculate the rotation on z axis between two PoseStamped types
    if pose1.header.frame_id != pose2.header.frame_id:
        raise RuntimeError('poses must be in the same frame')
    q1 = q_to_array(pose1.pose.orientation)
    q2 = q_to_array(pose2.pose.orientation)
    a1 = tf.transformations.euler_from_quaternion(q1)
    a2 = tf.transformations.euler_from_quaternion(q2)
    return (a2[2] - a1[2])

def q_to_array(orientation):
    # return 4-element array from geometry_msgs/Quaternion.msg
    return [
        orientation.x,
        orientation.y,
        orientation.z,
        orientation.w
    ]

def array_to_q(array):
    #return geometry_msgs/Quaternion.msg from 4-element list
    q = Quaternion()
    q.x = array[0]
    q.y = array[1]
    q.z = array[2]
    q.w = array[3]
    return q

def zeroPose(frame):
    # a zero PoseStamped
    pose = PoseStamped()
    pose.header.frame_id = frame
    pose.header.stamp = rospy.Time(0)
    pose.pose.orientation.w = 1.0
    return pose

def zeroPoint(frame):
    # a zero PointStamped
    point = PointStamped()
    point.header.frame_id = frame
    point.header.stamp = rospy.Time(0)
    return point

def rotationCenter(frame, vx, vy, omega):
    # center of rotation in frame. See RKJ notebook 2020-07-10
    r = vx / omega
    a = vy / omega
    print(r, a)

    center = zeroPoint(frame)
    center.point.x = -a
    center.point.y = r
    return center