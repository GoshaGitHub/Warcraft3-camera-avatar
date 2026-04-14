import sys
import ctypes
from engine import AvatarEngine
from ui import AvatarUI

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    engine = AvatarEngine()
    
    app = AvatarUI(engine)
    app.mainloop()