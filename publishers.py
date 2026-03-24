import requests
import base64

WP_URL = "https://felsefemiz.net/wp-json/wp/v2/posts"
WP_USER = "serezart"
WP_APP_PASS = "TBTJ w0hn 9Pz7 FyIa A6py xj6O"

def send_to_wordpress(title, content):
    credentials = f"{WP_USER}:{WP_APP_PASS}"
    token = base64.b64encode(credentials.encode()).decode()
    headers = {'Authorization': f'Basic {token}', 'Content-Type': 'application/json'}
    payload = {'title': title, 'content': content, 'status': 'publish'}
    try:
        response = requests.post(WP_URL, json=payload, headers=headers)
        return response.status_code == 201, response.text
    except Exception as e:
        return False, str(e)
