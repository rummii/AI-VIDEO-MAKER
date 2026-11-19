r"""
Maverick Edit Engine - minimalistic white GUI for the video pipeline.

Runs on Windows 11 with the Python 3 that already includes Tkinter:
    python tools\maverick_gui.py

Or double-click "Maverick Edit Engine.bat" in the project root.

Features:
- Open any shots JSON plan (defaults to tools/edits/rail_slide_full.shots.json)
- Timeline with each shot as a block, proportional to its display duration
- Drag a block's LEFT or RIGHT edge to trim a shot (start/end in source time)
- Select a shot to edit start/end/speed numerically, or delete it
- Keeps the music drop aligned with the money shot when you trim earlier shots
- Render through the same engine (build command) in a background thread
"""
import json, os, subprocess, sys, threading, queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "tools", "make_video.py")
DEFAULT_PLAN = os.path.join(ROOT, "tools", "edits", "rail_slide_full.shots.json")
OUT_DIR = os.path.join(ROOT, "output")
ACCENT = "#0a7d6b"
LIME = "#d0e000"

BG = "#ffffff"
PANEL = "#f7f8f9"
LINE = "#dfe3e6"
TXT = "#1b1f22"


def display_duration(s):
    if s.get("kind") in ("black", "noise"):
        return float(s.get("dur", 0.0))
    return (float(s["end"]) - float(s["start"])) / float(s.get("speed", 1.0))


def compute_total(shots):
    return sum(display_duration(s) for s in shots)


def money_start(shots):
    t = 0.0
    for s in shots:
        if "money" in str(s.get("note", "")).lower():
            return t
        t += display_duration(s)
    return None


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Maverick Edit Engine")
        self.root.geometry("1180x760")
        self.root.configure(bg=BG)

        self.doc = None
        self.plan_path = None
        self.selected = None
        self.segments = []          # (start_display, dur, index)
        self.scale = 8.0            # px per second
        self.drag = None            # (index, mode, press_x, orig_start, orig_end)
        self.q = queue.Queue()

        self._style()
        self._build_ui()
        self.load_plan(DEFAULT_PLAN)
        self.root.after(60, self._poll_queue)

    # ------------------------------------------------------------------ UI
    def _style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", background=BG, foreground=TXT, font=("Segoe UI", 10))
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, foreground=TXT)
        st.configure("Header.TLabel", background=BG, foreground=TXT,
                     font=("Segoe UI", 19, "bold"))
        st.configure("Sub.TLabel", background=BG, foreground="#667078",
                     font=("Segoe UI", 9))
        st.configure("TButton", background=PANEL, foreground=TXT,
                     borderwidth=1, focuscolor=ACCENT)
        st.configure("Accent.TButton", background=ACCENT, foreground="white",
                     borderwidth=0, font=("Segoe UI", 10, "bold"))
        st.configure("TEntry", fieldbackground=BG, borderwidth=1)
        st.configure("TCombobox", fieldbackground=BG)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(18, 12, 18, 8))
        top.pack(fill="x")
        ttk.Label(top, text="MAVERICK", style="Header.TLabel").pack(side="left")
        ttk.Label(top, text="  EDIT ENGINE", style="Sub.TLabel").pack(side="left", pady=(8, 0))

        bar = ttk.Frame(self.root, padding=(18, 4, 18, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="Open plan", command=self.open_plan).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Save plan", command=self.save_plan).pack(side="left", padx=(0, 18))

        ttk.Label(bar, text="Music:").pack(side="left")
        self.music_var = tk.StringVar(value="rail-slide")
        ttk.Entry(bar, textvariable=self.music_var, width=22).pack(side="left", padx=(4, 14))

        ttk.Label(bar, text="Format:").pack(side="left")
        self.format_var = tk.StringVar(value="9:16")
        ttk.Combobox(bar, textvariable=self.format_var, width=8, state="readonly",
                     values=["9:16", "16:9", "both", "16:9-4k", "9:16-4k"]).pack(side="left", padx=(4, 14))

        ttk.Label(bar, text="Output:").pack(side="left")
        self.out_var = tk.StringVar(value="rail_slide_full")
        ttk.Entry(bar, textvariable=self.out_var, width=20).pack(side="left", padx=(4, 14))

        ttk.Button(bar, text="RENDER", style="Accent.TButton",
                   command=self.render).pack(side="left")

        # timeline card
        card = tk.Frame(self.root, bg=BG, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="both", expand=True, padx=18, pady=6)
        hdr = tk.Frame(card, bg=BG)
        hdr.pack(fill="x", pady=(8, 2), padx=10)
        tk.Label(hdr, text="TIMELINE", bg=BG, fg="#667078",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.info_var = tk.StringVar(value="")
        tk.Label(hdr, textvariable=self.info_var, bg=BG, fg="#667078",
                 font=("Segoe UI", 9)).pack(side="right")

        canvas_wrap = tk.Frame(card, bg=BG)
        canvas_wrap.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas = tk.Canvas(canvas_wrap, bg=BG, highlightthickness=0, height=190)
        self.hscroll = ttk.Scrollbar(canvas_wrap, orient="horizontal",
                                     command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hscroll.set)
        self.hscroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        zoom = tk.Frame(card, bg=BG)
        zoom.pack(fill="x", padx=10, pady=(2, 8))
        tk.Label(zoom, text="Zoom", bg=BG, fg="#667078").pack(side="left")
        self.zoom_var = tk.DoubleVar(value=self.scale)
        ttk.Scale(zoom, from_=4, to=40, variable=self.zoom_var,
                  command=self.on_zoom, length=200).pack(side="left", padx=8)
        tk.Label(zoom, text="Drag a block edge to trim  •  Click a block to edit",
                 bg=BG, fg="#98a0a6").pack(side="left", padx=20)

        # detail editor
        det = tk.Frame(self.root, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        det.pack(fill="x", padx=18, pady=(6, 8))
        self.detail_var = tk.StringVar(value="Select a shot on the timeline")
        tk.Label(det, textvariable=self.detail_var, bg=PANEL, fg=TXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        row = tk.Frame(det, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 8))
        self.fields = {}
        for name in ("start", "end", "speed"):
            tk.Label(row, text=name, bg=PANEL, fg="#667078").pack(side="left", padx=(6, 2))
            v = tk.StringVar(value="")
            ttk.Entry(row, textvariable=v, width=9).pack(side="left", padx=(0, 10))
            self.fields[name] = v
        ttk.Button(row, text="Apply", command=self.apply_fields).pack(side="left", padx=(4, 6))
        ttk.Button(row, text="Delete shot", command=self.delete_shot).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Preview source", command=self.preview_shot).pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status_var, bg=BG, fg="#667078",
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=18, pady=(0, 10))

    # -------------------------------------------------------------- drawing
    def load_plan(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            messagebox.showerror("Maverick", f"Could not open plan:\n{e}")
            return
        self.doc = doc
        self.plan_path = path
        self.selected = None
        self._last_money = money_start(doc.get("shots", []))
        self.root.title(f"Maverick Edit Engine - {os.path.basename(path)}")
        self.draw()
        self.status_var.set(f"Loaded {os.path.basename(path)}  •  {len(doc.get('shots', []))} shots  •  {compute_total(doc.get('shots', [])):.2f}s")

    def draw(self):
        self.canvas.delete("all")
        if not self.doc:
            return
        shots = self.doc.get("shots", [])
        self.scale = float(self.zoom_var.get()) if hasattr(self, "zoom_var") else 8.0
        total = compute_total(shots)
        t = 0.0
        self.segments = []
        ruler_y = 24
        bar_y, bar_h = 44, 90
        # ruler
        step = 10 if self.scale < 14 else 5
        for sec in range(0, int(total) + 1, step):
            x = 20 + sec * self.scale
            self.canvas.create_line(x, ruler_y - 6, x, ruler_y + 2, fill="#b9c0c5")
            self.canvas.create_text(x + 2, ruler_y - 12, anchor="sw",
                                    text=f"{sec//60}:{sec%60:02d}", fill="#98a0a6",
                                    font=("Segoe UI", 8))
        # drop marker
        drop = self.drop_time()
        if drop is not None and 0 <= drop <= total:
            x = 20 + drop * self.scale
            self.canvas.create_line(x, ruler_y, x, bar_y + bar_h + 8, fill="#e0553b", width=2)
            self.canvas.create_text(x + 4, ruler_y + 2, anchor="nw", text="DROP",
                                    fill="#e0553b", font=("Segoe UI", 8, "bold"))
        for i, s in enumerate(shots):
            d = display_duration(s)
            x0 = 20 + t * self.scale
            w = max(3, d * self.scale)
            x1 = x0 + w
            self.segments.append((t, d, i))
            kind = s.get("kind", "clip")
            fill = {"black": "#2c3338", "noise": "#9aa3a9", "texture": "#d0e000"}.get(kind, "#cfe8e3")
            if i == self.selected:
                fill = "#7fd1c1"
            self.canvas.create_rectangle(x0, bar_y, x1, bar_y + bar_h,
                                         fill=fill, outline=BG, width=1, tags=f"seg{i}")
            # label
            label = s.get("note") or os.path.basename(s.get("clip", kind))
            if w > 34:
                self.canvas.create_text(x0 + 5, bar_y + 12, anchor="nw",
                                        text=str(label)[:max(4, int(w / 7))],
                                        fill="white" if kind in ("black", "noise") else "#233",
                                        font=("Segoe UI", 8))
            if w > 60:
                self.canvas.create_text(x0 + 5, bar_y + bar_h - 14, anchor="sw",
                                        text=f"{d:.1f}s", fill="white" if kind in ("black", "noise") else "#466",
                                        font=("Segoe UI", 8))
            # edge handles on selected
            if i == self.selected:
                self.canvas.create_rectangle(x0 - 2, bar_y, x0 + 3, bar_y + bar_h,
                                             fill=ACCENT, outline="")
                self.canvas.create_rectangle(x1 - 3, bar_y, x1 + 2, bar_y + bar_h,
                                             fill=ACCENT, outline="")
            t += d
        self.canvas.configure(scrollregion=(0, 0, max(self.canvas.winfo_width(), 20 + total * self.scale + 40), 170))
        self.info_var.set(f"{len(shots)} shots  •  {total:.2f}s  •  drop {drop:.2f}s" if drop else f"{len(shots)} shots  •  {total:.2f}s")
        if self.selected is not None:
            self.fill_fields()

    def drop_time(self):
        if not self.doc:
            return None
        lib_path = os.path.join(ROOT, "music", "library.json")
        try:
            lib = json.load(open(lib_path, encoding="utf-8"))
        except Exception:
            return None
        track_name = None
        q = (self.music_var.get() or "").lower()
        for name in lib:
            if q and q in name.lower():
                track_name = name
                break
        if not track_name:
            return None
        drop = float(lib[track_name].get("drop_estimate", 0.0))
        return drop - float(self.doc.get("music_start", 0.0))

    # --------------------------------------------------------------- editing
    def on_zoom(self, _=None):
        self.scale = float(self.zoom_var.get())
        self.draw()

    def _hit(self, x):
        for t, d, i in self.segments:
            x0 = 20 + t * self.scale
            x1 = x0 + max(3, d * self.scale)
            if x0 - 4 <= x <= x1 + 4:
                return i, x0, x1
        return None, None, None

    def on_press(self, event):
        x = self.canvas.canvasx(event.x)
        i, x0, x1 = self._hit(x)
        if i is None:
            return
        self.selected = i
        mode = "right" if abs(x - x1) <= 7 else ("left" if abs(x - x0) <= 7 else "select")
        s = self.doc["shots"][i]
        self.drag = (i, mode, x, float(s.get("start", 0.0)), float(s.get("end", 0.0)), float(s.get("dur", 0.0)))
        self.draw()

    def on_drag(self, event):
        if not self.drag:
            return
        i, mode, x_press, st, en, du = self.drag
        delta = (self.canvas.canvasx(event.x) - x_press) / self.scale
        s = self.doc["shots"][i]
        if mode == "right":
            if s.get("kind") in ("black", "noise"):
                s["dur"] = round(max(0.12, du + delta), 3)
            else:
                speed = float(s.get("speed", 1.0))
                s["end"] = round(max(st + 0.12 * speed, en + delta * speed), 3)
        elif mode == "left":
            if s.get("kind") in ("black", "noise"):
                pass
            else:
                speed = float(s.get("speed", 1.0))
                s["start"] = round(max(0.0, min(en - 0.12 * speed, st + delta * speed)), 3)
        else:
            return
        self.realign_music()
        self.draw()

    def on_release(self, _=None):
        self.drag = None

    def realign_music(self):
        """If the money shot moved, move music_start so the drop stays on it."""
        if not self.doc:
            return
        new_ms = money_start(self.doc["shots"])
        old = getattr(self, "_last_money", new_ms)
        if new_ms is not None and old is not None:
            self.doc["music_start"] = round(float(self.doc.get("music_start", 0.0)) + (new_ms - old), 3)
        self._last_money = new_ms

    def fill_fields(self):
        if self.selected is None:
            return
        s = self.doc["shots"][self.selected]
        for name, var in self.fields.items():
            var.set(f"{float(s.get(name, 0.0)):.3f}")
        self.detail_var.set(f"Shot {self.selected + 1}: {s.get('note') or s.get('kind') or s.get('clip','')}")

    def apply_fields(self):
        if self.selected is None:
            return
        s = self.doc["shots"][self.selected]
        try:
            for name, var in self.fields.items():
                s[name] = round(float(var.get()), 3)
        except ValueError:
            messagebox.showerror("Maverick", "Numbers only."); return
        self.realign_music()
        self.draw()

    def delete_shot(self):
        if self.selected is None:
            return
        if not messagebox.askyesno("Maverick", "Delete this shot?"):
            return
        del self.doc["shots"][self.selected]
        self.selected = None
        self.realign_music()
        self.draw()

    def preview_shot(self):
        if self.selected is None:
            return
        s = self.doc["shots"][self.selected]
        clip = s.get("clip")
        if not clip:
            return
        path = clip if os.path.isabs(clip) else os.path.join(ROOT, clip)
        if os.path.exists(path):
            os.startfile(path)

    # ---------------------------------------------------------------- actions
    def open_plan(self):
        p = filedialog.askopenfilename(initialdir=os.path.join(ROOT, "tools", "edits"),
                                       filetypes=[("Shot plans", "*.json")])
        if p:
            old_ms = money_start(self.doc["shots"]) if self.doc else None
            self.load_plan(p)
            self._last_money = money_start(self.doc["shots"]) if self.doc else None

    def save_plan(self):
        if not self.doc:
            return
        p = filedialog.asksaveasfilename(initialdir=os.path.join(ROOT, "tools", "edits"),
                                         defaultextension=".json", filetypes=[("Shot plans", "*.json")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.doc, f, indent=2)
        self.plan_path = p
        self.status_var.set(f"Saved {os.path.basename(p)}")

    def render(self):
        if not self.doc:
            return
        plan_path = self.plan_path or os.path.join(ROOT, "tools", "edits", "gui_plan.shots.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(self.doc, f, indent=2)
        out = os.path.join(OUT_DIR, self.out_var.get().strip() or "maverick_render")
        cmd = [sys.executable, ENGINE, "build", "--shots", plan_path,
               "--music", self.music_var.get().strip(),
               "--format", self.format_var.get().strip(), "--out", out]
        self.status_var.set("Rendering... see status bar")
        def work():
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.q.put(("done", p.returncode, p.stdout[-2000:], p.stderr[-2000:], out))
        threading.Thread(target=work, daemon=True).start()

    def _poll_queue(self):
        try:
            kind, rc, out, err, path = self.q.get_nowait()
            if rc == 0:
                self.status_var.set(f"Rendered: {path}")
                if messagebox.askyesno("Maverick", "Render complete. Open output folder?"):
                    os.startfile(os.path.dirname(path) if os.path.isdir(os.path.dirname(path)) else OUT_DIR)
            else:
                self.status_var.set("Render failed")
                messagebox.showerror("Maverick", f"Render failed:\n{err or out}")
        except queue.Empty:
            pass
        self.root.after(60, self._poll_queue)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
