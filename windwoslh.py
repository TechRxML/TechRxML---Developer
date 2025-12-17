import sys
import os
import ctypes
import re
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFont, QIcon
from PyQt5.QtCore import Qt, QRectF, QRect, QPropertyAnimation, QEasingCurve, QTimer, QPoint


class NotchWindow(QWidget):
	def __init__(self, click_through=False):
		super().__init__()

		app = QApplication.instance()
		screen = app.primaryScreen()
		geom = screen.geometry()
		sw = geom.width()
		sh = geom.height()

		# Notch geometry (更接近 MacBook 风格：顶部平直、底部圆角)
		# 使用更小的宽度比例以避免过大
		notch_w = min(int(sw * 0.12), 420)
		notch_h = max(int(sh * 0.035), 36)
		radius = int(notch_h * 0.45)

		x = (sw - notch_w) // 2
		y = 0

		self.setGeometry(x, y, notch_w, notch_h)
		self.setWindowFlags(
			Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
		)
		self.setAttribute(Qt.WA_TranslucentBackground)

		self._bg_color = QColor(0, 0, 0)
		self._radius = radius
		self._click_through = click_through

		# keep base geometry for restore
		self._base_rect = self.geometry()
		self._expanded_rect = QRect(x - 150, y, notch_w + 300, notch_h)  # 扩张后的区域

		# hover animation
		self._anim = QPropertyAnimation(self, b"geometry")
		self._anim.setEasingCurve(QEasingCurve.OutCubic)
		self._anim.setDuration(200)

		# 中转站功能相关
		self._is_expanded = False
		self._is_animating = False
		self._show_text = False  # 控制文字是否显示
		self._click_count = 0
		self._click_timer = QTimer()
		self._click_timer.timeout.connect(self._reset_click_count)
		self._click_timer.setSingleShot(True)
		self._click_timer.setInterval(500)  # 500ms内完成三击

		# 文件夹路径存储
		self._left_folder = None
		self._right_folder = None

		# 自动恢复定时器（5秒）
		self._auto_restore_timer = QTimer()
		self._auto_restore_timer.timeout.connect(self._auto_restore)
		self._auto_restore_timer.setSingleShot(True)
		self._auto_restore_timer.setInterval(5000)  # 5秒后自动恢复

		# 灵动岛动画相关
		self._expand_anim = QPropertyAnimation(self, b"geometry")
		self._expand_anim.setEasingCurve(QEasingCurve.InOutQuad)
		self._expand_anim.setDuration(400)
		self._expand_anim.finished.connect(self._on_animation_finished)

		self.setMouseTracking(True)

	def showEvent(self, ev):
		super().showEvent(ev)
		if self._click_through and sys.platform.startswith("win"):
			hwnd = int(self.winId())
			GWL_EXSTYLE = -20
			WS_EX_LAYERED = 0x80000
			WS_EX_TRANSPARENT = 0x20
			user32 = ctypes.windll.user32
			cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
			user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_LAYERED | WS_EX_TRANSPARENT)

	def paintEvent(self, event):
		w = self.width()
		h = self.height()

		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)

		path = QPainterPath()
		r = float(self._radius)

		if self._is_expanded:
			# 扩张状态 - 保持底部圆润的形状
			path.moveTo(0.0, 0.0)
			path.lineTo(w, 0.0)
			path.lineTo(w, h - r)
			path.quadTo(w, h, w - r, h)
			path.lineTo(r, h)
			path.quadTo(0, h, 0, h - r)
			path.closeSubpath()
		else:
			# 正常状态 - 原始刘海形状
			path.moveTo(0.0, 0.0)
			path.lineTo(w, 0.0)
			path.lineTo(w, h - r)
			path.quadTo(w, h, w - r, h)
			path.lineTo(r, h)
			path.quadTo(0, h, 0, h - r)
			path.closeSubpath()

		# 先填充背景
		painter.fillPath(path, self._bg_color)

		# 只有在扩张状态且_show_text为True时才绘制文字
		if self._is_expanded and self._show_text:
			# 绘制文字或文件夹图标
			painter.setPen(QColor(255, 255, 255))
			font = QFont("Microsoft YaHei", 12)  # 使用微软系统默认字体
			painter.setFont(font)

			# 计算文本绘制区域，考虑圆角
			text_height = h
			text_y = 0

			# 计算左右侧边区域的宽度（各150像素）
			left_width = 150
			right_width = 150

			# 左侧区域
			if self._left_folder:
				# 显示文件夹图标和名称
				folder_name = os.path.basename(self._left_folder)
				if len(folder_name) > 6:
					folder_name = folder_name[:6] + "..."
				# 使用emoji图标
				text = f"📁 {folder_name}"
				painter.drawText(5, text_y, left_width - 10, text_height, Qt.AlignLeft | Qt.AlignVCenter, text)
			else:
				# 使用emoji图标
				painter.drawText(0, text_y, left_width, text_height, Qt.AlignCenter, "📥 中转站")

			# 右侧区域
			if self._right_folder:
				# 显示文件夹图标和名称
				folder_name = os.path.basename(self._right_folder)
				if len(folder_name) > 6:
					folder_name = folder_name[:6] + "..."
				# 使用emoji图标
				text = f"📁 {folder_name}"
				painter.drawText(w - right_width + 5, text_y, right_width - 10, text_height, Qt.AlignLeft | Qt.AlignVCenter, text)
			else:
				# 使用emoji图标
				painter.drawText(w - right_width, text_y, right_width, text_height, Qt.AlignCenter, "📂 文件")

	def mousePressEvent(self, ev):
		if self._click_through:
			return

		# 三击检测
		self._click_count += 1
		if self._click_count == 1:
			self._click_timer.start()
		elif self._click_count == 3:
			self._click_timer.stop()
			self._reset_click_count()
			self._toggle_expansion()
			return

		super().mousePressEvent(ev)

	def mouseReleaseEvent(self, ev):
		if self._is_expanded and not self._click_through:
			# 检查点击位置
			mid_x = self.width() // 2
			if ev.x() < mid_x:
				# 点击左侧
				if not self._left_folder:
					self._select_folder("left")
				else:
					self._open_folder(self._left_folder)
			else:
				# 点击右侧
				if not self._right_folder:
					self._select_folder("right")
				else:
					self._open_folder(self._right_folder)
		super().mouseReleaseEvent(ev)

	def _reset_click_count(self):
		self._click_count = 0

	def _toggle_expansion(self):
		if self._is_animating:
			return
			
		self._is_expanded = not self._is_expanded
		self._is_animating = True
		
		if self._is_expanded:
			# 扩张动画 - 灵动岛风格
			current_rect = self.geometry()
			
			# 第一阶段：轻微收缩
			stage1_rect = QRect(
				current_rect.x() + 10, 
				current_rect.y(), 
				current_rect.width() - 20, 
				current_rect.height()
			)
			
			# 第二阶段：扩张到目标大小
			stage2_rect = self._expanded_rect
			
			# 创建动画序列
			self._expand_anim.stop()
			self._expand_anim.setStartValue(current_rect)
			self._expand_anim.setEndValue(stage1_rect)
			self._expand_anim.setDuration(150)
			self._expand_anim.finished.disconnect()
			self._expand_anim.finished.connect(lambda: self._expand_stage2(stage2_rect))
			self._expand_anim.start()
		else:
			# 收缩动画 - 灵动岛风格
			current_rect = self.geometry()
			
			# 第一阶段：轻微扩张
			stage1_rect = QRect(
				current_rect.x() - 10, 
				current_rect.y(), 
				current_rect.width() + 20, 
				current_rect.height()
			)
			
			# 第二阶段：收缩到原始大小
			stage2_rect = self._base_rect
			
			# 创建动画序列
			self._expand_anim.stop()
			self._expand_anim.setStartValue(current_rect)
			self._expand_anim.setEndValue(stage1_rect)
			self._expand_anim.setDuration(150)
			self._expand_anim.finished.disconnect()
			self._expand_anim.finished.connect(lambda: self._expand_stage2(stage2_rect))
			self._expand_anim.start()

	def _expand_stage2(self, target_rect):
		# 第二阶段动画
		self._expand_anim.stop()
		self._expand_anim.setStartValue(self.geometry())
		self._expand_anim.setEndValue(target_rect)
		self._expand_anim.setDuration(250)
		self._expand_anim.finished.disconnect()
		self._expand_anim.finished.connect(self._on_animation_finished)
		self._expand_anim.start()

	def _on_animation_finished(self):
		self._is_animating = False
		# 如果是扩张状态，启动自动恢复定时器并显示文字
		if self._is_expanded:
			self._auto_restore_timer.start()
			# 延迟一小段时间后显示文字，增强动画效果
			QTimer.singleShot(100, self._show_text_after_delay)
		else:
			# 收缩时隐藏文字
			self._show_text = False
		self.update()  # 确保动画完成后重绘

	def _show_text_after_delay(self):
		# 延迟显示文字
		self._show_text = True
		self.update()

	def _auto_restore(self):
		# 5秒后自动恢复到原始大小
		if self._is_expanded and not self._is_animating:
			self._toggle_expansion()

	def _select_folder(self, side):
		folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
		if folder:
			if side == "left":
				self._left_folder = folder
			else:
				self._right_folder = folder
			self.update()  # 重绘界面

	def _open_folder(self, folder_path):
		if sys.platform == "win32":
			os.startfile(folder_path)
		elif sys.platform == "darwin":
			subprocess.Popen(["open", folder_path])
		else:
			subprocess.Popen(["xdg-open", folder_path])

	def enterEvent(self, event):
		if self._click_through or self._is_expanded or self._is_animating:
			return

		base = self._base_rect
		w = base.width()
		h = base.height()
		new_w = max(1, int(w * 1.06))
		new_h = max(1, int(h * 1.08))
		cx = base.center().x()
		new_x = cx - new_w // 2
		new_y = base.top()
		end_rect = QRect(new_x, new_y, new_w, new_h)

		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(end_rect)
		self._anim.start()

	def leaveEvent(self, event):
		if self._click_through or self._is_expanded or self._is_animating:
			return

		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(self._base_rect)
		self._anim.start()

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Escape:
			QApplication.quit()
		if event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier):
			QApplication.quit()


def main():
	import argparse

	parser = argparse.ArgumentParser(description="在屏幕顶部居中显示一个简单的刘海覆盖，支持鼠标悬停放大。")
	parser.add_argument("--clickthrough", action="store_true", help="使覆盖层可点击穿透（不会阻止鼠标事件）。")
	args = parser.parse_args()

	app = QApplication(sys.argv)

	w = NotchWindow(click_through=args.clickthrough)
	w.show()

	try:
		sys.exit(app.exec_())
	except KeyboardInterrupt:
		pass


if __name__ == '__main__':
	main()