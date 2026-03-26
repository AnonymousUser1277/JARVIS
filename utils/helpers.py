"""
Helper utilities
"""
import subprocess
import sys
import os

def restart_program():
    import main
    main.IS_RESTARTING = True

    print("🔄 Restarting cleanly...")
    subprocess.Popen([sys.executable] + sys.argv)
    os._exit(0)
def shutdown(root=None, cleanup=None, icon=None):
    print("❌ Shutting down cleanly...")

    try:
        if icon:
            icon.visible = False
            icon.stop()
    except Exception as e:
        print("Tray stop error:", e)

    try:
        if cleanup:
            cleanup()
    except Exception as e:
        print("Cleanup error:", e)

    try:
        if root:
            root.destroy()
    except Exception as e:
        print("GUI destroy error:", e)

    os._exit(0)
def get_script_path():
    """Get current script path"""
    try:
        return os.path.abspath(__file__)
    except NameError:
        return os.path.abspath(sys.argv[0])