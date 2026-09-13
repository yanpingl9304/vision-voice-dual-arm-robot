#!/usr/bin/env python3
"""Lightweight RQT chat plugin for the drink robot HMI.

This plugin has NO dependency on conda packages (no pyaudio, YOLO, torch, etc.).
It provides a simple Qt GUI that:
  - Publishes typed text commands to /user_command (std_msgs/String)
  - Sends drink orders via /drinks_robot/submit_order service
  - Subscribes /robot_status (std_msgs/String) to display robot state
"""

import threading

from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rqt_gui_py.plugin import Plugin
from std_msgs.msg import String
from std_srvs.srv import Trigger

from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from drinks_robot_interface.action import ExecuteDrinkTask  # pyright: ignore[reportMissingImports]


class _UISignals(QObject):
    log_msg = pyqtSignal(str, str)
    update_status = pyqtSignal(str, str)
    set_cancel_enabled = pyqtSignal(bool)


class ChatInterfacePlugin(Plugin):
    def __init__(self, context):
        super().__init__(context)
        self.setObjectName('ChatInterfacePlugin')
        self._node = context.node

        self._signals = _UISignals()
        self._signals.log_msg.connect(self._on_log_msg)
        self._signals.update_status.connect(self._on_update_status)

        self._widget = QWidget()
        self._setup_ui()
        context.add_widget(self._widget)

        self._signals.set_cancel_enabled.connect(self._cancel_btn.setEnabled)

        self._cmd_pub = self._node.create_publisher(String, '/user_command', 10)
        self._drink_cmd_sub = self._node.create_subscription(
            String, '/drink_command', self._drink_command_callback, 10
        )
        self._status_sub = self._node.create_subscription(
            String, '/robot_status', self._status_callback, 10
        )
        self._drink_client = ActionClient(self._node, ExecuteDrinkTask, '/drinks_robot/execute_task')
        self._clients = {
            'water': self._node.create_client(Trigger, '/drinks_robot/reset_water'),
            'coffee': self._node.create_client(Trigger, '/drinks_robot/reset_coffee'),
            'tea': self._node.create_client(Trigger, '/drinks_robot/reset_tea')
        }

        self._current_goal_handle = None

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        from PyQt5.QtGui import QFont, QFontDatabase

        root = QVBoxLayout(self._widget)

        # Try to find a working CJK font, fallback to monospace if not available
        default_font = QFont()
        cjk_fonts = ['Noto Sans CJK JP', 'AR PL UMing CN', 'WenQuanYi Zen Hei', 'DejaVu Sans', 'Liberation Sans']

        for font_name in cjk_fonts:
            default_font.setFamily(font_name)
            if QFontDatabase().families().__contains__(font_name) or font_name in QFontDatabase().families():
                break
        else:
            # Fallback: let Qt choose
            default_font = QFont('Monospace')

        default_font.setPointSize(10)

        # Status bar
        status_row = QHBoxLayout()
        self._status_light = QLabel()
        self._status_light.setFixedSize(20, 20)
        self._status_light.setStyleSheet('background-color: grey; border-radius: 10px;')
        self._status_label = QLabel('Waiting for connection...')
        self._status_label.setFont(default_font)
        self._status_label.setStyleSheet('font-size: 16px; font-weight: bold;')
        status_row.addWidget(self._status_light)
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        root.addLayout(status_row)

        # Chat log
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setFont(default_font)
        self._chat_display.setStyleSheet('font-size: 12px;')
        root.addWidget(self._chat_display)

        # Text input row
        input_row = QHBoxLayout()
        self._input_box = QLineEdit()
        self._input_box.setPlaceholderText('Type command...')
        self._input_box.setFont(default_font)
        self._input_box.setStyleSheet('font-size: 12px; padding: 6px;')
        self._input_box.returnPressed.connect(self._send_command)
        send_btn = QPushButton('Send')
        send_btn.setFont(default_font)
        send_btn.setStyleSheet('font-size: 12px; padding: 6px 16px;')
        send_btn.clicked.connect(self._send_command)
        input_row.addWidget(self._input_box)
        input_row.addWidget(send_btn)
        root.addLayout(input_row)

        # Drink order buttons
        drink_row = QHBoxLayout()
        drink_label = QLabel('Order Drink:')
        drink_label.setFont(default_font)
        drink_label.setStyleSheet('font-size: 12px;')
        drink_row.addWidget(drink_label)
        for drink_type, label in [('water', 'Water'), ('coffee', 'Coffee'), ('tea', 'Tea')]:
            btn = QPushButton(label)
            btn.setFont(default_font)
            btn.setStyleSheet(
                'font-size: 12px; padding: 8px 16px; '
                'background-color: #4caf50; color: white; border-radius: 4px;'
            )
            btn.clicked.connect(lambda checked, d=drink_type: self._order_drink(d))
            drink_row.addWidget(btn)
        drink_row.addStretch()

        # Cancel button
        self._cancel_btn = QPushButton('Cancel Order')
        self._cancel_btn.setFont(default_font)
        self._cancel_btn.setStyleSheet(
            'font-size: 12px; padding: 8px 16px; '
            'background-color: #f44336; color: white; border-radius: 4px;'
        )
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_order)
        drink_row.addWidget(self._cancel_btn)
        root.addLayout(drink_row)

        # Reset button
        reset_row = QHBoxLayout()
        reset_label = QLabel('補水重設:')
        reset_label.setFont(default_font)
        reset_label.setStyleSheet('font-size: 12px; font-weight: bold; margin-top: 5px;')
        reset_row.addWidget(reset_label)

        for d_type, d_label in [('water', '補滿水'), ('coffee', '補滿咖啡'), ('tea', '補滿茶')]:
            r_btn = QPushButton(d_label)
            r_btn.setFont(default_font)
            r_btn.setStyleSheet(
                'font-size: 11px; padding: 6px 12px; font-weight: bold; '
                'background-color: #00bcd4; color: white; border-radius: 4px;'
            )
            r_btn.clicked.connect(lambda checked, dt=d_type: self._reset_specific_action(dt))
            reset_row.addWidget(r_btn)

        reset_row.addStretch()
        root.addLayout(reset_row)

    # ------------------------------------------------------------------
    # ROS callbacks
    # ------------------------------------------------------------------

    def _status_callback(self, msg: String):
        try:
            import json
            data = json.loads(msg.data)
            state = data.get("state", "unknown").upper()
            drink = data.get("current_drink", "None")
            self._signals.update_status.emit(f"[{state}] Current Task: {drink}", 'green')
        except Exception:
            self._signals.update_status.emit(msg.data, 'green')

    def _drink_command_callback(self, msg: String):
        self._signals.log_msg.emit('Robot', f'收到飲料命令: {msg.data}')
        self._order_drink(drink_type=msg.data.strip().lower())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _reset_specific_action(self, drink_type: str):
        def _call_service():
            client = self._clients.get(drink_type)
            if client is None or not client.wait_for_service(timeout_sec=2.0):
                self._signals.log_msg.emit('System', f'無法連接到 {drink_type} 的重設服務。')
                return
            req = Trigger.Request()
            future = client.call_async(req)
            future.add_done_callback(lambda f, dt=drink_type: self._on_reset_specific_response(f, dt))
            
        threading.Thread(target=_call_service, daemon=True).start()

    def _on_reset_specific_response(self, future, drink_type: str):
        try:
            response = future.result()
            if response.success:
                self._signals.log_msg.emit('System', f'【{drink_type}】水壺已補滿，該杯數已手動歸零！')
            else:
                self._signals.log_msg.emit('System', f'{drink_type} 杯數重設失敗: {response.message}')
        except Exception as e:
            self._signals.log_msg.emit('System', f'呼叫重設服務錯誤: {e}')

    def _send_command(self):
        text = self._input_box.text().strip()
        if not text:
            return
        self._input_box.clear()
        msg = String()
        msg.data = text
        self._cmd_pub.publish(msg)
        self._signals.log_msg.emit('User', text)

    def _order_drink(self, drink_type: str):
        def _send():
            if not self._drink_client.wait_for_server(timeout_sec=2.0):
                self._signals.log_msg.emit('System', '動作伺服器不可用，請確認機器人節點已啟動。')
                return
            goal = ExecuteDrinkTask.Goal()
            goal.drink_type = drink_type
            future = self._drink_client.send_goal_async(goal, feedback_callback=self._on_drink_feedback)
            future.add_done_callback(self._on_goal_response)

        threading.Thread(target=_send, daemon=True).start()
        self._signals.log_msg.emit('User', f'點了{drink_type}')

    def _on_goal_response(self, future):
        """Handle goal acceptance/rejection."""
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self._signals.log_msg.emit('System', '目標被拒絕 (機器人忙碌或飲料不支援)。')
                return
            self._current_goal_handle = goal_handle
            self._signals.set_cancel_enabled.emit(True)
            self._signals.log_msg.emit('System', '目標已接受，任務執行中...')
            goal_handle.get_result_async().add_done_callback(self._on_drink_order_result)
        except Exception as e:
            self._signals.log_msg.emit('System', f'目標送出錯誤: {e}')

    def _on_drink_feedback(self, feedback_msg):
        """Handle feedback from the drink robot action."""
        try:
            fb = feedback_msg.feedback
            desc = f'[{fb.state}] {fb.progress*100:.0f}% — {fb.description}'
            self._signals.update_status.emit(desc, 'orange')
            self._signals.log_msg.emit('Robot', desc)
        except Exception as e:
            self._signals.log_msg.emit('System', f'回饋處理錯誤: {e}')

    def _on_drink_order_result(self, future):
        """Handle final result from the drink task action."""
        self._current_goal_handle = None
        self._signals.set_cancel_enabled.emit(False)
        try:
            result_response = future.result()
            res = result_response.result
            if result_response.status == GoalStatus.STATUS_SUCCEEDED:
                self._signals.log_msg.emit('System', f'點飲料成功: {res.message}')
                self._signals.update_status.emit('完成', 'green')
            elif result_response.status == GoalStatus.STATUS_CANCELED:
                self._signals.log_msg.emit('System', '訂單已取消。')
                self._signals.update_status.emit('已取消', 'grey')
            else:
                self._signals.log_msg.emit('System', f'點飲料失敗: {res.message}')
                self._signals.update_status.emit('失敗', 'red')
        except Exception as e:
            self._signals.log_msg.emit('System', f'結果讀取錯誤: {e}')

    def _cancel_order(self):
        """Cancel the current order."""
        if self._current_goal_handle is None:
            return
        self._signals.log_msg.emit('System', '送出取消請求...')
        cancel_future = self._current_goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(
            lambda f: self._signals.log_msg.emit('System', '取消請求已確認。')
        )

    # ------------------------------------------------------------------
    # Thread-safe UI updates (must run on Qt main thread)
    # ------------------------------------------------------------------

    def _on_log_msg(self, sender: str, msg: str):
        # Use HTML with explicit font specification and Unicode support
        html = f'<div style="font-family: monospace; font-size: 12px;"><b>[{sender}]</b> {msg}</div>'
        self._chat_display.append(html)
        self._chat_display.verticalScrollBar().setValue(
            self._chat_display.verticalScrollBar().maximum()
        )

    def _on_update_status(self, text: str, color: str):
        self._status_label.setText(text)
        self._status_light.setStyleSheet(
            f'background-color: {color}; border-radius: 10px;'
        )

    def shutdown_plugin(self):
        self._drink_client.destroy()

    def save_settings(self, plugin_settings, instance_settings):
        pass

    def restore_settings(self, plugin_settings, instance_settings):
        pass