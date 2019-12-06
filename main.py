"""Privacy Manager add-on for Mozilla WebThings Gateway."""

from os import path
import functools
import gateway_addon
import signal
import sys
import time

sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

#from pkg.power_settings import PowerSettingsAdapter  # noqa
from pkg.privacy_manager import PrivacyManagerAPIHandler  # noqa



_HANDLER = None

print = functools.partial(print, flush=True)


def cleanup(signum, frame):
    """Clean up any resources before exiting."""
    if _HANDLER is not None:
        _HANDLER.close_proxy()

    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    #_HANDLER = PowerSettingsAdapter(verbose=True)
    _HANDLER = PrivacyManagerAPIHandler(verbose=True)
    

    # Wait until the proxy stops running, indicating that the gateway shut us
    # down.
    while _HANDLER.proxy_running():
        time.sleep(2)