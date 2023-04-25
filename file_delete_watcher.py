import sys
import time
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

class FileDeletionHandler(FileSystemEventHandler):
    def on_deleted(self, event):
        if event.is_directory:
            print(f"Directory deleted: {event.src_path}")
        else:
            print(f"File deleted: {event.src_path}. Triggering warning.")

def main(directory_to_watch):
    event_handler = FileDeletionHandler()
    observer = PollingObserver()
    observer.schedule(event_handler, directory_to_watch, recursive=True)
    
    print(f"Starting to watch '{directory_to_watch}' for file deletions.")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory_to_watch = sys.argv[1]
        main(directory_to_watch)
    else:
        print("Usage: python file_deletion_watchdog.py <directory_to_watch>")
