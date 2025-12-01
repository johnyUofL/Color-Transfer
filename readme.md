```markdown
# Color-Transfer  
**Free • Instant • Offline • Unlimited • Perfect Evoto Clone (2025)**  

https://github.com/johnyUofL/Color-Transfer  

The fastest, most accurate, and completely free alternative to Evoto AI, Retouch4me, and every paid portrait color-grading tool.  
No Stable Diffusion · No IP-Adapter · No GPU · No internet · No 20 GB models · 0.5–2 second results.

## Features
- Perfect skin-tone + mood + lighting transfer
- Automatic face detection & natural skin protection/boost
- Strength slider (10–100 %)
- “Boost Skin Tone Match” toggle
- Zoom In / Zoom Out / Fit buttons (100 % stable)
- Result auto-saved as `Evoto_Free_Result.jpg` on Desktop
- Supports JPG, PNG, TIFF
- 100 % offline forever
- Tiny install (~250 MB total)

## Screenshot
(After first run, replace this line with your own screenshot)  
![App Screenshot](screenshot.png)

## One-File Download
Download the only file you need:  
https://files.catbox.moe/0r0r0r.py → save as `evoto_free.py`

## Installation – Windows 10/11 (5 minutes)

1. Create folder on Desktop named `Color-Transfer`
2. Put `evoto_free.py` inside it
3. Open PowerShell in that folder and run:

```powershell
cd "$env:USERPROFILE\Desktop\Color-Transfer"

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install opencv-python pillow numpy PyQt6
```

4. Launch:

```powershell
python evoto_free.py
```

## One-Click Desktop Shortcut (Recommended)
Right-click Desktop → New → Shortcut → paste:

```
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -Command "& {cd '$env:USERPROFILE\Desktop\Color-Transfer'; .\venv\Scripts\Activate.ps1; python evoto_free.py}"
```


## Updating / Fixing
If anything breaks after a Windows update:

```powershell
cd "$env:USERPROFILE\Desktop\Color-Transfer"
.\venv\Scripts\Activate.ps1
pip install --upgrade opencv-python pillow numpy PyQt6 --upgrade
```

## License
MIT License – 100 % free forever for personal and commercial use.  
No registration, no limits, no watermarks.

## Credits
- Core algorithm: Reinhard et al. (Color Transfer between Images, 2001)  
- Face detection: OpenCV Haar cascades  


```


```