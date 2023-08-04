from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, cast, Tuple
from typing_extensions import Self

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from viam.components.arm import Arm, Pose, JointPositions, KinematicsFileFormat
from viam.components.board import Board
from viam.logging import getLogger

from .controller import YahboomServoController

import time
import ikpy.chain
import numpy as np

# adapted from https://github.com/YahboomTechnology/dofbot-Pi/tree/master/11.Communication%20protocol%20and%20Python%20library/1.Install%20Python%20module

LOGGER = getLogger(__name__)


class yahboom(Arm, Reconfigurable):
    MODEL: ClassVar[Model] = Model(ModelFamily("viamlabs", "arm"), "yahboom")
    
    joint_positions = None
    my_chain = ikpy.chain.Chain.from_urdf_file("/home/nataliehuang/yahboom/src/dofbot.urdf")

    # Constructor
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        my_class.controller = YahboomServoController()
        return my_class

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ComponentConfig):
        return

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        return

    """ Implement the methods the Viam RDK defines for the Arm API (rdk:components:arm) """

    
    async def get_end_position(
        self,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Pose:
        """
        Get the current position of the end of the arm expressed as a Pose.

        Returns:
            Pose: The location and orientation of the arm described as a Pose.
        """
        return Pose(0, 0, 0, 0, 0, 0)

    
    async def move_to_position(
        self,
        pose: Pose,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        """
        Move the end of the arm to the Pose specified in ``pose``.

        Args:
            pose (Pose): The destination Pose for the arm.
        """
        pass

    
    async def move_to_joint_positions(
        self,
        positions: JointPositions,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        """
        Move each joint on the arm to the corresponding angle specified in ``positions``.

        Args:
            positions (JointPositions): The destination ``JointPositions`` for the arm.
        """
        LOGGER.info(f'moving to positions {positions.values}')
        max_time = 1000
        for i, val in enumerate(positions.values):
            # approx 10 deg per second
            max_time = max(max_time, (abs(val - self.joint_positions[i])*1000//10))

        gripper_pos = await self.get_gripper_position()
        all_positions = list(positions.values) + [gripper_pos]
        try:
            await self.controller.write_all_servos(all_positions, int(max_time))
        except Exception as e:
            LOGGER.error(f'error writing positions {all_positions.values} to servos {e}')
    
    async def get_joint_positions(
        self,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> JointPositions:
        """
        Get the JointPositions representing the current position of the arm.

        Returns:
            JointPositions: The current JointPositions for the arm. [base spin, joint 1, 2, 3, top claw spin]
        """
        values = []
        for id in range(1, 6):
            val = await self.controller.read_servo(id)
            values.append(val)
            time.sleep(0.01)
        # LOGGER.info(f"joint values log: {values}")
        self.joint_positions = values
        return JointPositions(values=values)

    async def get_gripper_position(self):
        return await self.controller.read_servo(6)

    async def stop(
        self,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        """
        Stop all motion of the arm. It is assumed that the arm stops immediately.
        """
        pass

    
    async def is_moving(self) -> bool:
        """
        Get if the arm is currently moving.

        Returns:
            bool: Whether the arm is moving.
        """
        pass

    
    async def get_kinematics(self, *, timeout: Optional[float] = None) -> Tuple[KinematicsFileFormat.ValueType, bytes]:
        """
        Get the kinematics information associated with the arm.

        Returns:
            Tuple[KinematicsFileFormat.ValueType, bytes]:
                - KinematicsFileFormat.ValueType:
                  The format of the file, either in URDF format or Viam's kinematic parameter format (spatial vector algebra).

                - bytes: The byte contents of the file.
        """
        f = open("/home/nataliehuang/yahboom/src/dofbot.json", "rb")

        data = f.read()
        f.close()
        return (KinematicsFileFormat.KINEMATICS_FILE_FORMAT_SVA, data)