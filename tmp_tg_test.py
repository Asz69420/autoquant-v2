import urllib.request
import urllib.parse
import json

# Step 1
token = ''
for l in open(r'C:\Users\Clamps\.openclaw\workspace\.env', encoding='utf-8'):
    if 'TELEGRAM_BOT_TOKEN' in l:
        token = l.strip().split('=', 1)[1].strip().strip('"')
        print(f'Token found: {token[:10]}...{token[-5:]}')
        print(f'Token length: {len(token)}')
        break

# Step 2
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = urllib.parse.urlencode({
    'chat_id': '1801759510',
    'text': 'AutoQuant test from raw API call',
    'parse_mode': 'HTML'
}).encode()

try:
    resp = urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
    print(json.loads(resp.read().decode('utf-8')))
except Exception as e:
    print(f'ERROR: {e}')
