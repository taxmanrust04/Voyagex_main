# ========================================================
# INTEGRATION TEST — PERCEPTION FUSION
# ========================================================
import rclpy
import time
import threading
import numpy as np

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor

from sensor_msgs.msg import CameraInfo, Image
from geometry_msgs.msg import TransformStamped
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose

from unittest.mock import MagicMock

from vx_custom_msgs.msg import FusedObjects
from sensor_fusion_cpm.perception_fusion_node import PerceptionFusionNode



class TC_Int_PerceptionFusion(Node):
    def __init__(self):
        super().__init__('TC_Int_PerceptionFusion')

        self.fused_received = False

        self.create_subscription(
            FusedObjects,
            '/fused_objects_out',
            self.fused_cb,
            10
        )

    def fused_cb(self, msg):
        self.fused_received = True


def spin_for(node, duration=0.5):
    end = time.time() + duration
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)


def wait_for(condition, node, timeout=10.0):
    start = time.time()
    while time.time() - start < timeout:
        rclpy.spin_once(node, timeout_sec=0.05)
        if condition():
            return True
    return False


def test_TC_Int_PerceptionFusion():
    """
    Integration test for Perception Fusion.

    Expected:
    - fused_objects_out is published
    """

    rclpy.init()
    executor = SingleThreadedExecutor()

    fusion_node = PerceptionFusionNode()
    test_node = TC_Int_PerceptionFusion()

    executor.add_node(fusion_node)
    executor.add_node(test_node)

    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()

    # ---------------- Camera Info ----------------
    cam = CameraInfo()
    cam.k = [
        600.0, 0.0, 320.0,
        0.0, 600.0, 240.0,
        0.0, 0.0, 1.0
    ]
    fusion_node.camera_info_callback(cam)

    # ---------------- Depth Image ----------------
    depth = Image()
    depth.height = 480
    depth.width = 640
    depth.encoding = '16UC1'
    depth.step = 640 * 2
    depth.data = (np.ones((480, 640), dtype=np.uint16) * 2000).tobytes()

    fusion_node.depth_callback(depth)

    # ---------------- Fake TF ----------------
    fake_tf = TransformStamped()
    fake_tf.transform.rotation.w = 1.0
    fusion_node.tf_buffer.lookup_transform = MagicMock(return_value=fake_tf)

    # ---------------- Detection ----------------
    det_msg = Detection2DArray()

    det = Detection2D()
    det.bbox.center.position.x = 320.0
    det.bbox.center.position.y = 240.0
    det.bbox.size_x = 80.0
    det.bbox.size_y = 80.0

    hyp = ObjectHypothesisWithPose()
    hyp.hypothesis.class_id = '\x05'  # Car
    hyp.hypothesis.score = 0.9

    det.results = [hyp]
    det_msg.detections.append(det)

    fusion_node.detections_callback(det_msg)

    assert wait_for(lambda: test_node.fused_received, test_node), \
        "Expected Result FAILED: /fused_objects_out not published"

    print("Expected Result: PASSED (Perception Fusion published fused objects)")

    executor.shutdown()
    fusion_node.destroy_node()
    test_node.destroy_node()
    rclpy.shutdown()

