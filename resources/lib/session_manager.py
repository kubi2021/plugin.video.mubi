import random
import requests
import re
import xbmc

class SessionManager:
    def __init__(self, plugin):
        self.plugin = plugin
        self.device_id = self.plugin.getSetting('deviceID') or self.generate_device_id()
        self.client_country = self.plugin.getSetting('client_country') or self.get_client_country()
        self.token = self.plugin.getSetting('token')
        self.is_logged_in = bool(self.token)

    def set_logged_in(self, token):
        self.token = token
        self.is_logged_in = True
        self.plugin.setSetting('token', token)
        self.plugin.setSettingBool('logged', True)

    def set_logged_out(self):
        self.token = None
        self.is_logged_in = False
        self.plugin.setSetting('token', '')
        self.plugin.setSettingBool('logged', False)

    def generate_device_id(self):
        device_id = f"{self.code_gen(8)}-{self.code_gen(4)}-{self.code_gen(4)}-{self.code_gen(4)}-{self.code_gen(12)}"
        self.plugin.setSetting('deviceID', device_id)
        return device_id

    def code_gen(self, length):
        base = '0123456789abcdef'
        return ''.join(random.choice(base) for _ in range(length))

    def get_client_country(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = 'https://mubi.com/'
        try:
            resp = requests.get(url, headers=headers)
            country = re.findall(r'"Client-Country":"([^"]+?)"', resp.text)
            cli_country = country[0] if country else 'CH'
            self.plugin.setSetting('client_country', cli_country)
            return cli_country
        except Exception as e:
            xbmc.log(f"Failed to get client country: {str(e)}", xbmc.LOGERROR)
            return 'CH'