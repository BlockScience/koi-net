import socket
from logging import Logger

from ..config.loader import ConfigLoader
from ..config.full_node import FullNodeConfig
from .profile_monitor import ProfileMonitor


class PortManager:
    """Changes port if already in use by another process."""
    
    def __init__(
        self,
        log: Logger,
        config: FullNodeConfig,
        config_loader: ConfigLoader,
        profile_monitor: ProfileMonitor
    ):
        self.log = log
        self.config = config
        self.config_loader = config_loader
        self.profile_monitor = profile_monitor
        
    def start(self):
        self.acquire_port()
        
    def acquire_port(self):
        base_url_is_derived = self.config.koi_net.node_profile.base_url == self.config.server.url
        
        changed_port: bool = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            address = (self.config.server.host, self.config.server.port)
            while s.connect_ex(address) == 0:
                self.log.debug(f"Port {address[1]} in use")
                self.config.server.port += 1
                address = (address[0], self.config.server.port)
                changed_port = True
        
        self.log.debug(f"Acquired port {address[1]}")
        
        if base_url_is_derived and changed_port:
            self.log.debug("Updating node profile")
            self.config.koi_net.node_profile.base_url = self.config.server.url
            self.profile_monitor.process_profile()
        
        self.config_loader.save_to_yaml()