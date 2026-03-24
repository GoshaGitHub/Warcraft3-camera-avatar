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
    # 1. Проверяем права администратора (нужно для реестра)
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    # 2. Создаем "движок" (камера, звук)
    engine = AvatarEngine()
    
    # 3. Создаем и запускаем интерфейс, передав ему движок
    app = AvatarUI(engine)
    app.mainloop()