#!/usr/bin/env python3

import rclpy
import asyncio
from typing import List
from dual_amm.dual_amm import DUAL_AMM_Node
import time 



class LeftArmMoveNode(DUAL_AMM_Node):
    def __init__(self):
        super().__init__()
        self.get_logger().info('✅ 左手移動節點初始化完成')
        self.hand_shake_pin = 0  # 假設使用 IO 0 作為 Handshake Pin
        self.action_triggered = False
        # 建立 Timer，使用父類別的 ReentrantCallbackGroup (cb_re) 以支援非同步執行
        self.timer = self.create_timer(3.0, self.execute_move, callback_group=self.cb_re)
        self.get_logger().info('🚀 準備就緒，3 秒後開始移動...')

    async def _pick_at_pose_left(self, object_pose: List[float], opening: float) -> tuple:
        """在指定位置抓取物體"""
        try:
            # ================= [修改] 加入 Wait 0 確保訊號乾淨 =================
            await self.robot_controller_left.set_io_async(0, 1, self.hand_shake_pin, 0.0)
            await self.robot_controller_left.wait_for_io_async(self.hand_shake_pin, 0)
            # await self.robot_controller_left.wait_for_ioo
            # =================================================================

            # # 計算預抓取位置
            # pre_grasp_pose = self._calculate_pre_approach_pose(
            #     object_pose, self.pick_place_config.pre_grasp_offset
            # )

            # 移動到目標位置
            self.get_logger().info(f"🎯 移動到目標抓取位置: {object_pose}")
            await self.robot_controller_left.move_to_pose_async(object_pose)

            # 發送到達訊號
            await self.robot_controller_left.set_io_async(0, 1, self.hand_shake_pin, 1.0)
            self.get_logger().info("👀 等待到達訊號...")
            await self.robot_controller_left.wait_for_io_async(self.hand_shake_pin, 1,15)
            self.get_logger().info("✅ 已到達目標抓取位置")

            # 關閉夾爪e
            self.get_logger().info(f"🔒 關閉夾爪（opening={opening}）...")
            await self.gripper_controller_left.set_gripper_state_async(
                position=int(opening * 255 + 0.5), wait_time=2
            )
            self.get_logger().info("✅ 夾爪已關閉")

            # ================= [修改] 上拉動作加入完整 Handshake =================
            # 1. 先清零並等待確認
            await self.robot_controller_left.set_io_async(0, 1, self.hand_shake_pin, 0.0)
            await self.robot_controller_left.wait_for_io_async(self.hand_shake_pin, 0)

            # 3. 發送完成訊號
            await self.robot_controller_left.set_io_async(0, 1, self.hand_shake_pin, 1.0)

            # 4. 等待完成訊號 (這會卡住直到機器人真的回到上方)
            self.get_logger().info("👀 等待回到預抓取位置...")
            await self.robot_controller_left.wait_for_io_async(self.hand_shake_pin, 1)
            self.get_logger().info("✅ 已返回預抓取位置")

            # 5. 最後清零
            await self.robot_controller_left.set_io_async(0, 1, self.hand_shake_pin, 0.0)
            # ====================================================================

            # 獲取夾爪狀態
            self.get_logger().info("📊 獲取最終夾爪狀態...")
            status = await self.gripper_controller_left.get_gripper_status_async()
            self.get_logger().info(f"✅ 抓取完成，狀態: {status.result}")

            return status.ok, status.status_code
        
        

        except Exception as e:
            self.get_logger().error(f'抓取失敗: {e}')
            await self.robot_controller_left.move_to_home_async()
            raise

    async def _pick_at_pose_right(self, object_pose: List[float], opening: float) -> tuple:
        """在指定位置抓取物體"""
        try:
            # ================= [修改] 加入 Wait 0 確保訊號乾淨 =================
            await self.robot_controller_right.set_io_async(0, 1, self.hand_shake_pin, 0.0)
            await self.robot_controller_right.wait_for_io_async(self.hand_shake_pin, 0)

            # 移動到目標位置
            self.get_logger().info(f"🎯 移動到目標抓取位置: {object_pose}")
            await self.robot_controller_right.move_to_pose_async(object_pose)

            # 發送到達訊號
            await self.robot_controller_right.set_io_async(0, 1, self.hand_shake_pin, 1.0)
            self.get_logger().info("👀 等待到達訊號...")
            await self.robot_controller_right.wait_for_io_async(self.hand_shake_pin, 1,15)
            self.get_logger().info("✅ 已到達目標抓取位置")

            # 關閉夾爪e
            self.get_logger().info(f"🔒 關閉夾爪（opening={opening}）...")
            await self.gripper_controller_right.set_gripper_state_async(
                position=int(opening * 255 + 0.5), wait_time=2
            )
            self.get_logger().info("✅ 夾爪已關閉")

            # ================= [修改] 上拉動作加入完整 Handshake =================
            # 1. 先清零並等待確認
            await self.robot_controller_right.set_io_async(0, 1, self.hand_shake_pin, 0.0)
            await self.robot_controller_right.wait_for_io_async(self.hand_shake_pin, 0)

            # # 2. 回到預抓取位置
            # self.get_logger().info("🔙 返回預抓取位置...")
            # await self.robot_controller_right.move_to_pose_async(pre_grasp_pose, MotionType.LINE_T)

            # 3. 發送完成訊號
            await self.robot_controller_right.set_io_async(0, 1, self.hand_shake_pin, 1.0)

            # 4. 等待完成訊號 (這會卡住直到機器人真的回到上方)
            self.get_logger().info("👀 等待回到預抓取位置...")
            await self.robot_controller_right.wait_for_io_async(self.hand_shake_pin, 1)
            self.get_logger().info("✅ 已返回預抓取位置")

            # 5. 最後清零
            await self.robot_controller_right.set_io_async(0, 1, self.hand_shake_pin, 0.0)
            # ====================================================================

            # 獲取夾爪狀態
            self.get_logger().info("📊 獲取最終夾爪狀態...")
            status = await self.gripper_controller_right.get_gripper_status_async()
            self.get_logger().info(f"✅ 抓取完成，狀態: {status.result}")

            return status.ok, status.status_code
        
    
 
        except Exception as e:
            self.get_logger().error(f'抓取失敗: {e}')
            await self.robot_controller_left.move_to_home_async()
            raise

    async def execute_move(self):
        """執行純手臂移動序列"""
        if self.action_triggered:
            return
        self.action_triggered = True
        self.timer.cancel() # 確保只觸發一次
        

        try:
            self.get_logger().info('🚀 開始執行移動序列...')
            await self.gripper_controller_left.open_gripper_async()
            await self.gripper_controller_right.open_gripper_async()

            # await self.gripper_controller_left.close_gripper_async()
            
            #right_home
            # [0.14722264099121093, -0.004881676435470581, 0.6757967529296875, -3.141507432434911, -0.036347912788972696, 2.9862688430169926]
            #left home
            # [0.14384927368164063, 0.012112136840820313, 0.6726647338867188, 3.130990875606297, 0.035230579392440745, 0.24306576394039373]


            # home
            p2 = [0.13936578369140626, 0.031412448883056644, 0.6671008911132813, 3.118365361510449, 0.0353893454053015, 0.17596627178762722]
            await self._pick_at_pose_left(p2, 0.0)

            # old p1 = [0.14722264099121093, -0.004881676435470581, 0.6757967529296875, -3.141507432434911, -0.036347912788972696, 2.9862688430169926]
            p1 = [-0.10237763214111328, 0.21554049682617188, 0.6445255126953126, 3.110098110538516, -0.024431602652602347, 2.873694626894362]
            await self._pick_at_pose_right(p1, 0.0)
            
            
            ### photo posi and pick cup          
            p2 = [0.24141854858398437, -0.3884188842773438, 0.5917418212890625, 3.109182782071856, 0.005127249328229102, 0.16350226176713606]
            await self._pick_at_pose_left(p2, 0.0)

            p2 = [0.2291017303466797, -0.32033749389648436, 0.22987982177734376, -3.025712655606047, -0.009921558787414365, 0.15174720187358082]
            await self._pick_at_pose_left(p2, 0.0)

            p2 = [0.23510298156738282, -0.3690068359375, 0.08867085266113281, 2.25889856292739, -0.040068968849004676, 0.16411532145007232]
            await self._pick_at_pose_left(p2, 0.0)
            
            p2 = [0.2455984344482422, -0.4138735046386719, 0.08619603729248047, 2.235474729559598, -0.0417964657407874, 0.165096563153712]
            await self._pick_at_pose_left(p2, 0.3)

            p2 = [0.2507308502197266, -0.4217689208984375, 0.45924456787109375, 2.121994106559959, 0.019442594791637624, 0.24379775041075882]
            await self._pick_at_pose_left(p2, 0.3)  
            
            p2 = [0.057706130981445315, -0.4371502380371094, 0.5844339599609375, 1.86376761567926, 0.03382408287758044, -0.6627673183664606]
            await self._pick_at_pose_left(p2, 0.3)  


            ### pick drink

            p1 = [0.3454256591796875, 0.2816202697753906, 0.8514802856445313, -0.4758597155563518, -1.552808138370011, -1.095782065016104]
            await self._pick_at_pose_right(p1, 0.0)
                    
            p1 = [0.4778376770019531, 0.2774620361328125, 0.18343806457519532, 2.731418974082405, -1.4036994799911828, 2.0628600792933494]
            await self._pick_at_pose_right(p1, 0.0)

            p1 = [0.44987548828125, 0.33533203125, 0.17877297973632814, 2.052581609066188, -1.4918498457566967, 2.7959308556962665]
            await self._pick_at_pose_right(p1, 0.8)

            p1 = [0.44987548828125, 0.33533203125, 0.77877297973632814, 2.052581609066188, -1.4918498457566967, 2.7959308556962665]
            await self._pick_at_pose_right(p1, 0.8)

            p1 = [-0.05195105361938477, 0.42368914794921875, 0.6678565673828125, 2.1430358754907295, -1.4631251233971565, 2.410240148722195]
            await self._pick_at_pose_right(p1, 0.8) 

            p1 = [-0.09121429443359375, 0.45012701416015627, 0.7120404663085937, 1.2995363255393497, -0.6527582934625885, -2.780353493848175]
            await self._pick_at_pose_right(p1, 0.8) 

            p1 = [-0.05195105361938477, 0.42368914794921875, 0.6678565673828125, 2.1430358754907295, -1.4631251233971565, 2.410240148722195]
            await self._pick_at_pose_right(p1, 0.8) 

            p1 = [0.44987548828125, 0.33533203125, 0.77877297973632814, 2.052581609066188, -1.4918498457566967, 2.7959308556962665]
            await self._pick_at_pose_right(p1, 0.8)
            
            #give drink
            p2 = [0.2893251647949219, -0.5314427490234375, 0.3631981201171875, 1.6769398078333126, -0.05469404670912187, 0.202720587835645]
            await self._pick_at_pose_left(p2, 0.0)

            self.get_logger().info('🎉 所有移動任務圓滿達成！')

        except Exception as e:
            self.get_logger().error(f'❌ 移動執行失敗: {e}')

def main(args=None):
    rclpy.init(args=args)
    
    # 建立節點實例
    node = LeftArmMoveNode()
    
    # 使用 MultiThreadedExecutor 以支援非同步 await 運作
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('🛑 使用者手動停止')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()