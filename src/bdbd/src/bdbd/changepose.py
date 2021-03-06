#!/usr/bin/env python

# ROS node to implement changePose action server

# generally follows http://wiki.ros.org/actionlib_tutorials/Tutorials/Writing%20a%20Simple%20Action%20Server%20using%20the%20Execute%20Callback%20%28Python%29

import os
import time
import rospy
import actionlib
import traceback
import math
from bdbd.msg import ChangePoseFeedback, ChangePoseResult, ChangePoseAction
from bdbd_common.geometry import pose3to2, D_TO_R, Motor
from bdbd_common.pathPlan2 import PathPlan
from bdbd_common.utils import fstr
from nav_msgs.msg import Odometry

class ChangePose():
    def __init__(self):
        self._feedback = ChangePoseFeedback()
        self._result = ChangePoseResult()
        self._actionServer = actionlib.SimpleActionServer('changepose', ChangePoseAction, auto_start=False)
        self._actionServer.register_goal_callback(self.goal_cb)
        self._actionServer.register_preempt_callback(self.preempt_cb)
        self._actionServer.start()
        self._motor = Motor()
        self.count = 0
        self.skip = 4
        self.psum = [0.0, 0.0, 0.0]
        self.tsum = [0.0, 0.0, 0.0]
        self.tt = 0.0

    def preempt_cb(self):
        print('preempted')
        traceback.print_stack()
        if hasattr(self, 'odom_sub'):
            self.odom_sub.unregister()
        return

    def goal_cb(self):
        print('accept new goal')
        goal = self._actionServer.accept_new_goal()
        self.last_time = None
        endPose2d = pose3to2(goal.endPose)
        self.pp = PathPlan()
        rospy.loginfo('Executing changePose with goal x: {:6.3f} y: {:6.3f} theta: {:6.3f}'.format(*endPose2d))
        self.pp.start(goal.startPose, goal.endPose)
        for seg in self.pp.path:
            rospy.loginfo(fstr(seg))

        vx_start = goal.startTwist.linear.x
        omega_start = goal.startTwist.angular.z
        vx_end = goal.endTwist.linear.x
        omega_end = goal.endTwist.angular.z
        vhat_start = max(0.0, abs(vx_start) + self.pp.rhohat * abs(omega_start))
        vhat_end = max(0.0, abs(vx_end) + self.pp.rhohat * abs(omega_end))
        vhat_cruise = goal.vcruise
        s_plan = self.pp.speedPlan(vhat_start, vhat_cruise, vhat_end, u=0.50)
        for seg in s_plan:
            rospy.loginfo(fstr(seg))

        # start executing the action, driven by odometry message receipt
        self.odom_sub = rospy.Subscriber('/t265/odom/sample', Odometry, self.odom_cb, tcp_nodelay=True)

    def odom_cb(self, odometry):
        then = float(odometry.header.stamp.secs + 1.0e-9 * odometry.header.stamp.nsecs)

        pose_m = pose3to2(odometry.pose.pose)
        twist3 = odometry.twist.twist
        twist_r = (twist3.linear.x, twist3.linear.y, twist3.angular.z)

        if self.last_time is None:
            self.last_time = then
            return

        self.count += 1

        for i in range(3):
            self.psum[i] += pose_m[i]
            self.tsum[i] += twist_r[i]

        if self.count % self.skip != 0:
            return

        pasum = []
        tasum = []
        for i in range(3):
            pasum.append(self.psum[i] / self.skip)
            tasum.append(self.tsum[i] / self.skip)

        self.psum = [0.0, 0.0, 0.0]
        self.tsum = [0.0, 0.0, 0.0]
        dt = then - self.last_time
        self.tt += dt
        self.last_time = then
        lag = rospy.get_time() - then

        (v_new, o_new) = self.pp.controlStep(dt, pasum, tasum)
        #if self.count % 5 == 0:
        if True:
            print(' ')
            print('tt: {:6.3f} '.format(self.tt) + fstr({
                'r_m': pasum,
                'nr_m': self.pp.near_robot_m,
                't_t': tasum,
                'nw_p': self.pp.near_wheel_p,
            }, '8.5f'))
            print(fstr({
                'o_n': o_new,
                'v_n': v_new,
                'dy': self.pp.dy_r * 100.0,
                'dydt': self.pp.dydt * 100.0,
                'psi': self.pp.psi / D_TO_R,
                'oa': self.pp.oa,
                'va': self.pp.va,
                'lagms': lag * 1000.,
                'kn': self.pp.kappa_new,
                'ka': self.pp.kappaa,
                'dsinpdt': self.pp.dsinpdt,
                'vha': self.pp.vhata,
                'vhn': self.pp.vhat_new,
                'vhp': self.pp.vhat_plan,
                'ev': self.pp.va
            }))
        self._feedback.fraction = self.pp.lp_frac
        self._feedback.dy = self.pp.dy_r
        self._feedback.vnew = v_new
        self._feedback.onew = o_new
        self._feedback.psi = self.pp.psi
        self._feedback.rostime = then
        self._feedback.tt = self.tt

        # calculate the dhat error to the target pose, dhat adding an angle error addition to distance
        dhat = math.sqrt( (pose_m[0] - self.pp.end_m[0])**2 + (pose_m[1] - self.pp.end_m[1])**2 )
        dhat += self.pp.rhohat * (1.0 - math.cos(pose_m[2] - self.pp.end_m[2]))
        self._feedback.dhat = dhat

        self._actionServer.publish_feedback(self._feedback)

        if abs(v_new) < 1.e-3 and self.pp.lp_frac > 0.999 and self._actionServer.is_active():
            print(fstr({'v_new': v_new, 'lp_frac': self.pp.lp_frac}))
            self.finish()

    def finish(self):
        print('finish called')
        if hasattr(self, 'odom_sub'):
            self.odom_sub.unregister()

        self._result.yerror = .01
        self._result.terror = .02
        rospy.loginfo('Done')
        self._actionServer.set_succeeded(self._result)

def main():
    rospy.init_node('changepose')
    rospy.loginfo('{} starting with PID {}'.format(os.path.basename(__file__), os.getpid()))
    server = ChangePose()
    rospy.spin()

if __name__ == '__main__':
    main()
