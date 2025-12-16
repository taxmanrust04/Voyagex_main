import pytest
import rclpy
import time
import threading

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from nav_msgs.msg import Odometry, Path
from std_msgs.msg import Int8
from vx_custom_msgs.msg import GoalPoint

GO_TO_PICKUP = 1
GO_TO_DROPOFF = 3

# ---------------- Test Node ----------------
class TC_Int_PathPlanner(Node):
    def __init__(self):
        super().__init__('tc_int_path_planner')

        qos = QoSProfile(
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST
        )

        self.odom_received = False
        self.goal_received = False
        self.state_received = False
        self.path_received = False

        self.last_vehicle_state = None
        self.path_after_state = None

        self.create_subscription(Odometry, '/odom', self.odom_cb, qos)
        self.create_subscription(GoalPoint, '/pickup_drop_goal', self.goal_cb, qos)
        self.create_subscription(Int8, '/vehicle_state', self.state_cb, qos)
        self.create_subscription(Path, '/path_data', self.path_cb, qos)

    def odom_cb(self, msg):
        self.odom_received = True

    def goal_cb(self, msg):
        self.goal_received = True

    def state_cb(self, msg):
        self.state_received = True
        self.last_vehicle_state = msg.data

    def path_cb(self, msg):
        if len(msg.poses) > 0:
            self.path_received = True
            self.path_after_state = self.last_vehicle_state


# ---------------- Helper ----------------
def wait_for_condition(condition_fn, timeout=20.0, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


# ---------------- Pytest Fixture ----------------
@pytest.fixture(scope="module")
def test_node():
    rclpy.init()

    node = TC_Int_PathPlanner()
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()

    yield node

    executor.shutdown()
    thread.join(timeout=1.0)
    node.destroy_node()
    rclpy.shutdown()


# ---------------- Test Case: Pickup ----------------
def test_path_to_pickup(test_node):
    assert wait_for_condition(lambda: test_node.odom_received), \
        "FAILED: /odom not received"

    assert wait_for_condition(lambda: test_node.goal_received), \
        "FAILED: /pickup_drop_goal not received"

    assert wait_for_condition(lambda: test_node.state_received), \
        "FAILED: /vehicle_state not received"

    assert wait_for_condition(
        lambda: test_node.path_received and test_node.path_after_state == GO_TO_PICKUP
    ), "FAILED: Path to PICKUP not published"


# ---------------- Test Case: Dropoff ----------------
def test_path_to_dropoff(test_node):
    test_node.path_received = False
    test_node.path_after_state = None

    assert wait_for_condition(
        lambda: test_node.path_received and test_node.path_after_state == GO_TO_DROPOFF
    ), "FAILED: Path to DROPOFF not published"
