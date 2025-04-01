import ctypes
import os
import platform

def take_photo(filename="photo.bmp"):  # Changed to .bmp
    try:
        print(f"Step 1: Current directory: {os.getcwd()}")
        print(f"Step 1: Python architecture: {platform.architecture()[0]}")

        dll_path = os.path.join(os.getcwd(), "camera_capture.dll")
        print(f"Step 2: DLL path: {dll_path}")
        if not os.path.exists(dll_path):
            raise FileNotFoundError("camera_capture.dll not found in the current directory")
        print("Step 2: DLL file exists")

        print("Step 3: Attempting to load DLL...")
        camera_dll = ctypes.CDLL(dll_path)
        print("Step 3: DLL loaded successfully")

        print("Step 4: Defining function signature...")
        capture_photo = camera_dll.capturePhoto
        capture_photo.argtypes = [ctypes.c_char_p]
        capture_photo.restype = ctypes.c_int
        print("Step 4: Function signature defined")

        print(f"Step 5: Preparing filename: {filename}")
        filename_bytes = filename.encode('utf-8')
        print(f"Step 5: Filename encoded to bytes: {filename_bytes}")

        print("Step 6: Calling capturePhoto function...")
        result = capture_photo(filename_bytes)
        print(f"Step 6: Function called, result: {result}")

        print("Step 7: Processing result...")
        if result == 0:
            print(f"Step 7: Photo saved as {filename}")
            if os.path.exists(filename):
                print(f"Step 7: File size: {os.path.getsize(filename)} bytes")
            else:
                print("Step 7: Warning: File was not created despite success return code")
        else:
            print(f"Step 7: Failed to capture photo (return code: {result})")

    except Exception as e:
        print(f"Error at current step: {str(e)}")

if __name__ == "__main__":
    print("Starting execution...")
    take_photo("photo.bmp")  # Changed to .bmp
    print("Execution completed.")