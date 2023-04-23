import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class NewJsonFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        new_file_path = event.src_path
        file_name, file_ext = os.path.splitext(os.path.basename(new_file_path))

        if file_ext == ".json":
            custom_function(new_file_path)


def custom_function(json_file_path):
    print(f"New JSON file added: {json_file_path}")
    # Your custom processing logic here


def watch_directory(path):
    event_handler = NewJsonFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    directory_to_watch = "trial"
    watch_directory(directory_to_watch)
