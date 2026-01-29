#!/usr/bin/env python3
import gi, os, threading, time
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

class FloatingFlasher(Gtk.Window):
    def __init__(self):
        super().__init__(title="Flasher")
        self.set_border_width(8)
        self.set_default_size(320, 160)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_resizable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box)

        hbox1 = Gtk.Box(spacing=6)
        self.iso_entry = Gtk.Entry()
        self.iso_entry.set_size_request(200, 25)
        iso_button = Gtk.Button(label="Select Image")
        iso_button.set_size_request(80, 25)
        iso_button.connect("clicked", self.select_iso)
        hbox1.pack_start(Gtk.Label(label="Image:"), False, False, 0)
        hbox1.pack_start(self.iso_entry, True, True, 0)
        hbox1.pack_start(iso_button, False, False, 0)
        box.pack_start(hbox1, False, False, 0)

        hbox2 = Gtk.Box(spacing=6)
        self.device_combo = Gtk.ComboBoxText()
        self.device_combo.set_size_request(200, 25)
        refresh_button = Gtk.Button(label="Refresh")
        refresh_button.set_size_request(80, 25)
        refresh_button.connect("clicked", lambda x: self.refresh_devices())
        hbox2.pack_start(Gtk.Label(label="USB Drive:"), False, False, 0)
        hbox2.pack_start(self.device_combo, True, True, 0)
        hbox2.pack_start(refresh_button, False, False, 0)
        box.pack_start(hbox2, False, False, 0)

        self.flash_button = Gtk.Button(label="Flash")
        self.flash_button.set_size_request(80, 25)
        self.flash_button.connect("clicked", self.confirm_flash)
        box.pack_start(self.flash_button, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_size_request(300, 25)
        box.pack_start(self.progress, False, False, 0)

        self.refresh_devices()

    def select_iso(self, widget):
        dialog = Gtk.FileChooserDialog(title="Select Image", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.iso_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def refresh_devices(self):
        self.device_combo.remove_all()
        try:
            for dev in os.listdir("/sys/block"):
                removable_path = f"/sys/block/{dev}/removable"
                if not os.path.exists(removable_path):
                    continue
                with open(removable_path) as f:
                    if f.read().strip() != "1":
                        continue
                if dev.startswith(("loop", "zram", "sr")):
                    continue
                if dev in ("sda", "nvme0n1"):
                    continue
                size_path = f"/sys/block/{dev}/size"
                with open(size_path) as f:
                    sectors = int(f.read().strip())
                size_gb = sectors * 512 / (1024 ** 3)
                self.device_combo.append_text(f"/dev/{dev} ({size_gb:.1f} GB)")
        except Exception as e:
            print("Error listing devices:", e)

    def confirm_flash(self, widget):
        iso = self.iso_entry.get_text()
        device_text = self.device_combo.get_active_text()
        if not iso or not device_text:
            self.update_progress(0.0, "Select an image and a USB drive")
            return
        device = device_text.split()[0]
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=f"Flash {iso} to {device}? THIS WILL ERASE IT!")
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        threading.Thread(target=self.flash_process, args=(iso, device), daemon=True).start()

    def flash_process(self, iso, device):
        iso_size = os.path.getsize(iso)
        bs = 4 * 1024 * 1024
        total_written = 0

        try:
            with open(iso, "rb") as f_iso, open(device, "wb") as f_dev:
                while True:
                    data = f_iso.read(bs)
                    if not data:
                        break
                    f_dev.write(data)
                    f_dev.flush()
                    total_written += len(data)
                    fraction = total_written / iso_size
                    GLib.idle_add(self.update_progress, fraction, f"Writing {fraction*100:.1f}%")
            GLib.idle_add(self.update_progress, 1.0, "Flashing Finished")
            time.sleep(1)

            total_verified = 0
            with open(iso, "rb") as f_iso, open(device, "rb") as f_dev:
                while True:
                    data_iso = f_iso.read(bs)
                    if not data_iso:
                        break
                    data_dev = f_dev.read(len(data_iso))
                    total_verified += len(data_iso)
                    fraction = total_verified / iso_size
                    GLib.idle_add(self.update_progress, fraction, f"Verifying {fraction*100:.1f}%")
            GLib.idle_add(self.update_progress, 1.0, "Verification Complete")
            time.sleep(1)

            GLib.idle_add(self.update_progress, 0.0, "Writing Finished")
            GLib.idle_add(self.show_popup, "Writing Finished!")
        except Exception as e:
            GLib.idle_add(self.update_progress, 0.0, f"Error: {e}")

    def show_popup(self, message):
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text=message)
        dialog.run()
        dialog.destroy()

    def update_progress(self, fraction, text):
        self.progress.set_fraction(fraction)
        self.progress.set_text(text)
        return False

if __name__ == "__main__":
    win = FloatingFlasher()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
