import rclpy
import time

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from std_msgs.msg import Bool, Int8

# Import your FSM logic
from decision_unit.decision_core_fsm import DecisionUnit


# ---------------- Wrapper Node ----------------
class DecisionUnitWrapper(Node):
    def __init__(self):
        super().__init__('decision_unit_node')

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.vehicle_state_pub = self.create_publisher(
            Int8, '/vehicle_state', qos
        )

        self.booking_sub = self.create_subscription(
            Bool, '/booking_request', self.booking_cb, 10
        )
        self.goal_sub = self.create_subscription(
            Bool, '/goal_reached', self.goal_cb, 10
        )
        self.door_sub = self.create_subscription(
            Bool, '/door_open', self.door_cb, 10
        )

        self.fsm = DecisionUnit(self)

    def booking_cb(self, msg):
        self.fsm.booking_request = msg.data
        self.fsm.publish_state()

    def goal_cb(self, msg):
        self.fsm.goal_reached = msg.data
        self.fsm.publish_state()

    def door_cb(self, msg):
        self.fsm.door_open = msg.data
        self.fsm.publish_state()




# ---------------- Test Listener ----------------
class _TestListener(Node):
    def __init__(self):
        super().__init__('decision_unit_test_listener')

        self.state_received = False
        self.states = []

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.create_subscription(
            Int8, '/vehicle_state', self.state_cb, qos
        )

        self.booking_pub = self.create_publisher(Bool, '/booking_request', 10)
        self.goal_pub = self.create_publisher(Bool, '/goal_reached', 10)
        self.door_pub = self.create_publisher(Bool, '/door_open', 10)

    def state_cb(self, msg):
        self.state_received = True
        self.states.append(msg.data)


# ---------------- Test Case ----------------
def test_TC_Int_DecisionUnit():
    """
    Integration test for Decision Unit FSM.
    """

    rclpy.init()
    executor = SingleThreadedExecutor()

    decision_node = DecisionUnitWrapper()
    test_node = _TestListener()

    executor.add_node(decision_node)
    executor.add_node(test_node)

    # ---- FSM INPUT SEQUENCE ----
    test_node.booking_pub.publish(Bool(data=True))
    executor.spin_once(timeout_sec=0.2)

    test_node.goal_pub.publish(Bool(data=True))
    executor.spin_once(timeout_sec=0.2)

    test_node.door_pub.publish(Bool(data=False))
    executor.spin_once(timeout_sec=0.2)

    test_node.goal_pub.publish(Bool(data=True))
    executor.spin_once(timeout_sec=0.2)

    test_node.door_pub.publish(Bool(data=False))
    executor.spin_once(timeout_sec=0.2)

    test_node.goal_pub.publish(Bool(data=True))
    executor.spin_once(timeout_sec=0.5)

    assert test_node.state_received, \
        "FAILED: /vehicle_state was not published"

    print("PASSED: Decision Unit published vehicle_state")
    print("States:", test_node.states)

    decision_node.destroy_node()
    test_node.destroy_node()
    rclpy.shutdown()

