#!/usr/bin/env python3
"""SWYK entry point — launches the GUI."""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

def main():
    try:
        import tkinter
    except ImportError:
        print("ERROR: tkinter not found.")
        print("Install: sudo apt install python3-tk  (Debian/Ubuntu)")
        print("    or:  sudo dnf install python3-tkinter  (Fedora)")
        sys.exit(1)

    from gui.app import SwykApp
    app = SwykApp()
    app.run()

if __name__ == "__main__":
    main()
