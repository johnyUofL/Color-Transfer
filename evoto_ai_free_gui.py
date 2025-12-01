import sys
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Face detector (built-in, offline)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def evoto_perfect_skin_transfer(target_path, ref_path, strength=80):
    strength = strength / 100.0

    target = Image.open(target_path).convert("RGB")
    ref    = Image.open(ref_path).convert("RGB")
    ref = ref.resize(target.size, Image.LANCZOS)

    t_np = np.array(target, dtype=np.float64)
    r_np = np.array(ref,    dtype=np.float64)

    # Convert to LAB
    t_lab = cv2.cvtColor(t_np.astype(np.uint8), cv2.COLOR_RGB2LAB)
    r_lab = cv2.cvtColor(r_np.astype(np.uint8), cv2.COLOR_RGB2LAB)

    # Detect faces in both images
    t_gray = cv2.cvtColor(t_np.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    r_gray = cv2.cvtColor(r_np.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    t_faces = face_cascade.detectMultiScale(t_gray, 1.15, 5, minSize=(100,100))
    r_faces = face_cascade.detectMultiScale(r_gray, 1.15, 5, minSize=(100,100))

    result_lab = t_lab.astype(np.float64)

    # === 1. GLOBAL color transfer (background, clothes, mood) ===
    for i in [1, 2]:
        t_mean, t_std = t_lab[:,:,i].mean(), t_lab[:,:,i].std()
        r_mean, r_std = r_lab[:,:,i].mean(), r_lab[:,:,i].std()
        transferred = (t_lab[:,:,i] - t_mean) * (r_std / (t_std + 1e-8)) + r_mean
        result_lab[:,:,i] = t_lab[:,:,i] * (1 - strength) + transferred * strength

    # === 2. SKIN-ONLY transfer (only if faces exist in BOTH images) ===
    if len(t_faces) > 0 and len(r_faces) > 0:
        # Take the largest face from each
        tx, ty, tw, th = max(t_faces, key=lambda x: x[2]*x[3])
        rx, ry, rw, rh = max(r_faces, key=lambda x: x[2]*x[3])

        # Extract skin regions
        t_skin = t_lab[ty:ty+th, tx:tx+tw, 1:3]   # a,b channels only
        r_skin = r_lab[ry:ry+rh, rx:rx+rw, 1:3]

        # Compute skin color statistics
        t_skin_mean = t_skin.mean(axis=(0,1))
        t_skin_std  = t_skin.std(axis=(0,1))
        r_skin_mean = r_skin.mean(axis=(0,1))
        r_skin_std  = r_skin.std(axis=(0,1))

        # Apply skin correction globally but stronger on face area
        skin_strength = strength * 1.3  # skin gets a little extra boost
        skin_strength = min(1.0, skin_strength)

        transferred_skin = (t_lab[:,:,1:3] - t_skin_mean) * (r_skin_std / (t_skin_std + 1e-8)) + r_skin_mean
        result_lab[:,:,1:3] = t_lab[:,:,1:3] * (1 - skin_strength) + transferred_skin * skin_strength

    # Lightness: very gentle
    result_lab[:,:,0] = t_lab[:,:,0] * 0.85 + r_lab[:,:,0].mean() * 0.15

    # Final conversion
    result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB)
    result = Image.fromarray(result)

    # Subtle Evoto polish
    result = ImageEnhance.Contrast(result).enhance(1.05)
    result = ImageEnhance.Color(result).enhance(1.08)

    return result

class Worker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, t, r, s): super().__init__(); self.t=t; self.r=r; self.s=s
    def run(self):
        try:
            res = evoto_perfect_skin_transfer(self.t, self.r, self.s)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit("Error: " + str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FREE EVOTO PRO – PERFECT SKIN COLOR TRANSFER")
        self.setGeometry(50,50,1500,900)
        w = QWidget(); self.setCentralWidget(w); h = QHBoxLayout(w)

        left = QVBoxLayout()
        self.l1 = QLabel("Click → YOUR photo"); self.l1.setStyleSheet("border:4px dashed #3498db;background:#f0f8ff;font-size:20px;"); self.l1.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l1.setMinimumHeight(400); self.l1.mousePressEvent = lambda e:self.pick("t")
        self.l2 = QLabel("Click → REFERENCE photo (with desired skin tone)"); self.l2.setStyleSheet("border:4px dashed #e67e22;background:#fdf5e6;font-size:20px;"); self.l2.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l2.setMinimumHeight(400); self.l2.mousePressEvent = lambda e:self.pick("r")
        left.addWidget(self.l1); left.addWidget(self.l2); h.addLayout(left)

        right = QVBoxLayout()
        right.addWidget(QLabel("<h1>Free Evoto Pro</h1><h3>Exact Skin Color Transfer + Mood</h3>"))

        sld = QHBoxLayout()
        sld.addWidget(QLabel("Strength:"))
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(10,100); self.slider.setValue(80)
        self.slider.setStyleSheet("QSlider::handle{background:#e67e22;width:24px;border-radius:12px;}")
        self.val = QLabel("80%"); self.slider.valueChanged.connect(lambda v: self.val.setText(f"{v}%"))
        sld.addWidget(self.slider); sld.addWidget(self.val); right.addLayout(sld)

        self.btn = QPushButton("GENERATE – Perfect Skin + Mood"); self.btn.clicked.connect(self.go)
        self.btn.setStyleSheet("font-size:26px;padding:28px;background:#e67e22;color:white;")
        right.addWidget(self.btn)

        self.res = QLabel("Result"); self.res.setStyleSheet("border:8px solid #2c3e50;background:#2c3e50;")
        self.res.setAlignment(Qt.AlignmentFlag.AlignCenter); right.addWidget(self.res,1)
        h.addLayout(right)

        self.tp = self.rp = None

    def pick(self, x):
        p,_ = QFileDialog.getOpenFileName(self,"Open","", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if p:
            pix = QPixmap(p).scaled(560,560,Qt.AspectRatioMode.KeepAspectRatio)
            if x=="t": self.tp=p; self.l1.setPixmap(pix)
            else:      self.rp=p; self.l2.setPixmap(pix)

    def go(self):
        if not self.tp or not self.rp: QMessageBox.warning(self,"","Pick both photos!"); return
        self.btn.setEnabled(False); self.btn.setText("Working…")
        self.w = Worker(self.tp, self.rp, self.slider.value())
        self.w.finished.connect(self.done); self.w.start()

    def done(self, data):
        if isinstance(data,str): QMessageBox.critical(self,"Error",data)
        else:
            q = QImage(data.tobytes(), data.width, data.height, data.width*3, QImage.Format.Format_RGB888)
            self.res.setPixmap(QPixmap.fromImage(q).scaled(1000,1000,Qt.AspectRatioMode.KeepAspectRatio))
            data.save("Evoto_Perfect_Skin_Result.jpg")
            QMessageBox.information(self,"MASTERPIECE","Saved as Evoto_Perfect_Skin_Result.jpg\nSkin color perfectly matched!")
        self.btn.setText("GENERATE – Perfect Skin + Mood"); self.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())