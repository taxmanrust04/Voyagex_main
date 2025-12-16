import pytest
import rclpy
import time
import threading

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from etsi_its_mapem_ts_msgs.msg import MAPEM
from etsi_its_spatem_ts_msgs.msg import SPATEM
from vx_custom_msgs.msg import TrafficSignalState


# ---------------- Test Node ----------------
class TC_Int_V2XDecoder(Node):
    def __init__(self):
        super().__init__('TC_Int_V2XDecoder')

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST
        )

        self.signal_received = False

        # Output subscriber
        self.create_subscription(
            TrafficSignalState,
            '/traffic_signal_state',
            self.signal_cb,
            qos
        )

        # Input publishers
        self.mapem_pub = self.create_publisher(MAPEM, '/mapem', qos)
        self.spatem_pub = self.create_publisher(SPATEM, '/spat', qos)

    def signal_cb(self, msg):
        self.signal_received = True


# ---------------- Helpers ----------------
def wait_for_condition(condition_fn, timeout=10.0, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


def make_minimal_mapem():
    return MAPEM()   # minimal valid message (structure exists)


def make_minimal_spatem():
    return SPATEM()  # minimal valid message


# ---------------- Fixture ----------------
@pytest.fixture(scope="module")
def test_node():
    rclpy.init()

    node = TC_Int_V2XDecoder()
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
def test_TC_Int_V2XDecoder(test_node):
    """
    Integration test for V2X decoder.

    Expected:
    - MAPEM received
    - SPATEM received
    - traffic_signal_state published
    """

    test_node.mapem_pub.publish(make_minimal_mapem())
    test_node.spatem_pub.publish(make_minimal_spatem())

    assert wait_for_condition(lambda: test_node.signal_received), \
        "Expected Result FAILED: No /traffic_signal_state published"

    print("Expected Result: PASSED (V2X decoded)")
