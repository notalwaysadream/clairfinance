#!/usr/bin/env python3
"""
Custom HTTP server for ClaireFinance Frontend with Cross-Origin-Opener-Policy support.
Required by Google Identity Services OAuth popup to prevent blank screen issues in modern browsers.
"""
import http.server
import socketserver
import sys
import os

PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
DIRECTORY = sys.argv[2] if len(sys.argv) > 2 else (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "frontend")

if not os.path.isabs(DIRECTORY):
    DIRECTORY = os.path.abspath(DIRECTORY)

class SecurityHeadersHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Critical for Google Identity Services OAuth popup communication
        self.send_header("Cross-Origin-Opener-Policy", "same-origin-allow-popups")
        self.send_header("Cross-Origin-Embedder-Policy", "unsafe-none")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, format, *args):
        # Silent for asset fetches, log only warnings/errors
        if len(args) > 1 and str(args[1]).startswith(('4', '5')):
            super().log_message(format, *args)

def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), SecurityHeadersHandler) as httpd:
        print(f"🎨 ClaireFinance Frontend serving from {DIRECTORY} on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    run()
