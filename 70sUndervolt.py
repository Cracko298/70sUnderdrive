import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
from xml.dom import minidom

# This is the SaveGame decryption key for the XOR Cipher they used.
KEY = b"PLEASE DO NOT HACK THIS FOR A WHILE. WE REALLY WANT TO EARN A BIT."
REQUIRED_TAG = "m_isMPH"

def xor_data(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def try_decode_xml(data: bytes) -> str:
    encodings = ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]
    for enc in encodings:
        try:
            text = data.decode(enc)
            if "<" in text and ">" in text:
                return text
        except UnicodeDecodeError:
            pass
    raise ValueError("Could not decode data as XML text.")

def pretty_xml(element: ET.Element) -> str:
    rough_string = ET.tostring(element, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def validate_80s_overdrive_save(xml_text: str) -> ET.Element:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"XML parse failed: {e}") from e

    if REQUIRED_TAG not in xml_text:
        raise ValueError(
            f"This SaveGame does not appear to be a valid 80s Overdrive Save. "
            f"Required tag '{REQUIRED_TAG}' was not found."
        )

    return root

class XmlSaveEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("70s Undervolt - An 80s Overdrive Save Editor")
        self.root.geometry("1100x700")
        self.root.minsize(980, 620)

        self.file_path = None
        self.tree_root = None
        self.item_to_element = {}
        self.use_xor_on_save = True
        self.loaded_format_name = None

        self.colors = {
            "bg_top": "#14001f",
            "bg_mid": "#4a0d67",
            "bg_bottom": "#0b2a6f",
            "panel": "#0b1020",
            "panel_2": "#101735",
            "text": "#e8f7ff",
            "cyan": "#00f0ff",
            "pink": "#ff3cac",
            "gold": "#ffbf4d",
            "entry_bg": "#09101e",
            "list_bg": "#0a1022",
        }

        self.configure_styles()
        self.build_ui()

        self.root.bind("<Configure>", self.on_root_resize)
        self.root.after(50, self.redraw_background)

    def configure_styles(self):
        self.root.configure(bg=self.colors["panel"])

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Synth.Treeview",
            background=self.colors["list_bg"],
            foreground=self.colors["cyan"],
            fieldbackground=self.colors["list_bg"],
            borderwidth=1,
            rowheight=24,
            font=("Consolas", 10),
        )
        style.map(
            "Synth.Treeview",
            background=[("selected", self.colors["pink"])],
            foreground=[("selected", "#000000")],
        )
        style.configure(
            "Synth.Treeview.Heading",
            background=self.colors["panel_2"],
            foreground=self.colors["gold"],
            relief="flat",
            font=("Consolas", 10, "bold"),
        )
        style.configure(
            "Vertical.TScrollbar",
            troughcolor=self.colors["panel"],
            background=self.colors["pink"],
            arrowcolor=self.colors["cyan"],
            bordercolor=self.colors["panel"],
            lightcolor=self.colors["panel_2"],
            darkcolor=self.colors["panel_2"],
        )
        style.configure(
            "Horizontal.TScrollbar",
            troughcolor=self.colors["panel"],
            background=self.colors["pink"],
            arrowcolor=self.colors["cyan"],
            bordercolor=self.colors["panel"],
            lightcolor=self.colors["panel_2"],
            darkcolor=self.colors["panel_2"],
        )
        style.configure(
            "TPanedwindow",
            background=self.colors["panel"],
            sashthickness=6,
        )

    def style_frame(self, parent, **kwargs):
        defaults = {"bg": self.colors["panel"], "highlightthickness": 1, "highlightbackground": self.colors["cyan"]}
        defaults.update(kwargs)
        return tk.Frame(parent, **defaults)

    def style_label(self, parent, text="", fg=None, bg=None, font=None, **kwargs):
        return tk.Label(
            parent,
            text=text,
            fg=fg or self.colors["text"],
            bg=bg or self.colors["panel"],
            font=font or ("Consolas", 10),
            **kwargs,
        )

    def neon_button(self, parent, text, command, accent=None):
        accent = accent or self.colors["pink"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.colors["panel_2"],
            fg=accent,
            activebackground=accent,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            highlightthickness=1,
            highlightbackground=accent,
            font=("Consolas", 10, "bold"),
            cursor="hand2",
        )

    def style_entry(self, parent, textvariable=None, width=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=self.colors["entry_bg"],
            fg=self.colors["cyan"],
            insertbackground=self.colors["pink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["pink"],
            font=("Consolas", 10),
        )

    def style_text(self, parent, **kwargs):
        return tk.Text(
            parent,
            bg=self.colors["entry_bg"],
            fg=self.colors["cyan"],
            insertbackground=self.colors["pink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["pink"],
            font=("Consolas", 10),
            **kwargs,
        )

    def build_ui(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.outer_frame = tk.Frame(self.canvas, bg="#000000", highlightthickness=0)
        self.canvas_window = self.canvas.create_window(0, 0, anchor="nw", window=self.outer_frame)

        self.top_bar = self.style_frame(self.outer_frame, bg=self.colors["panel_2"])
        self.top_bar.pack(fill="x", padx=12, pady=12)

        self.neon_button(self.top_bar, "Open 80s Overdrive Save", self.open_file, self.colors["cyan"]).pack(side="left", padx=4, pady=4)
        self.neon_button(self.top_bar, "Save", self.save_file, self.colors["pink"]).pack(side="left", padx=4, pady=4)
        self.neon_button(self.top_bar, "Save As", self.save_file_as, self.colors["gold"]).pack(side="left", padx=4, pady=4)
        self.neon_button(self.top_bar, "Reload Tree", self.reload_tree, self.colors["cyan"]).pack(side="left", padx=4, pady=4)

        self.path_label = self.style_label(
            self.top_bar,
            text="[No SaveGame Loaded]",
            anchor="w",
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            font=("Consolas", 10, "bold"),
        )
        self.path_label.pack(side="left", fill="x", expand=True, padx=12)

        self.main_pane = tk.PanedWindow(
            self.outer_frame,
            sashrelief="raised",
            sashwidth=6,
            bg=self.colors["panel"],
            bd=0,
            relief="flat",
        )
        self.main_pane.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        left_frame = self.style_frame(self.main_pane)
        self.main_pane.add(left_frame, width=450)

        tree_header = self.style_label(left_frame, text="XML Tree", fg=self.colors["gold"], font=("Consolas", 11, "bold"))
        tree_header.pack(anchor="w", padx=8, pady=(8, 2))

        tree_container = tk.Frame(left_frame, bg=self.colors["panel"])
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.xml_tree = ttk.Treeview(tree_container, style="Synth.Treeview")
        self.xml_tree.pack(fill="both", expand=True, side="left")

        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.xml_tree.yview)
        tree_scroll.pack(fill="y", side="right")
        self.xml_tree.configure(yscrollcommand=tree_scroll.set)
        self.xml_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        right_frame = self.style_frame(self.main_pane)
        self.main_pane.add(right_frame)

        form_frame = self.style_frame(right_frame, bg=self.colors["panel_2"])
        form_frame.pack(fill="x", padx=8, pady=8)

        self.style_label(form_frame, text="Tag:", fg=self.colors["gold"], bg=self.colors["panel_2"], font=("Consolas", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.tag_var = tk.StringVar()
        self.tag_entry = self.style_entry(form_frame, textvariable=self.tag_var, width=50)
        self.tag_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=4)

        self.style_label(form_frame, text="Text:", fg=self.colors["gold"], bg=self.colors["panel_2"], font=("Consolas", 10, "bold")).grid(row=1, column=0, sticky="nw")
        self.text_box = self.style_text(form_frame, height=8, wrap="word")
        self.text_box.grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        form_frame.grid_columnconfigure(1, weight=1)

        attr_frame = tk.LabelFrame(
            right_frame,
            text="Attributes",
            bg=self.colors["panel_2"],
            fg=self.colors["gold"],
            font=("Consolas", 10, "bold"),
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["pink"],
        )
        attr_frame.pack(fill="both", expand=False, padx=8, pady=8)

        self.attr_list = tk.Listbox(
            attr_frame,
            height=10,
            bg=self.colors["list_bg"],
            fg=self.colors["cyan"],
            selectbackground=self.colors["pink"],
            selectforeground="#000000",
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["cyan"],
            font=("Consolas", 10),
        )
        self.attr_list.pack(fill="both", expand=True, side="left", padx=(6, 0), pady=6)
        self.attr_list.bind("<<ListboxSelect>>", self.on_attr_select)

        attr_scroll = ttk.Scrollbar(attr_frame, orient="vertical", command=self.attr_list.yview)
        attr_scroll.pack(fill="y", side="left", pady=6)
        self.attr_list.configure(yscrollcommand=attr_scroll.set)

        attr_edit_frame = tk.Frame(attr_frame, bg=self.colors["panel_2"])
        attr_edit_frame.pack(fill="both", expand=True, side="left", padx=10, pady=6)

        self.style_label(attr_edit_frame, text="Name:", fg=self.colors["gold"], bg=self.colors["panel_2"], font=("Consolas", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.attr_name_var = tk.StringVar()
        self.attr_name_entry = self.style_entry(attr_edit_frame, textvariable=self.attr_name_var)
        self.attr_name_entry.grid(row=0, column=1, sticky="ew", pady=3)

        self.style_label(attr_edit_frame, text="Value:", fg=self.colors["gold"], bg=self.colors["panel_2"], font=("Consolas", 10, "bold")).grid(row=1, column=0, sticky="w")
        self.attr_value_var = tk.StringVar()
        self.attr_value_entry = self.style_entry(attr_edit_frame, textvariable=self.attr_value_var)
        self.attr_value_entry.grid(row=1, column=1, sticky="ew", pady=3)

        self.neon_button(attr_edit_frame, "Update Attribute", self.update_attribute, self.colors["cyan"]).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=4
        )
        self.neon_button(attr_edit_frame, "Add Attribute", self.add_attribute, self.colors["gold"]).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=4
        )
        self.neon_button(attr_edit_frame, "Delete Attribute", self.delete_attribute, self.colors["pink"]).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=4
        )

        attr_edit_frame.grid_columnconfigure(1, weight=1)

        bottom_frame = self.style_frame(right_frame, bg=self.colors["panel_2"])
        bottom_frame.pack(fill="x", padx=8, pady=8)

        self.neon_button(
            bottom_frame,
            "Apply Changes To Selected Element",
            self.apply_element_changes,
            self.colors["pink"],
        ).pack(fill="x", padx=6, pady=6)

    def on_root_resize(self, event=None):
        if event is None or event.widget == self.root:
            self.canvas.itemconfigure(self.canvas_window, width=self.root.winfo_width(), height=self.root.winfo_height())
            self.redraw_background()

    def hex_to_rgb(self, color):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def blend(self, c1, c2, t):
        r1, g1, b1 = self.hex_to_rgb(c1)
        r2, g2, b2 = self.hex_to_rgb(c2)
        return self.rgb_to_hex((
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        ))

    def redraw_background(self):
        if not hasattr(self, "canvas"):
            return

        self.canvas.delete("bg")
        width = max(self.root.winfo_width(), 1)
        height = max(self.root.winfo_height(), 1)

        top = self.colors["bg_top"]
        mid = self.colors["bg_mid"]
        bottom = self.colors["bg_bottom"]

        split = max(height // 2, 1)
        for y in range(height):
            if y <= split:
                t = y / split
                color = self.blend(top, mid, t)
            else:
                t = (y - split) / max(height - split, 1)
                color = self.blend(mid, bottom, t)
            self.canvas.create_line(0, y, width, y, fill=color, tags="bg")

        # horizon glow
        glow_y = int(height * 0.66)
        for i in range(28):
            alpha_mix = i / 28.0
            color = self.blend(self.colors["pink"], self.colors["gold"], alpha_mix)
            self.canvas.create_line(0, glow_y + i, width, glow_y + i, fill=color, tags="bg")

        # retro scanlines
        for y in range(0, height, 4):
            self.canvas.create_line(0, y, width, y, fill="#0a0010", tags="bg", stipple="gray25")

        self.canvas.tag_lower("bg")
        self.canvas.tag_raise(self.canvas_window)

    def try_load_save_variants(self, raw_data: bytes):
        attempts = [
            ("PC/Steam", True, xor_data(raw_data, KEY)),
            ("Nintendo Switch", False, raw_data),
        ]

        errors = []
        not_80s_error = None

        for label, use_xor, candidate_data in attempts:
            try:
                xml_text = try_decode_xml(candidate_data)
                parsed_root = validate_80s_overdrive_save(xml_text)
                return parsed_root, use_xor, label
            except ValueError as e:
                error_text = f"{label}: {e}"
                errors.append(error_text)
                if REQUIRED_TAG in str(e):
                    not_80s_error = error_text
            except Exception as e:
                errors.append(f"{label}: {e}")

        if not_80s_error is not None:
            raise ValueError(not_80s_error)

        raise ValueError(
            "Failed to load save. Not a Valid 80s Overdrive SaveGame "
            "Did not produce or load.\n\n" + "\n".join(errors)
        )

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open Save",
            filetypes=[("Save files", "*.sav"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                raw_data = f.read()

            self.tree_root, self.use_xor_on_save, self.loaded_format_name = self.try_load_save_variants(raw_data)
            self.file_path = path
            suffix = " [PC/Steam SaveGame]" if self.use_xor_on_save else " [Nintendo Switch SaveGame]"
            self.path_label.config(text=path + suffix)
            self.reload_tree()
            messagebox.showinfo(
                "Success",
                f"Loaded 80s Overdrive save successfully.\nDetected format: {self.loaded_format_name}."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open/validate/parse file:\n{e}")

    def reload_tree(self):
        self.xml_tree.delete(*self.xml_tree.get_children())
        self.item_to_element.clear()

        if self.tree_root is None:
            return

        self.add_tree_node("", self.tree_root)

    def add_tree_node(self, parent_item, element):
        text_preview = (element.text or "").strip()
        if len(text_preview) > 30:
            text_preview = text_preview[:30] + "..."

        label = element.tag
        if text_preview:
            label += f" = {text_preview}"

        item_id = self.xml_tree.insert(parent_item, "end", text=label, open=True)
        self.item_to_element[item_id] = element

        for child in element:
            self.add_tree_node(item_id, child)

    def get_selected_element(self):
        selected = self.xml_tree.selection()
        if not selected:
            return None
        return self.item_to_element.get(selected[0])

    def on_tree_select(self, event=None):
        element = self.get_selected_element()
        if element is None:
            return

        self.tag_var.set(element.tag)
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", element.text if element.text is not None else "")

        self.refresh_attr_list(element)

    def refresh_attr_list(self, element):
        self.attr_list.delete(0, "end")
        for k, v in element.attrib.items():
            self.attr_list.insert("end", f"{k} = {v}")
        self.attr_name_var.set("")
        self.attr_value_var.set("")

    def on_attr_select(self, event=None):
        element = self.get_selected_element()
        if element is None:
            return

        selection = self.attr_list.curselection()
        if not selection:
            return

        index = selection[0]
        key = list(element.attrib.keys())[index]
        value = element.attrib[key]

        self.attr_name_var.set(key)
        self.attr_value_var.set(value)

    def apply_element_changes(self):
        element = self.get_selected_element()
        if element is None:
            messagebox.showwarning("No Selection", "Select an element first.")
            return

        new_tag = self.tag_var.get().strip()
        if not new_tag:
            messagebox.showwarning("Invalid Tag", "Tag name cannot be empty.")
            return

        element.tag = new_tag
        element.text = self.text_box.get("1.0", "end-1c")

        self.reload_tree()
        messagebox.showinfo("Updated", "Element changes applied.")

    def update_attribute(self):
        element = self.get_selected_element()
        if element is None:
            messagebox.showwarning("No Selection", "Select an element first.")
            return

        name = self.attr_name_var.get().strip()
        value = self.attr_value_var.get()

        if not name:
            messagebox.showwarning("Invalid Attribute", "Attribute name cannot be empty.")
            return

        element.attrib[name] = value
        self.refresh_attr_list(element)

    def add_attribute(self):
        self.update_attribute()

    def delete_attribute(self):
        element = self.get_selected_element()
        if element is None:
            messagebox.showwarning("No Selection", "Select an element first.")
            return

        name = self.attr_name_var.get().strip()
        if not name:
            messagebox.showwarning("Invalid Attribute", "Select or enter an attribute name.")
            return

        if name in element.attrib:
            del element.attrib[name]
            self.refresh_attr_list(element)
        else:
            messagebox.showwarning("Missing Attribute", f"Attribute '{name}' not found.")

    def build_output_bytes(self) -> bytes:
        if self.tree_root is None:
            raise ValueError("No SaveGame loaded.")

        xml_text = pretty_xml(self.tree_root)

        if REQUIRED_TAG not in xml_text:
            raise ValueError(
                f"Refusing to save because required tag '{REQUIRED_TAG}' was not found."
            )

        xml_bytes = xml_text.encode("utf-8")
        if self.use_xor_on_save:
            return xor_data(xml_bytes, KEY)
        return xml_bytes

    def save_file(self):
        if self.file_path is None:
            self.save_file_as()
            return

        try:
            output_data = self.build_output_bytes()
            with open(self.file_path, "wb") as f:
                f.write(output_data)
            save_mode = "PC/Steam" if self.use_xor_on_save else "Nintendo Switch"
            messagebox.showinfo("Saved", f"Saved {save_mode} SaveGame back to:\n{self.file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save SaveGame:\n{e}")

    def save_file_as(self):
        if self.tree_root is None:
            messagebox.showwarning("No File", "No SaveGame file is loaded.")
            return

        path = filedialog.asksaveasfilename(
            title="Save File As",
            defaultextension=".sav",
            filetypes=[("Save Files", "*.sav"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            output_data = self.build_output_bytes()
            with open(path, "wb") as f:
                f.write(output_data)
            self.file_path = path
            suffix = " [PC/Steam SaveGame]" if self.use_xor_on_save else " [Nintendo Switch SaveGame]"
            self.path_label.config(text=path + suffix)
            save_mode = "PC/Steam" if self.use_xor_on_save else "Nintendo Switch"
            messagebox.showinfo("Saved", f"Saved {save_mode} SaveGame to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save SaveGame:\n{e}")

# Cracko298
if __name__ == "__main__":
    root = tk.Tk()
    app = XmlSaveEditor(root)
    root.mainloop()
