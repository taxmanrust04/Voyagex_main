import pytest
import rclpy
import time
import threading
import math

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
from vx_custom_msgs.msg import TrafficSignalState


# ---------------- Test Node ----------------
class TC_Int_TrafficSignalDecision(Node):
    def __init__(self):
        super().__init__('TC_Int_TrafficSignalDecision')

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST
        )

        self.stop_received = None

        # Subscriber (output of module)
        self.create_subscription(Bool, '/stop_signal', self.stop_cb, qos)

        # Publishers (inputs to module)
        self.odom_pub = self.create_publisher(Odometry, '/odom', qos)
        self.signal_pub = self.create_publisher(
            TrafficSignalState, '/traffic_signal_state', qos
        )

    def stop_cb(self, msg):
        self.stop_received = msg.data


# ---------------- Helpers ----------------
def wait_for_condition(condition_fn, timeout=10.0, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


def make_test_odom(x, y, heading_deg):
    odom = Odometry()
    odom.pose.pose.position.x = x
    odom.pose.pose.position.y = y

    yaw = math.radians(heading_deg)
    odom.pose.pose.orientation.z = math.sin(yaw / 2.0)
    odom.pose.pose.orientation.w = math.cos(yaw / 2.0)

    return odom


def make_red_signal(intersection_id, signal_group_id):
    msg = TrafficSignalState()
    msg.intersection_id = intersection_id
    msg.signal_group_id = signal_group_id
    msg.event_state = 3  # RED
    return msg


# ---------------- Pytest Fixture ----------------
@pytest.fixture(scope="module")
def test_node():
    rclpy.init()

    node = TC_Int_TrafficSignalDecision()
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()

    yield node

    executor.shutdown()
    thread.join(timeout=1.0)
    node.destroy_node()
    rclpy.shutdown()


# ---------------- Test Case ----------------
def test_TC_Int_TrafficSignalDecision(test_node):
    """
    Integration test for traffic signal decision.

    Expected:
    - Vehicle inside intersection zone
    - RED traffic signal received
    - stop_signal == True
    """

    # Intersection 1, signal group 1 bounding box:
    # (4.0, 2.0) to (5.5, 3.0), heading 135–225 deg
    test_node.odom_pub.publish(make_test_odom(
        x=4.5,
        y=2.5,
        heading_deg=180.0
    ))

    # Publish RED traffic signal
    test_node.signal_pub.publish(make_red_signal(
        intersection_id=1,
        signal_group_id=1
    ))

    assert wait_for_condition(lambda: test_node.stop_received is True), \
        "Expected Result FAILED: stop_signal was not TRUE for RED light"

    print("Expected Result: PASSED (STOP on RED)")
