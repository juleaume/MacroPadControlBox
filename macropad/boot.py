import usb_cdc
import supervisor

usb_cdc.enable(data=True, console=False)
supervisor.runtime.autoreload = False
