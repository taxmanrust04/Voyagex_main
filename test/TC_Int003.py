import pytest
import rclpy
import time
import threading
import math

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool


# ---------------- Test Node ----------------
class TC_Int_ObstacleDetector(Node):
    def __init__(self):
        super().__init__('TC_Int_ObstacleDetector')

        scan_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.stop_received = None

        # Output
        self.create_subscription(
            Bool,
            '/stop_obstacle',
            self.stop_cb,
            10
        )

        # Input
        self.scan_pub = self.create_publisher(
            LaserScan,
            '/scan',
            scan_qos
        )

    def stop_cb(self, msg):
        self.stop_received = msg.data


# ---------------- Helpers ----------------
def wait_for_condition(condition_fn, timeout=5.0, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


def make_obstacle_scan(distance=0.5):
    scan = LaserScan()
    scan.header.frame_id = "laser"
    scan.angle_min = -math.pi
    scan.angle_max = math.pi
    scan.angle_increment = math.radians(1.0)
    scan.range_min = 0.05
    scan.range_max = 10.0

    count = int((scan.angle_max - scan.angle_min) / scan.angle_increment)
    scan.ranges = [10.0] * count

    # Put obstacle in ROI (~ -120 deg)
    roi_index = int((math.radians(-120) - scan.angle_min) / scan.angle_increment)
    scan.ranges[roi_index] = distance

    return scan


# ---------------- Fixture ----------------
@pytest.fixture(scope="module")
def test_node():
    rclpy.init()

    node = TC_Int_ObstacleDetector()
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
def test_TC_Int_ObstacleDetector(test_node):
    """
    Integration test for obstacle detector.

    Expected:
    - obstacle in ROI
    - stop_obstacle == True
    """

    test_node.scan_pub.publish(make_obstacle_scan(distance=0.5))

    assert wait_for_condition(lambda: test_node.stop_received is True), \
        "Expected Result FAILED: /stop_obstacle not TRUE"

    print("Expected Result: PASSED (Obstacle detected)")
