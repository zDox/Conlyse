import logging

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)
    interface = HubInterface()
    interface.set_proxy({
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080"
    })
    interface.api.set_certificate("burp_suite_certificate.pem")
    print(interface.register("fgdljehjggfojkgtesa", "tesdstdiffdjkhgfhf@gmail.com", "gjkhjhgjhdugoh"))
    """
    res= interface.register(username="eQVnARsGDSfdsfgfgwyfdfaC",
                       email="WODnGzzZpncXfdssgfgdfsdffFn@gmail.com",
                       password="dshfjshisafhjiios")
    """
