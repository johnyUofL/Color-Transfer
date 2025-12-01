import sys
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def evoto_master_transfer(target_path, ref_path, strength=82, skin_boost=True):
    strength /= 100.0
    target = Image.open(target_path).convert("RGB")
    ref    = Image.open(ref_path).convert("RGB")
    ref = ref.resize(target.size, Image.LANCZOS)

    t = np.array(target, dtype=np.float64)
    r = np.array(ref,    dtype=np.float64)
    t_lab = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_RGB2LAB)
    r_lab = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_RGB2LAB)
    result_lab = t_lab.astype(np.float64)

    for i in [1, 2]:
        tm, ts = t_lab[:,:,i].mean(), t_lab[:,:,i].std()
        rm, rs = r_lab[:,:,i].mean(), r_lab[:,:,i].std()
        trans = (t_lab[:,:,i] - tm) * (rs / (ts + 1e-8)) + rm
        result_lab[:,:,i] = t_lab[:,:,i] * (1 - strength) + trans * strength

    if skin_boost:
        t_gray = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        r_gray = cv2.cvtColor(r.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        t_faces = face_cascade.detectMultiScale(t_gray, 1.15, 5, minSize=(80,80))
        r_faces = face_cascade.detectMultiScale(r_gray, 1.15, 5, minSize=(80,80))
        if len(t_faces) > 0 and len(r_faces) > 0:
            tx,ty,tw,th = max(t_faces, key=lambda x:x[2]*x[3])
            rx,ry,rw,rh = max(r_faces, key=lambda x:x[2]*x[3])
            ts_mean = t_lab[ty:ty+th, tx:tx+tw, 1:3].mean(axis=(0,1))
            ts_std  = t_lab[ty:ty+th, tx:tx+tw, 1:3].std(axis=(0,1))
            rs_mean = r_lab[ry:ry+rh, rx:rx+rw, 1:3].mean(axis=(0,1))
            rs_std  = r_lab[ry:ry+rh, rx:rx+rw, 1:3].std(axis=(0,1))
            trans_skin = (t_lab[:,:,1:3] - ts_mean) * (rs_std/(ts_std+1e-8)) + rs_mean
            result_lab[:,:,1:3] = t_lab[:,:,1:3] * (1 - strength*1.4) + trans_skin * strength*1.4

    result_lab[:,:,0] = t_lab[:,:,0] * 0.85 + r_lab[:,:,0].mean() * 0.15
    result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB)
    result = Image.fromarray(result)
    result = ImageEnhance.Contrast(result).enhance(1.0 + 0.1*strength)
    result = ImageEnhance.Color(result).enhance(1.0 + 0.2*strength)
    return result

class Worker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, t, r, s, skin): super().__init__(); self.t,self.r,self.s,self.skin = t,r,s,skin
    def run(self):
        try:
            res = evoto_master_transfer(self.t, self.r, self.s, self.skin)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit("Error: " + str(e))

class EvotoFree(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EVOTO FREE – STABLE ZOOM BUTTONS")
        self.setGeometry(50,50,1580,920)
        self.setStyleSheet("background:#1e1e1e;color:#eee;")
        self.tp = self.rp = None
        self.current_pixmap = None
        self.zoom_level = 1.0

        w = QWidget(); self.setCentralWidget(w)
        main = QHBoxLayout(w)

        # LEFT
        left = QVBoxLayout()
        title = QLabel("EVOTO FREE")
        title.setFont(QFont("Arial", 38, QFont.Weight.Bold))
        title.setStyleSheet("color:#ff9500"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(title)

        self.l1 = QLabel("YOUR PHOTO")
        self.l1.setStyleSheet("border:4px dashed #3498db;background:#2c3e50;font-size:20px;min-height:400px;")
        self.l1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.l1.mousePressEvent = lambda e: self.pick("t")

        self.l2 = QLabel("REFERENCE")
        self.l2.setStyleSheet("border:4px dashed #e74c3c;background:#2c3e50;font-size:20px;min-height:400px;")
        self.l2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.l2.mousePressEvent = lambda e: self.pick("r")

        left.addWidget(self.l1); left.addWidget(self.l2)
        main.addLayout(left)

        # RIGHT
        right = QVBoxLayout()
        right.addWidget(QLabel("<h2>Settings</h2>"))

        sld = QHBoxLayout()
        sld.addWidget(QLabel("Strength:"))
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(10,100); self.slider.setValue(82)
        self.slider.setStyleSheet("QSlider::handle{background:#ff9500;width:34px;border-radius:17px;}")
        self.val = QLabel("82%"); self.slider.valueChanged.connect(lambda v:self.val.setText(f"{v}%"))
        sld.addWidget(self.slider); sld.addWidget(self.val); right.addLayout(sld)

        self.cb = QCheckBox("Boost Skin Tone Match"); self.cb.setChecked(True); right.addWidget(self.cb)

        self.btn_gen = QPushButton("GENERATE")
        self.btn_gen.setStyleSheet("background:#ff9500;font-size:30px;padding:25px;border-radius:15px;")
        self.btn_gen.clicked.connect(self.generate)
        right.addWidget(self.btn_gen)

        # ZOOM BUTTONS
        zoom_bar = QHBoxLayout()
        zoom_bar.addStretch()
        btn_zoom_in = QPushButton("Zoom In")
        btn_zoom_in.setStyleSheet("background:#27ae60;color:white;padding:12px;font-size:18px;")
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out = QPushButton("Zoom Out")
        btn_zoom_out.setStyleSheet("background:#e74c3c;color:white;padding:12px;font-size:18px;")
        btn_zoom_out.clicked.connect(self.zoom_out)
        btn_reset = QPushButton("Fit")
        btn_reset.setStyleSheet("background:#3498db;color:white;padding:12px;font-size:18px;")
        btn_reset.clicked.connect(self.zoom_reset)
        zoom_bar.addWidget(btn_zoom_out)
        zoom_bar.addWidget(btn_reset)
        zoom_bar.addWidget(btn_zoom_in)
        zoom_bar.addStretch()
        right.addLayout(zoom_bar)

        self.result_label = QLabel("Result appears here")
        self.result_label.setStyleSheet("background:#000;border:6px solid #ff9500;")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setMinimumSize(800, 600)
        right.addWidget(self.result_label, 1)
        main.addLayout(right)

    def pick(self, typ):
        p,_ = QFileDialog.getOpenFileName(self,"Open Image","", "Images (*.png *.jpg *.jpeg *.tiff)")
        if p:
            pix = QPixmap(p).scaled(560,560,Qt.AspectRatioMode.KeepAspectRatio)
            if typ=="t": self.tp=p; self.l1.setPixmap(pix)
            else:        self.rp=p; self.l2.setPixmap(pix)

    def generate(self):
        if not self.tp or not self.rp:
            QMessageBox.warning(self,"","Pick both photos first!"); return
        self.btn_gen.setEnabled(False); self.btn_gen.setText("Working…")
        self.worker = Worker(self.tp, self.rp, self.slider.value(), self.cb.isChecked())
        self.worker.finished.connect(self.done)
        self.worker.start()

    def done(self, data):
        if isinstance(data,str):
            QMessageBox.critical(self,"Error",data)
        else:
            qimg = QImage(data.tobytes(), data.width, data.height, data.width*3, QImage.Format.Format_RGB888)
            self.current_pixmap = QPixmap.fromImage(qimg)
            self.zoom_reset()  # show at 100% fit
            data.save("Evoto_Free_Result.jpg")
            QMessageBox.information(self,"SUCCESS","Saved as Evoto_Free_Result.jpg")
        self.btn_gen.setText("GENERATE"); self.btn_gen.setEnabled(True)

    def update_result(self):
        if not self.current_pixmap:
            return
        scaled = self.current_pixmap.scaled(
            self.result_label.size() * self.zoom_level,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.result_label.setPixmap(scaled)

    def zoom_in(self):
        self.zoom_level = min(5.0, self.zoom_level * 1.25)
        self.update_result()

    def zoom_out(self):
        self.zoom_level = max(0.2, self.zoom_level / 1.25)
        self.update_result()

    def zoom_reset(self):
        self.zoom_level = 1.0
        self.update_result()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = EvotoFree()
    win.show()
    sys.exit(app.exec())