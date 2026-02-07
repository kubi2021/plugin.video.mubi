import threading
import socket
import os
import xbmcvfs
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer

class LocalServer:
    """
    A simple threaded HTTP server to serve files from Kodi's temp directory.
    This bypasses inputstream.adaptive's inability to read local files on some platforms.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.server = None
        self.thread = None
        self.port = 0
        self.root_dir = xbmcvfs.translatePath("special://temp/")

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = LocalServer()
        return cls._instance

    def start(self):
        """Starts the server if not already running."""
        with self._lock:
            if self.server:
                return

            class Handler(SimpleHTTPRequestHandler):
                def __init__(handler_self, *args, **kwargs):
                    # Set the directory to serve from
                    super().__init__(*args, directory=self.root_dir, **kwargs)

                def log_message(self, format, *args):
                    # Suppress default logging to stderr
                    pass

            # Create server on ephemeral port
            self.server = ThreadingTCPServer(('127.0.0.1', 0), Handler)
            self.port = self.server.server_address[1]
            
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()

    def get_url(self, file_path):
        """
        Returns a localhost URL for the given file path.
        Use special://temp/filename or absolute path.
        """
        self.start()
        
        # We only serve from temp dir, so extract filename
        filename = os.path.basename(file_path)
        return f"http://127.0.0.1:{self.port}/{filename}"

    def is_healthy(self):
        """
        Tests if the LocalServer is working by making a quick HTTP request.
        Returns True if server responds, False otherwise.
        
        This catches issues like Linux ABI mismatches that cause crashes
        when switching between localhost and remote CDN contexts.
        """
        if not self.server:
            return False
        
        try:
            import urllib.request
            # Quick timeout test - just check if server responds
            test_url = f"http://127.0.0.1:{self.port}/"
            req = urllib.request.Request(test_url, method='HEAD')
            with urllib.request.urlopen(req, timeout=2) as response:
                # Any response (even 404) means server is working
                return True
        except Exception:
            # Connection refused, timeout, or crash = not healthy
            return False

    def stop(self):
        """Stops the server."""
        with self._lock:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
                self.thread = None
