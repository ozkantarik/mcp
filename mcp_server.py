import http.server
import socketserver
import json
import datetime
import requests

PORT = 8080
# Switched to the more reliable Binance public API endpoint
API_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

class LiveDataHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            market_data_content = ""
            try:
                response = requests.get(API_URL, timeout=5)
                response.raise_for_status()
                
                # Adapted parsing for Binance API response: {"symbol":"BTCUSDT","price":"..."}
                api_data = response.json()
                price = float(api_data['price'])
                
                market_data_content = f"Live Bitcoin (BTC) Price: ${price:,.2f} (from Binance)"

            except requests.exceptions.RequestException as e:
                market_data_content = f"ERROR: Could not fetch live market data. Network error: {e}"
            except (KeyError, TypeError, ValueError) as e:
                market_data_content = f"ERROR: Could not parse API response. Invalid data format: {e}"

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            response_data = {
                "context": [
                    {
                        "title": "System Time",
                        # Fixed the DeprecationWarning by using timezone-aware UTC datetime
                        "content": f"{datetime.datetime.now(datetime.timezone.utc).isoformat()}"
                    },
                    {
                        "title": "Live BTC Market Data",
                        "content": market_data_content
                    }
                ]
            }

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")


with socketserver.TCPServer(("", PORT), LiveDataHttpRequestHandler) as httpd:
    print(f"Live Market Data MCP server starting at port {PORT}")
    print(f"Fetching data from: {API_URL}")
    httpd.serve_forever()