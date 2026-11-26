def format_hotkey(keysym, state):
    key = keysym.casefold()
    if key in {
        "alt_l",
        "alt_r",
        "control_l",
        "control_r",
        "shift_l",
        "shift_r",
        "meta_l",
        "meta_r",
        "super_l",
        "super_r",
    }:
        return None

    modifiers = []
    if state & 0x4:
        modifiers.append("ctrl")
    if state & 0x8:
        modifiers.append("alt")
    if state & 0x1:
        modifiers.append("shift")

    key = {
        "backspace": "backspace",
        "escape": "esc",
        "return": "enter",
        "prior": "page up",
        "next": "page down",
    }.get(key, key)
    return "+".join([*modifiers, key])


def configure_hotkeys(config, config_path, save_config, parent=None):
    import tkinter as tk
    from tkinter import messagebox, ttk

    from protocols import PROTOCOLS

    try:
        root = tk.Toplevel(parent) if parent else tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError(f"Could not open hotkey settings: {exc}") from exc

    root.title("Tactical Ops Console - Hotkey Settings")
    root.resizable(False, False)
    root.minsize(540, 500)
    if parent:
        root.transient(parent)
        root.grab_set()

    hotkeys = config.setdefault("hotkeys", {})
    original_hotkeys = hotkeys.copy()
    saved = False
    values = {}

    ttk.Label(
        root,
        text="Click Set, then press a key or key combination.",
        padding=(12, 12, 12, 2),
    ).grid(row=0, column=0, columnspan=3, sticky="w")
    ttk.Label(
        root,
        text="Use Ctrl, Alt, or Shift with a key to avoid accidental activation.",
        padding=(12, 0, 12, 10),
    ).grid(row=1, column=0, columnspan=3, sticky="w")

    ttk.Label(root, text="Protocol", padding=6).grid(row=2, column=0, sticky="w")
    ttk.Label(root, text="Current shortcut", padding=6).grid(row=2, column=1, sticky="w")

    def add_row(row, code, name):
        value = tk.StringVar(value=hotkeys.get(code, ""))
        values[code] = value
        ttk.Label(root, text=name, padding=(12, 4)).grid(row=row, column=0, sticky="w")
        ttk.Label(root, textvariable=value, width=22, padding=4).grid(row=row, column=1, sticky="w")

        def capture():
            dialog = tk.Toplevel(root)
            dialog.title("Set shortcut")
            dialog.resizable(False, False)
            ttk.Label(
                dialog,
                text="Press the shortcut you want to use.",
                padding=20,
            ).pack()
            dialog.transient(root)
            dialog.grab_set()
            dialog.focus_force()

            def on_key(event):
                if event.keysym == "Escape":
                    dialog.destroy()
                    return "break"
                shortcut = format_hotkey(event.keysym, event.state)
                if shortcut is not None:
                    hotkeys[code] = shortcut
                    value.set(shortcut)
                    dialog.destroy()
                return "break"

            dialog.bind("<KeyPress>", on_key)
            dialog.bind("<Escape>", lambda _: dialog.destroy())

        def clear():
            hotkeys[code] = ""
            value.set("")

        ttk.Button(root, text="Set", command=capture, width=8).grid(row=row, column=2, padx=(0, 12))
        ttk.Button(root, text="Clear", command=clear, width=8).grid(row=row, column=3, padx=(0, 12))

    for row, protocol in enumerate(PROTOCOLS, start=3):
        add_row(row, protocol.code, protocol.name)
    add_row(len(PROTOCOLS) + 3, "TEST", "Toggle test mode")

    def cancel():
        hotkeys.clear()
        hotkeys.update(original_hotkeys)
        root.destroy()

    def save_and_close():
        configured = [value.strip().casefold() for value in hotkeys.values() if value.strip()]
        duplicates = sorted({value for value in configured if configured.count(value) > 1})
        if duplicates:
            messagebox.showerror(
                "Duplicate shortcuts",
                f"Each action needs a unique shortcut. Duplicate: {', '.join(duplicates)}",
                parent=root,
            )
            return
        try:
            save_config(config, config_path)
        except OSError as exc:
            messagebox.showerror("Could not save settings", str(exc), parent=root)
            return
        nonlocal saved
        saved = True
        root.destroy()

    buttons = ttk.Frame(root, padding=12)
    buttons.grid(row=len(PROTOCOLS) + 4, column=0, columnspan=4, sticky="e")
    ttk.Button(buttons, text="Cancel", command=cancel).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Save and apply", command=save_and_close).pack(side="right")
    root.protocol("WM_DELETE_WINDOW", cancel)
    if parent:
        parent.wait_window(root)
    else:
        root.mainloop()
    return saved
