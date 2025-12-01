import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PIL import Image
import numpy as np

# Very small, ultra-stable color transfer function (no external color_matcher needed)
def simple_color_transfer(target, source):
    target = np.array(target, dtype=np.float64)
    source = np.array(source, dtype=np.float64)
    
    for i in range(3):  # R,G,B channels
        t_mean, t_std = target[:,:,i].mean(), target[:,:,i].std()
        s_mean, s_std = source[:,:,i].mean(), source[:,:,i].std()
        target[:,:,i] = (target[:,:,i] - t_mean) * (s_std / (t_std + 1e-6)) + s_mean
    
    target = np.clip(target, 0, 255).astype(np.uint8)
    return Image.fromarray(target)

class Worker(QThread):
    finished = pyqtSignal(object)   # PIL Image or error string

    def __init__(self, content_path, style_path):
        super().__init__()
        self.c = content_path
        self.s = style_path

    def run(self):
        try:
            content = Image.open(self.c).convert("RGB")
            style   = Image.open(self.s).convert("RGB")
            result  = simple_color_transfer(content, style)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Free Evoto Clone – 100% WORKING")
        self.setGeometry(100,100,1250,750)
        central = QWidget(); self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Left side
        left = QVBoxLayout()
        self.lbl1 = QLabel("Click → YOUR photo"); self.lbl1.setStyleSheet("border:3px dashed #3498db; background:#f0f8ff; font-size:18px;"); self.lbl1.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lbl1.setMinimumHeight(320)
        self.lbl1.mousePressEvent = lambda e: self.pick("content")
        self.lbl2 = QLabel("Click → REFERENCE photo"); self.lbl2.setStyleSheet("border:3px dashed #e74c3c; background:#fff0f0; font-size:18px;"); self.lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lbl2.setMinimumHeight(320)
        self.lbl2.mousePressEvent = lambda e: self.pick("style")
        left.addWidget(self.lbl1); left.addWidget(self.lbl2); layout.addLayout(left)

        # Right side
        right = QVBoxLayout()
        right.addWidget(QLabel("<h2>Free Evoto Clone</h2>"))
        self.btn = QPushButton("GENERATE NOW (instant)"); self.btn.clicked.connect(self.start); self.btn.setStyleSheet("font-size:22px;padding:18px;background:#27ae60;color:white;")
        right.addWidget(self.btn)
        self.res = QLabel("Result appears here"); self.res.setStyleSheet("border:4px solid #2c3e50;background:#34495e;"); self.res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.res); layout.addLayout(right)

        self.cp = self.sp = None

    def pick(self, t):
        p,_ = QFileDialog.getOpenFileName(self,"Open","", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if p:
            pix = QPixmap(p).scaled(500,500,Qt.AspectRatioMode.KeepAspectRatio)
            if t=="content": self.cp=p; self.lbl1.setPixmap(pix); self.lbl1.setText("")
            else:            self.sp=p; self.lbl2.setPixmap(pix); self.lbl2.setText("")

    def start(self):
        if not self.cp or not self.sp:
            QMessageBox.warning(self,"","Pick both photos first!"); return
        self.btn.setEnabled(False); self.btn.setText("Working…")
        self.w = Worker(self.cp, self.sp)
        self.w.finished.connect(self.done)
        self.w.start()

    def done(self, data):
        if isinstance(data, str):
            QMessageBox.critical(self,"Error",data)
        else:
            q = QImage(data.tobytes(), data.width, data.height, data.width*3, QImage.Format.Format_RGB888)
            self.res.setPixmap(QPixmap.fromImage(q).scaled(800,800,Qt.AspectRatioMode.KeepAspectRatio))
            data.save("Evoto_Free_Result.jpg")
            QMessageBox.information(self,"DONE!","Saved as Evoto_Free_Result.jpg")
        self.btn.setText("GENERATE NOW (instant)"); self.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())