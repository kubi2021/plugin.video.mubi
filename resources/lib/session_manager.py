import random
import xbmc

class SessionManager:
    """
    Manages the session for the Mubi plugin, including login status, device ID, and client country.
    """

    def __init__(self, plugin):
        """
        Initialize the session manager.

        :param plugin: Reference to the plugin object for accessing settings.
        """
        self.plugin = plugin
        self.device_id = self.get_or_generate_device_id()
        self.client_country = self._get_plugin_setting('client_country')
        self.token = self._get_plugin_setting('token')
        self.is_logged_in = bool(self.token)

    def get_or_generate_device_id(self) -> str:
        """
        Retrieve the device ID from settings or generate a new one if not present.

        :return: The device ID.
        """
        try:
            device_id = self._get_plugin_setting('deviceID')
            if not device_id:
                device_id = self.generate_device_id()
                self.plugin.setSetting('deviceID', device_id)
                xbmc.log(f"Generated new device ID: {device_id}", xbmc.LOGDEBUG)
            return device_id
        except Exception as e:
            xbmc.log(f"Error retrieving or generating device ID: {e}", xbmc.LOGERROR)
            return ''

    def generate_device_id(self) -> str:
        """
        Generates a new device ID in UUID format.

        :return: A newly generated device ID.
        """
        try:
            return f"{self._code_gen(8)}-{self._code_gen(4)}-{self._code_gen(4)}-{self._code_gen(4)}-{self._code_gen(12)}"
        except Exception as e:
            xbmc.log(f"Error generating device ID: {e}", xbmc.LOGERROR)
            return ''

    def _code_gen(self, length: int) -> str:
        """
        Generates a random string of hexadecimal characters.

        :param length: Length of the string to generate.
        :return: Randomly generated hexadecimal string.
        """
        try:
            base = '0123456789abcdef'
            return ''.join(random.choice(base) for _ in range(length))
        except Exception as e:
            xbmc.log(f"Error generating random code: {e}", xbmc.LOGERROR)
            return ''

    def set_logged_in(self, token: str):
        """
        Set the logged-in state and save the token to settings.

        :param token: Authentication token.
        """
        try:
            self.token = token
            self.is_logged_in = True
            self.plugin.setSetting('token', token)
            self.plugin.setSettingBool('logged', True)
            xbmc.log("User logged in successfully.", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Error setting logged-in status: {e}", xbmc.LOGERROR)

    def set_logged_out(self):
        """
        Set the logged-out state and clear the token from settings.
        """
        try:
            self.token = None
            self.is_logged_in = False
            self.plugin.setSetting('token', '')
            self.plugin.setSettingBool('logged', False)
            xbmc.log("User logged out successfully.", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Error setting logged-out status: {e}", xbmc.LOGERROR)

    def set_client_country(self, client_country: str):
        """
        Set the client's country and save it to settings.

        :param client_country: The country code of the client.
        """
        try:
            self.client_country = client_country
            self.plugin.setSetting('client_country', client_country)
            xbmc.log(f"Client country set to {client_country}.", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Error setting client country: {e}", xbmc.LOGERROR)

    def _get_plugin_setting(self, setting_key: str) -> str:
        """
        Retrieve a plugin setting with error handling.

        :param setting_key: The key of the setting to retrieve.
        :return: The value of the setting or an empty string if not found.
        """
        try:
            return self.plugin.getSetting(setting_key)
        except Exception as e:
            xbmc.log(f"Error retrieving plugin setting '{setting_key}': {e}", xbmc.LOGERROR)
            return ''
