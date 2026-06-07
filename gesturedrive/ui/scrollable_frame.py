import tkinter as tk


class ScrollableFrame(tk.Frame):
    """A ``tk.Frame`` that scrolls its contents vertically via a Canvas."""

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)

        self.content = tk.Frame(canvas)
        self.content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        self.window_id = canvas.create_window((0, 0), window=self.content, anchor="nw")

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self.window_id, width=e.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"
        ))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas
