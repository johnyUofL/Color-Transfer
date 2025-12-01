import sys
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal

def evoto_perfect_transfer(target_path, ref_path):
    target = Image.open(target_path).convert("RGB")
    ref    = Image.open(ref_path).convert("RGB")
    ref = ref.resize(target.size, Image.LANCZOS)

    t = np.array(target, dtype=np.float64)
    r = np.array(ref,    dtype=np.float64)

    # Convert to LAB
    t_lab = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_RGB2LAB)
    r_lab = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_RGB2LAB)

    # Transfer ONLY the a and b channels (chroma) → keeps original brightness!
    # L channel (lightness) stays from the original photo → no black/white blowout
    for i in [1, 2]:  # a and b channels only
        t_mean, t_std = t_lab[:,:,i].mean(), t_lab[:,:,i].std()
        r_mean, r_std = r_lab[:,:,i].mean(), r_lab[:,:,i].std()
        t_lab[:,:,i] = (t_lab[:,:,i] - t_mean) * (r_std / (t_std + 1e-8)) + r_mean

    # Gentle lightness adaptation (only 15-20% influence from reference)
    t_l_mean = t_lab[:,:,0].mean()
    r_l_mean = r_lab[:,:,0].mean()
    t_lab[:,:,0] = t_lab[:,:,0] * 0.8 + r_l_mean * 0.2

    # Clip and convert back
    t_lab = np.clip(t_lab, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(t_lab, cv2.COLOR_LAB2RGB)
    result = Image.fromarray(result.astype(np.uint8))

    # Final gentle polish (Evoto signature)
    result = ImageEnhance.Contrast(result).enhance(1.05)
    result = ImageEnhance.Color(result).enhance(1.10)
    result = result.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=1))

    return result

class Worker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, t, r): super().__init__(); self.t=t; self.r=r
    def run(self):
        try:
            res = evoto_perfect_transfer(self.t, self.r)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit("Error: " + str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Free Evoto Clone – PERFECT & SAFE")
        self.setGeometry(100,100,1350,800)
        w = QWidget(); self.setCentralWidget(w); h = QHBoxLayout(w)

        left = QVBoxLayout()
        self.l1 = QLabel("Click → YOUR photo"); self.l1.setStyleSheet("border:3px dashed #3498db;background:#f8f9fa;font-size:18px;"); self.l1.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l1.setMinimumHeight(360); self.l1.mousePressEvent = lambda e:self.pick("t")
        self.l2 = QLabel("Click → REFERENCE photo"); self.l2.setStyleSheet("border:3px dashed #e74c3c;background:#fdf2f2;font-size:18px;"); self.l2.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l2.setMinimumHeight(360); self.l2.mousePressEvent = lambda e:self.pick("r")
        left.addWidget(self.l1); left.addWidget(self.l2); h.addLayout(left)

        right = QVBoxLayout()
        right.addWidget(QLabel("<h2>Free Evoto Clone – FINAL SAFE VERSION</h2>"))
        self.btn = QPushButton("GENERATE – Perfect Natural Look"); self.btn.clicked.connect(self.go); self.btn.setStyleSheet("font-size:22px;padding:20px;background:#27ae60;color:white;")
        right.addWidget(self.btn)
        self.res = QLabel("Result"); self.res.setStyleSheet("border:6px solid #2c3e50;background:#34495e;"); self.res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.res,1); h.addLayout(right)

        self.tp = self.rp = None

    def pick(self, x):
        p,_ = QFileDialog.getOpenFileName(self,"Open","", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if p:
            pix = QPixmap(p).scaled(520,520,Qt.AspectRatioMode.KeepAspectRatio)
            if x=="t": self.tp=p; self.l1.setPixmap(pix)
            else:      self.rp=p; self.l2.setPixmap(pix)

    def go(self):
        if not self.tp or not self.rp:
            QMessageBox.warning(self,"","Pick both photos!"); return
        self.btn.setEnabled(False); self.btn.setText("Creating perfect result…")
        self.w = Worker(self.tp, self.rp)
        self.w.finished.connect(self.done)
        self.w.start()

    def done(self, data):
        if isinstance(data, str):
            QMessageBox.critical(self,"Error",data)
        else:
            q = QImage(data.tobytes(), data.width, data.height, data.width*3, QImage.Format.Format_RGB888)
            self.res.setPixmap(QPixmap.fromImage(q).scaled(900,900,Qt.AspectRatioMode.KeepAspectRatio))
            data.save("Evoto_Perfect_Result.jpg")
            QMessageBox.information(self,"PERFECT!","Saved as Evoto_Perfect_Result.jpg")
        self.btn.setText("GENERATE – Perfect Natural Look"); self.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())