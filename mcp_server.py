import http.server
import socketserver
import json
import datetime

PORT = 8080
MARKET_DATA_FILE = "market_conditions.txt"

class CombinedHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            try:
                with open(MARKET_DATA_FILE, "r") as f:
                    market_conditions = f.read().strip()
            except FileNotFoundError:
                market_conditions = "ERROR: Market data file not found."
            except Exception as e:
                market_conditions = f"ERROR: Could not read market data: {e}"

            response_data = {
                "context": [
                    {
                        "title": "System Status",
                        "content": f"The current time is {datetime.datetime.utcnow().isoformat()}"
                    },
                    {
                        "title": "Live Market Conditions",
                        "content": market_conditions
                    }
                ]
            }

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")


with socketserver.TCPServer(("", PORT), CombinedHttpRequestHandler) as httpd:
    print("MCP server starting at port", PORT)
    httpd.serve_forever()