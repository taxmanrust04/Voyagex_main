import pytest
import rclpy
import time
import threading

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import PoseStamped
from ackermann_msgs.msg import AckermannDrive
from std_msgs.msg import Bool
from vx_custom_msgs.msg import ETAAndDistance


# ---------------- Test Node ----------------
class TC_Int_MotionExecutor(Node):
    def __init__(self):
        super().__init__('TC_Int_MotionExecutor')

        qos = QoSProfile(
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST
        )

        # Flags
        self.path_received = False
        self.odom_received = False
        self.cmd_received = False
        self.eta_received = False

        # Subscribers (outputs of MotionExecutor)
        self.create_subscription(AckermannDrive, '/ackermann_drive', self.cmd_cb, qos)
        self.create_subscription(ETAAndDistance, '/eta_info', self.eta_cb, qos)

        # Publishers (inputs to MotionExecutor)
        self.path_pub = self.create_publisher(Path, '/path_data', qos)
        self.odom_pub = self.create_publisher(Odometry, '/odom', qos)
        self.stop_pub = self.create_publisher(Bool, '/stop_signal', qos)
        self.stop_obs_pub = self.create_publisher(Bool, '/stop_obstacle', qos)

    def cmd_cb(self, msg):
        self.cmd_received = True

    def eta_cb(self, msg):
        self.eta_received = True


# ---------------- Helpers ----------------
def wait_for_condition(condition_fn, timeout=10.0, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


def make_test_path():
    path = Path()
    path.header.frame_id = "map"

    for x in [0.0, 1.0, 2.0, 3.0]:
        ps = PoseStamped()
        ps.pose.position.x = x
        ps.pose.position.y = 0.0
        ps.pose.orientation.w = 1.0
        path.poses.append(ps)

    return path


def make_test_odom(x=0.0, y=0.0, yaw=0.0):
    odom = Odometry()
    odom.pose.pose.position.x = x
    odom.pose.pose.position.y = y
    odom.pose.pose.orientation.z = 0.0
    odom.pose.pose.orientation.w = 1.0
    return odom


# ---------------- Pytest Fixture ----------------
@pytest.fixture(scope="module")
def test_node():
    rclpy.init()

    node = TC_Int_MotionExecutor()
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
def test_TC_Int_MotionExecutor(test_node):
    """
    Integration test for MotionExecutor.

    Expected:
    - path is consumed
    - odom is consumed
    - ackermann command is published
    - ETA is published
    """

    # Ensure vehicle is not stopped
    test_node.stop_pub.publish(Bool(data=False))
    test_node.stop_obs_pub.publish(Bool(data=False))

    # Publish inputs
    test_node.path_pub.publish(make_test_path())
    test_node.odom_pub.publish(make_test_odom())

    assert wait_for_condition(lambda: test_node.cmd_received), \
        "Expected Result 1 FAILED: No /ackermann_drive published"
    print("Expected Result 1: PASSED")

    assert wait_for_condition(lambda: test_node.eta_received), \
        "Expected Result 2 FAILED: No /eta_info published"
    print("Expected Result 2: PASSED")
