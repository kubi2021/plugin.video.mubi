import random

class SessionManager:
    def __init__(self, plugin):
        self.plugin = plugin
        self.device_id = self.get_or_generate_device_id()
        self.client_country = self.plugin.getSetting('client_country')
        self.token = self.plugin.getSetting('token')
        self.is_logged_in = bool(self.token)

    def get_or_generate_device_id(self):
        """
        Get the device ID from settings, or generate a new one if it doesn't exist.
        """
        device_id = self.plugin.getSetting('deviceID')
        if not device_id:
            device_id = self.generate_device_id()
            self.plugin.setSetting('deviceID', device_id)
        return device_id

    def generate_device_id(self):
        """
        Generates a unique device ID in a standard UUID-like format.

        :return: A generated device ID.
        """
        return f"{self.code_gen(8)}-{self.code_gen(4)}-{self.code_gen(4)}-{self.code_gen(4)}-{self.code_gen(12)}"

    def code_gen(self, length):
        """
        Generates a random string of hexadecimal characters.

        :param length: The length of the string to generate.
        :return: Randomly generated hexadecimal string.
        """
        base = '0123456789abcdef'
        return ''.join(random.choice(base) for _ in range(length))

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

    def set_client_country(self, client_country):
        self.client_country = client_country
        self.plugin.setSetting('client_country', client_country)

