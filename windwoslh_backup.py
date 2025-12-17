import sys
import os
import ctypes
import re
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFont
from PyQt5.QtCore import Qt, QRectF, QRect, QPropertyAnimation, QEasingCurve, QTimer


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

		# hover animation
		self._anim = QPropertyAnimation(self, b"geometry")
		self._anim.setEasingCurve(QEasingCurve.OutCubic)
		self._anim.setDuration(200)

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

		path.moveTo(0.0, 0.0)
		path.lineTo(w, 0.0)
		path.lineTo(w, h - r)
		path.quadTo(w, h, w - r, h)
		path.lineTo(r, h)
		path.quadTo(0, h, 0, h - r)
		path.closeSubpath()

		painter.fillPath(path, self._bg_color)

	def enterEvent(self, event):
		if self._click_through:
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
		if self._click_through:
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