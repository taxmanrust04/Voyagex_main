#!/usr/bin/env python3
import time
import math
import pytest
import rclpy

from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy

from nav_msgs.msg import Odometry
from ackermann_msgs.msg import AckermannDrive
from mocap4r2_msgs.msg import RigidBodies, RigidBody
from geometry_msgs.msg import Pose, Point, Quaternion

from localization_kf.localization import Localization

class TestLocalizationIntegration:
    """
    Integration tests for Localization node.

    TC_INT_LOC_01: Pose updates when mocap pose changes
    TC_INT_LOC_02: Frozen mocap + moving vehicle -> odom still published
    TC_INT_LOC_03: Frozen mocap + stopped vehicle -> odom still published
    """

    # ---------------- setup / teardown ----------------

    def setup_method(self):
        rclpy.init()
        self.executor = SingleThreadedExecutor()

        # Node under test
        self.loc_node = Localization()
        self.executor.add_node(self.loc_node)

        # Helper test node
        self.node = rclpy.create_node('loc_test_node')
        self.executor.add_node(self.node)

        self.received_odom = None

        # Subscriber to output
        self.node.create_subscription(
            Odometry, '/odom', self.odom_cb, 10
        )

        # Publishers for inputs
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.pub_mocap = self.node.create_publisher(
            RigidBodies, '/pose_modelcars', qos
        )
        self.pub_speed = self.node.create_publisher(
            AckermannDrive, '/ackermann_drive_feedback', 10
        )

    def teardown_method(self):
        self.executor.shutdown()
        self.loc_node.destroy_node()
        self.node.destroy_node()
        rclpy.shutdown()

    # ---------------- helpers ----------------

    def odom_cb(self, msg):
        self.received_odom = msg

    def spin(self, duration=0.3):
        end = time.time() + duration
        while time.time() < end:
            self.executor.spin_once(timeout_sec=0.05)

    def publish_speed(self, speed):
        msg = AckermannDrive()
        msg.speed = speed
        self.pub_speed.publish(msg)

    def publish_mocap(self, x, y, yaw):
        msg = RigidBodies()

        body = RigidBody()
        body.rigid_body_name = '6'
        body.pose = Pose(
            position=Point(x=x, y=y, z=0.0),
            orientation=Quaternion(
                x=0.0,
                y=0.0,
                z=math.sin(yaw / 2.0),
                w=math.cos(yaw / 2.0),
            ),
        )

        msg.rigidbodies.append(body)
        self.pub_mocap.publish(msg)

    # ---------------- test cases ----------------

    def test_INT_LOC_ODOM_01_pose_changes(self):
        """
        TC_INT_LOC_01
        When mocap pose changes, localization must publish odom.
        """
        self.publish_mocap(0.0, 0.0, 0.0)
        self.spin()

        self.publish_mocap(1.0, 0.0, 0.0)
        self.spin()

        assert self.received_odom is not None, \
            "Expected odom when mocap pose changes"

    def test_INT_LOC_ODOM_02_frozen_pose_moving(self):
        """
        TC_INT_LOC_02
        Frozen mocap pose + speed > threshold → dead-reckoning odom published.
        """
        self.publish_speed(0.5)

        self.publish_mocap(1.0, 0.0, 0.0)
        self.spin()

        # Same pose again (frozen)
        self.publish_mocap(1.0, 0.0, 0.0)
        self.spin()

        assert self.received_odom is not None, \
            "Expected odom during frozen pose with vehicle moving"

    def test_INT_LOC_ODOM_03_frozen_pose_stopped(self):
        """
        TC_INT_LOC_03
        Frozen mocap pose + speed = 0 → odom still published (no motion).
        """
        self.publish_speed(0.0)

        self.publish_mocap(1.0, 0.0, 0.0)
        self.spin()

        assert self.received_odom is not None, \
            "Expected odom during frozen pose with vehicle stopped"
