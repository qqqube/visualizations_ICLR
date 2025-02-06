""" utils.py """
import configparser


def _get_credentials(credentials_path):
    """
    Credentials INI file should look like:

    [BASIC]
    USERNAME = <username>
    PASSWORD = <password>
    """
    config = configparser.ConfigParser()
    config.read(credentials_path)
    return config["BASIC"]["USERNAME"], config["BASIC"]["PASSWORD"]
