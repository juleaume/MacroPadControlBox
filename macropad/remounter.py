import storage

storage.remount("/", readonly=False)
with open("boot.py", "a") as b:
    b.write("\nsupervisor.runtime.autoreload = True\n")
    b.write("\nusb_cdc.enable(data=True, console=True)\n")
