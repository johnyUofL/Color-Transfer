import sys
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal

def evoto_transfer_with_strength(target_path, ref_path, strength=75):
    strength = strength / 100.0  # 0.0 = original, 1.0 = full transfer

    target = Image.open(target_path).convert("RGB")
    ref    = Image.open(ref_path).convert("RGB")
    ref = ref.resize(target.size, Image.LANCZOS)

    t = np.array(target, dtype=np.float64)
    r = np.array(ref,    dtype=np.float64)

    t_lab = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_RGB2LAB)
    r_lab = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_RGB2LAB)

    result_lab = t_lab.copy()

    # Transfer a and b channels (color)
    for i in [1, 2]:
        t_mean, t_std = t_lab[:,:,i].mean(), t_lab[:,:,i].std()
        r_mean, r_std = r_lab[:,:,i].mean(), r_lab[:,:,i].std()
        transferred = (t_lab[:,:,i] - t_mean) * (r_std / (t_std + 1e-8)) + r_mean
        result_lab[:,:,i] = t_lab[:,:,i] * (1 - strength) + transferred * strength

    # Gentle lightness adaptation (only 20% max)
    light_strength = strength * 0.2
    t_l_mean = t_lab[:,:,0].mean()
    r_l_mean = r_lab[:,:,0].mean()
    result_lab[:,:,0] = t_lab[:,:,0] * (1 - light_strength) + r_l_mean * light_strength

    result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB)
    result = Image.fromarray(result.astype(np.uint8))

    # Final subtle polish
    result = ImageEnhance.Contrast(result).enhance(1.0 + 0.08 * strength)
    result = ImageEnhance.Color(result).enhance(1.0 + 0.15 * strength)
    result = result.filter(ImageFilter.UnsharpMask(radius=1, percent=50, threshold=1))

    return result

class Worker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, t, r, strength):
        super().__init__()
        self.t = t
        self.r = r
        self.strength = strength
    def run(self):
        try:
            res = evoto_transfer_with_strength(self.t, self.r, self.strength)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit("Error: " + str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Free Evoto Clone – WITH OPACITY SLIDER!")
        self.setGeometry(100,100,1400,820)
        w = QWidget(); self.setCentralWidget(w); main = QHBoxLayout(w)

        # Left
        left = QVBoxLayout()
        self.l1 = QLabel("Click → YOUR photo"); self.l1.setStyleSheet("border:3px dashed #3498db;background:#f8fbff;font-size:18px;"); self.l1.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l1.setMinimumHeight(360); self.l1.mousePressEvent = lambda e:self.pick("t")
        self.l2 = QLabel("Click → REFERENCE photo"); self.l2.setStyleSheet("border:3px dashed #e74c3c;background:#fff5f5;font-size:18px;"); self.l2.setAlignment(Qt.AlignmentFlag.AlignCenter); self.l2.setMinimumHeight(360); self.l2.mousePressEvent = lambda e:self.pick("r")
        left.addWidget(self.l1); left.addWidget(self.l2); main.addLayout(left)

        # Right
        right = QVBoxLayout()
        right.addWidget(QLabel("<h2>Free Evoto Clone</h2><h3>Photoshop-style Opacity Slider</h3>"))

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Color Strength:"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(75)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(10)
        self.strength_label = QLabel("75%")
        self.slider.valueChanged.connect(lambda v: self.strength_label.setText(f"{v}%"))
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.strength_label)
        right.addLayout(slider_layout)

        self.btn = QPushButton("GENERATE – Perfect Result")
        self.btn.setStyleSheet("font-size:24px;padding:22px;background:#27ae60;color:white;")
        self.btn.clicked.connect(self.go)
        right.addWidget(self.btn)

        self.res = QLabel("Result")
        self.res.setStyleSheet("border:6px solid #2c3e50;background:#34495e;")
        self.res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.res,1)
        main.addLayout(right)

        self.tp = self.rp = None

    def pick(self, x):
        p,_ = QFileDialog.getOpenFileName(self,"Open","", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if p:
            pix = QPixmap(p).scaled(520,520,Qt.AspectRatioMode.KeepAspectRatio)
            if x=="t": self.tp=p; self.l1.setPixmap(pix)
            else:      self.rp=p; self.l2.setPixmap(pix)

    def go(self):
        if not self.tp or not self.rp:
            QMessageBox.warning(self,"","Pick both photos first!"); return
        self.btn.setEnabled(False); self.btn.setText("Working…")
        strength = self.slider.value()
        self.w = Worker(self.tp, self.rp, strength)
        self.w.finished.connect(self.done)
        self.w.start()

    def done(self, data):
        if isinstance(data, str):
            QMessageBox.critical(self,"Error",data)
        else:
            q = QImage(data.tobytes(), data.width, data.height, data.width*3, QImage.Format.Format_RGB888)
            self.res.setPixmap(QPixmap.fromImage(q).scaled(900,900,Qt.AspectRatioMode.KeepAspectRatio))
            data.save("Evoto_Result_With_Slider.jpg")
            QMessageBox.information(self,"PERFECT","Saved as Evoto_Result_With_Slider.jpg")
        self.btn.setText("GENERATE – Perfect Result"); self.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())