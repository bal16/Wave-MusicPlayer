import customtkinter as ctk


class ActionFrame(ctk.CTkFrame):
    def __init__(self, master, on_add_callback, on_reset_callback, **kwargs):
        super().__init__(master, **kwargs)

        # Simpan fungsi callback yang dikirim dari Parent
        self.on_add = on_add_callback
        self.on_reset = on_reset_callback

        # Setup UI Tombol
        self.btn_add = ctk.CTkButton(self, text="Tambah", command=self.on_add)
        self.btn_add.pack(side="left", padx=10, pady=10)

        self.btn_reset = ctk.CTkButton(
            self, text="Reset", command=self.on_reset, fg_color="red"
        )
        self.btn_reset.pack(side="left", padx=10, pady=10)
