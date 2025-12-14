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

		# Window covers just the notch area
		self.setGeometry(x, y, notch_w, notch_h)
		self.setWindowFlags(
			Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
		)
		self.setAttribute(Qt.WA_TranslucentBackground)

		self._bg_color = QColor(0, 0, 0)
		self._radius = radius

		self._click_through = click_through

		# 保留基准几何（用于恢复）
		self._base_rect = self.geometry()

		# 动画用于平滑放大/缩小（只改变几何）
		self._anim = QPropertyAnimation(self, b"geometry")
		self._anim.setEasingCurve(QEasingCurve.OutCubic)
		self._anim.setDuration(200)
		# 状态：是否正在显示“新消息”提示
		self._showing_msg = False
		self._msg_timer = QTimer(self)
		self._msg_timer.setSingleShot(True)
		self._msg_timer.timeout.connect(self._hide_play_info)

		# WeChat 轮询检测
		# 媒体/网易云轮询检测
		self._last_track = None
		self._poll_timer = QTimer(self)
		self._poll_timer.timeout.connect(self._poll_media)
		self._poll_timer.start(1000)

		# 滚动字幕状态
		self._left_text = ""
		self._right_text = ""
		self._left_offset = 0
		self._right_offset = 0
		self._left_width = 0
		self._right_width = 0
		self._marquee_timer = QTimer(self)
		self._marquee_timer.timeout.connect(self._marquee_tick)
		self._marquee_timer.setInterval(40)

		# 三击检测与快捷功能状态
		self._click_count = 0
		self._click_count_timer = QTimer(self)
		self._click_count_timer.setSingleShot(True)
		self._click_count_timer.setInterval(700)
		self._click_count_timer.timeout.connect(lambda: setattr(self, '_click_count', 0))

		self._showing_quick = False
		self._quick_timer = QTimer(self)
		self._quick_timer.setSingleShot(True)
		self._quick_timer.timeout.connect(self._hide_quick_actions)

		# 保存图标热区（相对于窗口）
		self._quick_icon_areas = []

		# 绘制用字体
		self._font = QFont("Segoe UI", 10)

		# 尝试导入 pywin32 的窗口枚举函数（仅在 Windows 可用）
		self._win32_available = False
		if sys.platform.startswith("win"):
			try:
				import win32gui
				import win32con
				self._win32_available = True
				self._win32 = win32gui
				self._win32con = win32con
			except Exception:
				self._win32_available = False


		# 启用鼠标追踪以接收 enter/leave 事件（若窗口非点击穿透）
		self.setMouseTracking(True)

	def showEvent(self, ev):
		super().showEvent(ev)
		if self._click_through and sys.platform.startswith("win"):
			# Make the window click-through on Windows
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

		# 提前获取字体度量，避免后续在不同分支中未定义 fm
		fm = painter.fontMetrics()

		path = QPainterPath()
		r = float(self._radius)

		# 构建顶部平直、底部左右圆角的路径
		path.moveTo(0.0, 0.0)
		path.lineTo(w, 0.0)
		path.lineTo(w, h - r)
		# 右下圆角（使用二次贝塞尔拟合圆角）
		path.quadTo(w, h, w - r, h)
		path.lineTo(r, h)
		# 左下圆角
		path.quadTo(0, h, 0, h - r)
		path.closeSubpath()

		painter.fillPath(path, self._bg_color)

		# 预计算布局变量，确保在任何分支都可用（避免 UnboundLocalError）
		icon_size = min(28, int(self.height() * 0.7))
		icon_margin = 8
		ix = icon_margin
		iy = (self.height() - icon_size) // 2
		# 左侧可用区域（图标右侧到中线）
		left_area_x = ix + icon_size + 8
		left_area_w = max(10, self.width()//2 - left_area_x - 8)
		# 右侧可用区域（中线到右侧）
		right_area_x = self.width()//2 + 8
		right_area_w = max(10, self.width() - right_area_x - 12)

		# 如果处于消息显示状态，绘制左侧图标与右侧文字
		if self._showing_msg:
			painter.setRenderHint(QPainter.Antialiasing)
			# 网易云红色圆角方块
			painter.setBrush(QColor(230, 26, 26))
			painter.setPen(Qt.NoPen)
			painter.drawRoundedRect(int(ix), int(iy), int(icon_size), int(icon_size), int(icon_size/4), int(icon_size/4))
			# 简化的白色音乐符号（圆形+矩形）
			painter.setBrush(QColor(255, 255, 255))
			head_w = icon_size * 0.45
			head_h = icon_size * 0.45
			head_x = ix + icon_size * 0.28
			head_y = iy + icon_size * 0.18
			painter.drawEllipse(int(head_x), int(head_y), int(head_w), int(head_h))
			stem_w = max(2, int(icon_size * 0.12))
			stem_h = int(icon_size * 0.55)
			stem_x = head_x + head_w - stem_w//2
			stem_y = head_y - int(icon_size * 0.25)
			painter.drawRect(int(stem_x), int(stem_y), int(stem_w), int(stem_h))

			# 左侧：歌曲名（图标右侧），右侧：歌词或提示
			painter.setFont(self._font)
			painter.setPen(QColor(255, 255, 255))
			fm = painter.fontMetrics()
			# 计算可用区域
			left_area_x = ix + icon_size + 8
			left_area_w = max(10, self.width()//2 - left_area_x - 8)
			right_area_x = self.width()//2 + 8
			right_area_w = max(10, self.width() - right_area_x - 12)

			# 绘制左侧滚动文本
			if self._left_text:
				self._left_width = fm.width(self._left_text)
				if self._left_width <= left_area_w:
					# 居中显示
					tx = left_area_x + (left_area_w - self._left_width)//2
					painter.drawText(int(tx), int(self.height()//2 + fm.ascent()//2), self._left_text)
				else:
					# 滚动
					tx = left_area_x - self._left_offset
					# 如果偏移过大，回绕
					if self._left_offset > (self._left_width + left_area_w + 20):
						self._left_offset = 0
					painter.drawText(int(tx), int(self.height()//2 + fm.ascent()//2), self._left_text)

			# 绘制右侧滚动文本
			if self._right_text:
				self._right_width = fm.width(self._right_text)
				if self._right_width <= right_area_w:
					tx2 = right_area_x + (right_area_w - self._right_width)//2
					painter.drawText(int(tx2), int(self.height()//2 + fm.ascent()//2), self._right_text)
				else:
					tx2 = right_area_x - self._right_offset
					if self._right_offset > (self._right_width + right_area_w + 20):
						self._right_offset = 0
					painter.drawText(int(tx2), int(self.height()//2 + fm.ascent()//2), self._right_text)

		# 如果处于快捷功能显示，绘制左侧文字提示与右侧两个图标
		if self._showing_quick:
			# 覆盖左侧文本为 "快捷功能"
			painter.setFont(self._font)
			painter.setPen(QColor(255, 255, 255))
			quick_text = "快捷功能"
			qw = fm.width(quick_text)
			qtx = left_area_x + (left_area_w - qw)//2
			painter.drawText(int(qtx), int(self.height()//2 + fm.ascent()//2), quick_text)

			# 右侧绘制两个小图标：微信（绿色）与腾讯会议（蓝色）
			icon_w = min(26, int(self.height() * 0.6))
			gap = 8
			start_x = right_area_x + (right_area_w - (icon_w*2 + gap))//2
			ia1 = QRect(int(start_x), int((self.height()-icon_w)//2), int(icon_w), int(icon_w))
			ia2 = QRect(int(start_x + icon_w + gap), int((self.height()-icon_w)//2), int(icon_w), int(icon_w))
			# draw WeChat style small rounded icon
			painter.setBrush(QColor(7, 193, 96))
			painter.setPen(Qt.NoPen)
			painter.drawRoundedRect(ia1, int(icon_w/4), int(icon_w/4))
			painter.setBrush(QColor(255,255,255))
			painter.drawEllipse(int(ia1.x()+icon_w*0.18), int(ia1.y()+icon_w*0.18), int(icon_w*0.45), int(icon_w*0.45))
			# draw Tencent Meeting small icon (blue)
			painter.setBrush(QColor(38, 115, 255))
			painter.drawRoundedRect(ia2, int(icon_w/4), int(icon_w/4))
			painter.setBrush(QColor(255,255,255))
			# draw simplified meeting camera shape
			painter.drawRect(ia2.x()+int(icon_w*0.22), ia2.y()+int(icon_w*0.28), int(icon_w*0.36), int(icon_w*0.28))

			# 保存图标区域用于点击检测
			self._quick_icon_areas = [ia1, ia2]

	def enterEvent(self, event):
		# 如果窗口设置了点击穿透，则不会接收鼠标事件
		if self._click_through:
			return

		# 计算稍微放大的几何（顶部保持不变，向下扩展）
		base = self._base_rect
		w = base.width()
		h = base.height()
		# 微小放大比例：宽度 +6%，高度 +8%
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

		# 恢复到基准几何
		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(self._base_rect)
		self._anim.start()

	def mousePressEvent(self, event):
		if self._click_through:
			return

		pos = event.pos()

		# 若处于快捷功能显示，检测是否点中了图标
		if self._showing_quick and self._quick_icon_areas:
			for idx, rect in enumerate(self._quick_icon_areas):
				if rect.contains(pos):
					if idx == 0:
						self._activate_wechat()
						return
					elif idx == 1:
						self._activate_tencent_meeting()
						return

		# 如果正在显示播放信息，点击则尝试激活/打开网易云音乐
		if self._showing_msg and self._win32_available:
			self._activate_netease()
			return

		# 三击检测：在短时间内连续三次点击展开快捷功能
		self._click_count += 1
		self._click_count_timer.start()
		if self._click_count >= 3:
			self._click_count = 0
			self._click_count_timer.stop()
			self._show_quick_actions()
			return

		super().mousePressEvent(event)


	def _show_quick_actions(self, duration_ms: int = 4000):
		if self._showing_quick:
			return
		self._showing_quick = True
		# 展开刘海，幅度比播放信息小一些
		base = self._base_rect
		sw = QApplication.instance().primaryScreen().geometry().width()
		extra = min(int(base.width() * 0.5), int(sw * 0.25))
		new_w = min(base.width() + extra, int(sw * 0.9))
		cx = base.center().x()
		new_x = cx - new_w // 2
		end_rect = QRect(new_x, base.top(), new_w, base.height())

		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(end_rect)
		self._anim.start()

		self._quick_timer.start(duration_ms)


	def _hide_quick_actions(self):
		self._showing_quick = False
		self._quick_icon_areas = []
		# 恢复到基准尺寸
		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(self._base_rect)
		def on_finished():
			try:
				self._anim.finished.disconnect(on_finished)
			except Exception:
				pass
		self._anim.finished.connect(on_finished)
		self._anim.start()

	def _activate_wechat(self):
		if not self._win32_available:
			try:
				os.startfile('WeChat.exe')
			except Exception:
				pass
			return

		def enum(hwnd, _):
			if not self._win32.IsWindowVisible(hwnd):
				return True
			title = self._win32.GetWindowText(hwnd)
			if title and ("微信" in title or "WeChat" in title):
				try:
					self._win32.ShowWindow(hwnd, self._win32con.SW_RESTORE)
					self._win32.SetForegroundWindow(hwnd)
				except Exception:
					pass
				return False
			return True

		try:
			self._win32.EnumWindows(enum, None)
		except Exception:
			try:
				os.startfile('WeChat.exe')
			except Exception:
				pass

	def _activate_tencent_meeting(self):
		if not self._win32_available:
			# try common executables
			for exe in ('qqmeeting.exe','TencentMeeting.exe','TXMeeting.exe'):
				try:
					os.startfile(exe)
				except Exception:
					pass
			return

		def enum(hwnd, _):
			if not self._win32.IsWindowVisible(hwnd):
				return True
			title = self._win32.GetWindowText(hwnd)
			if title and ("腾讯会议" in title or "会议" in title or "QQMeeting" in title or "Tencent Meeting" in title):
				try:
					self._win32.ShowWindow(hwnd, self._win32con.SW_RESTORE)
					self._win32.SetForegroundWindow(hwnd)
				except Exception:
					pass
				return False
			return True

		try:
			self._win32.EnumWindows(enum, None)
		except Exception:
			for exe in ('qqmeeting.exe','TencentMeeting.exe','TXMeeting.exe'):
				try:
					os.startfile(exe)
				except Exception:
					pass

	def _activate_netease(self):
		# 找到第一个窗口标题或进程名指向网易云音乐的窗口并置前
		def enum(hwnd, _):
			if not self._win32.IsWindowVisible(hwnd):
				return True
			title = self._win32.GetWindowText(hwnd)
			if title and ("网易云音乐" in title or "CloudMusic" in title or "cloudmusic" in title.lower()):
				try:
					self._win32.ShowWindow(hwnd, self._win32con.SW_RESTORE)
					self._win32.SetForegroundWindow(hwnd)
				except Exception:
					pass
				return False
			return True

		try:
			self._win32.EnumWindows(enum, None)
		except Exception:
			# fallback: try to start NetEase Cloud Music if installed in PATH
			try:
				os.startfile('cloudmusic.exe')
			except Exception:
				pass

	def _poll_media(self):
		# 尝试通过窗口标题与进程名检测网易云音乐并判断是否在播放
		if not self._win32_available:
			return

		found = []
		def enum(hwnd, _):
			if not self._win32.IsWindowVisible(hwnd):
				return True
			title = self._win32.GetWindowText(hwnd)
			if title and ("网易云音乐" in title or "CloudMusic" in title or "cloudmusic" in title.lower()):
				# get pid
				try:
					_, pid = self._win32.GetWindowThreadProcessId(hwnd)
				except Exception:
					pid = None
				found.append((hwnd, title, pid))
			return True

		self._win32.EnumWindows(enum, None)
		if not found:
			self._last_track = None
			return

		# use first found window
		hwnd, title, pid = found[0]
		# clean title: remove trailing app name like - 网易云音乐
		clean = re.sub(r"\s*-\s*网易云音乐.*$", "", title)
		clean = re.sub(r"\s*-\s*CloudMusic.*$", "", clean)
		clean = clean.strip()

		if not clean or clean.lower() in ("netease cloud music", "网易云音乐"):
			# no track info
			self._last_track = None
			return

		# If track changed or newly playing
		if self._last_track != clean:
			self._last_track = clean
			# 此处无法获取歌词，显示纯音乐或空歌词占位
			lyrics = "纯音乐"
			# 分配左右文本：左=歌名, 右=歌词或提示
			self._show_play_info(song=clean, lyrics=lyrics)

	def _show_play_info(self, song: str, lyrics: str, duration_ms: int = 3000):
		# 设置文本并展开刘海
		self._left_text = song
		self._right_text = lyrics if lyrics else "纯音乐"
		self._left_offset = 0
		self._right_offset = 0
		self._marquee_timer.start()
		self._showing_msg = True

		base = self._base_rect
		sw = QApplication.instance().primaryScreen().geometry().width()
		extra = min(int(base.width() * 0.9), int(sw * 0.5))
		new_w = min(base.width() + extra, int(sw * 0.95))
		cx = base.center().x()
		new_x = cx - new_w // 2
		end_rect = QRect(new_x, base.top(), new_w, base.height())

		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(end_rect)
		self._anim.start()

		self._msg_timer.start(duration_ms)

	def _hide_play_info(self):
		self._marquee_timer.stop()
		self._left_text = ""
		self._right_text = ""
		self._left_offset = 0
		self._right_offset = 0
		# 动画回到基准尺寸
		self._anim.stop()
		self._anim.setStartValue(self.geometry())
		self._anim.setEndValue(self._base_rect)
		def on_finished():
			self._showing_msg = False
			try:
				self._anim.finished.disconnect(on_finished)
			except Exception:
				pass
		self._anim.finished.connect(on_finished)
		self._anim.start()

	def _marquee_tick(self):
		# update offsets for scrolling texts
		if self._left_text:
			self._left_offset += 2
			# approximate width using font metrics requires painter; use QFontMetrics
			fm = QFont(self._font).metrics() if False else None
			# We'll compute widths on paint to keep it simple; wrap offsets to large value
			if self._left_offset > 10000:
				self._left_offset = 0
		if self._right_text:
			self._right_offset += 2
			if self._right_offset > 10000:
				self._right_offset = 0
		self.update()


	def keyPressEvent(self, event):
		# Allow closing with Escape or Ctrl+Q
		if event.key() == Qt.Key_Escape:
			QApplication.quit()
		if event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier):
			QApplication.quit()


def main():
	import argparse

	parser = argparse.ArgumentParser(description="在屏幕顶部居中显示一个模拟 Mac 刘海 的透明覆盖窗口。")
	parser.add_argument("--clickthrough", action="store_true", help="使覆盖层可点击穿透（不会阻止鼠标事件）。")
	args = parser.parse_args()

	app = QApplication(sys.argv)

	w = NotchWindow(click_through=args.clickthrough)
	w.show()

	print("刘海已显示。按 Ctrl+C 终止，或运行时按 Esc 关闭（若窗口接收键盘事件）。")

	try:
		sys.exit(app.exec_())
	except KeyboardInterrupt:
		pass


if __name__ == '__main__':
	main()

