from configparser import ConfigParser
import os


def get_config():
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_path, "config.ini")
    parser = ConfigParser()
    parser.read([config_path])
    return parser['config']

def mount_module():
    os.system('modprobe w1-gpio') 
    os.system('modprobe w1-therm')