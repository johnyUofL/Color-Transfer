import sys
import os
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QImage, QIcon, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# ==================== MAIN TRANSFER ENGINE ====================
def evoto_master_transfer(target_path, ref_path, strength=80, skin_boost=True, mood_only=False):
    strength = strength / 100.0
    target = Image.open(target_path).convert("RGB")
    ref    = Image.open(ref_path).convert("RGB")
    ref = ref.resize(target.size, Image.LANCZOS)

    t = np.array(target, dtype=np.float64)
    r = np.array(ref,    dtype=np.float64)
    t_lab = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_RGB2LAB)
    r_lab = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_RGB2LAB)
    result_lab = t_lab.astype(np.float64)

    # Global mood transfer
    if not mood_only:
        for i in [1, 2]:
            tm, ts = t_lab[:,:,i].mean(), t_lab[:,:,i].std()
            rm, rs = r_lab[:,:,i].mean(), r_lab[:,:,i].std()
            trans = (t_lab[:,:,i] - tm) * (rs / (ts + 1e-8)) + rm
            result_lab[:,:,i] = t_lab[:,:,i] * (1 - strength) + trans * strength

    # Skin transfer (only if faces in both)
    if skin_boost:
        t_gray = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        r_gray = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        t_faces = face_cascade.detectMultiScale(t_gray, 1.15, 5, minSize=(80,80))
        r_faces = face_cascade.detectMultiScale(r_gray, 1.15, 5, minSize=(80,80))
        if len(t_faces) > 0 and len(r_faces) > 0:
            tx,ty,tw,th = max(t_faces, key=lambda x:x[2]*x[3])
            rx,ry,rw,rh = max(r_faces, key=lambda x:x[2]*x[3])
            t_skin = t_lab[ty:ty+th, tx:tx+tw, 1:3]
            r_skin = r_lab[ry:ry+rh, rx:rx+rw, 1:3]
            ts_mean, ts_std = t_skin.mean(axis=(0,1)), t_skin.std(axis=(0,1))
            rs_mean, rs_std = r_skin.mean(axis=(0,1)), r_skin.std(axis=(0,1))
            trans_skin = (t_lab[:,:,1:3] - ts_mean) * (rs_std/(ts_std+1e-8)) + rs_mean
            result_lab[:,:,1:3] = t_lab[:,:,1:3] * (1 - strength*1.3) + trans_skin * strength*1.3

    # Lightness (gentle)
    result_lab[:,:,0] = t_lab[:,:,0] * 0.85 + r_lab[:,:,0].mean() * 0.15

    result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB)
    result = Image.fromarray(result)

    result = ImageEnhance.Contrast(result).enhance(1.0 + 0.1*strength)
    result = ImageEnhance.Color(result).enhance(1.0 + 0.2*strength)
    return result

class Worker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, t, r, s, skin, mood): super().__init__(); self.t=t; self.r=r; self.s=s; self.skin=skin; self.mood=mood
    def run(self):
        try:
            res = evoto_master_transfer(self.t, self.r, self.s, self.skin, self.mood)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit("Error: " + str(e))

class EvotoProStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EVOTO PRO STUDIO 2025 – FREE FOREVER")
        self.setGeometry(50,30,1600,1000)
        self.setStyleSheet("background:#1a1a1a; color:#f0f0f0;")
        self.tp = self.rp = None

        # Central widget
        w = QWidget(); self.setCentralWidget(w)
        main = QHBoxLayout(w)

        # === LEFT PANEL ===
        left = QVBoxLayout()
        title = QLabel("EVOTO\nPRO STUDIO"); title.setFont(QFont("Helvetica", 36, QFont.Weight.Bold)); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:#e67e22;")
        left.addWidget(title)

        self.l1 = QLabel("Click → YOUR PHOTO"); self.l1.setStyleSheet("border:5px dashed #3498db; background:#2c3e50; font-size:22px; min-height:420px;")
        self.l1.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l1.mousePressEvent = lambda e:self.pick("t")
        self.l2 = QLabel("Click → REFERENCE"); self.l2.setStyleSheet("border:5px dashed #e74c3c; background:#2c3e50; font-size:22px; min-height:420px;")
        self.l2.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l2.mousePressEvent = lambda e:self.pick("r")
        left.addWidget(self.l1); left.addWidget(self.l2)
        main.addLayout(left)

        # === RIGHT PANEL ===
        right = QVBoxLayout()
        tools = QGroupBox("TOOLS")
        tools.setStyleSheet("QGroupBox { font-size:18px; font-weight:bold; border:2px solid #444; border-radius:10px; margin:10px; }")
        tlay = QVBoxLayout()

        # Strength slider
        s = QHBoxLayout(); s.addWidget(QLabel("Strength:")); self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(0,100); self.slider.setValue(80)
        self.slider.setStyleSheet("QSlider::handle{background:#e67e22; width:30px; border-radius:15px;}")
        self.val = QLabel("80%"); self.slider.valueChanged.connect(lambda v:self.val.setText(f"{v}%")); s.addWidget(self.slider); s.addWidget(self.val)
        tlay.addLayout(s)

        # Checkboxes
        self.cb_skin = QCheckBox("Transfer Exact Skin Tone"); self.cb_skin.setChecked(True)
        self.cb_mood = QCheckBox("Mood & Lighting Only"); self.cb_mood.setChecked(False)
        tlay.addWidget(self.cb_skin); tlay.addWidget(self.cb_mood)

        # Buttons
        self.btn = QPushButton("GENERATE MASTERPIECE")
        self.btn.setStyleSheet("background:#e67e22; font-size:28px; padding:20px; border-radius:15px;")
        self.btn.clicked.connect(self.go)
        tlay.addWidget(self.btn)

        # Photoshop buttons
        psd = QHBoxLayout()
        btn_ps_open = QPushButton("Open PSD"); btn_ps_open.clicked.connect(self.open_psd); btn_ps_open.setStyleSheet("background:#444; padding:12px;")
        btn_ps_save = QPushButton("Save as PSD"); btn_ps_save.clicked.connect(self.save_psd); btn_ps_save.setStyleSheet("background:#444; padding:12px;")
        psd.addWidget(btn_ps_open); psd.addWidget(btn_ps_save)
        tlay.addLayout(psd)

        tools.setLayout(tlay); right.addWidget(tools)

        # Result
        self.res = QLabel("Result will appear here")
        self.res.setStyleSheet("border:8px solid #e67e22; background:#000; min-height:600px;")
        self.res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.res,1)
        main.addLayout(right)

    def pick(self, x):
        p,_ = QFileDialog.getOpenFileName(self,"Open","", "Images (*.png *.jpg *.jpeg *.psd)")
        if p:
            pix = QPixmap(p).scaled(560,560,Qt.AspectRatioMode.KeepAspectRatio)
            if x=="t": self.tp=p; self.l1.setPixmap(pix)
            else:      self.rp=p; self.l2.setPixmap(pix)

    def open_psd(self):
        path,_ = QFileDialog.getOpenFileName(self,"Open PSD","", "PSD (*.psd)")
        if path: self.tp = path; self.l1.setPixmap(QPixmap(path).scaled(560,560,Qt.AspectRatioMode.KeepAspectRatio))

    def save_psd(self):
        if hasattr(self, 'last_result'):
            path,_ = QFileDialog.getSaveFileName(self,"Save as PSD","", "PSD (*.psd)")
            if path: self.last_result.save(path)

    def go(self):
        if not self.tp or not self.rp: QMessageBox.warning(self,"","Pick both images!"); return
        self.btn.setEnabled(False); self.btn.setText("Creating masterpiece…")
        self.w = Worker(self.tp, self.rp, self.slider.value(), self.cb_skin.isChecked(), self.cb_mood.isChecked())
        self.w.finished.connect(self.done); self.w.start()

    def done(self, data):
        if isinstance(data,str): QMessageBox.critical(self,"Error",data)
        else:
            self.last_result = data
            q = QImage(data.tobytes(), data.width, data.height, data.width*3, QImage.Format.Format_RGB888)
            self.res.setPixmap(QPixmap.fromImage(q).scaled(1100,1100,Qt.AspectRatioMode.KeepAspectRatio))
            data.save("EVOTO_MASTERPIECE.jpg")
            QMessageBox.information(self,"DONE","Saved as EVOTO_MASTERPIECE.jpg")
        self.btn.setText("GENERATE MASTERPIECE"); self.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = EvotoProStudio()
    win.show()
    sys.exit(app.exec())
    