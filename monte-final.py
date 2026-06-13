#!/usr/bin/env python3
import tkinter as tk, tkinter.ttk as ttk, tkinter.filedialog as fd, sqlite3, os
import numpy as np, pandas as pd, matplotlib; matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime


DB = os.path.join(os.path.dirname(__file__), "mc.db")
with sqlite3.connect(DB) as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, ts TEXT, stock TEXT, 
price REAL, days INTEGER, N INTEGER, mean REAL, pnl REAL)""")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monte Carlo Simulator"); self.geometry("1100x650"); self.configure(bg="#1e1e2e")
        self.run, self.anim, self.paths, self.day = 0, None, None, 0
        
      
        s = ttk.Style(); s.theme_use("clam")
        s.configure("Treeview", bg="#181825", fg="#cdd6f4", fieldbackground="#181825", rowheight=30)
        s.configure("Treeview.Heading", bg="#313244", fg="#89b4fa", font=("Arial", 10, "bold"))
        
      
        left = tk.Frame(self, bg="#1e1e2e"); left.pack(side="left", fill="y", padx=10, pady=10)
        self.fig = Figure(figsize=(5,4), facecolor="#1e1e2e")
        self.ax = self.fig.add_subplot(111); self.ax.set_facecolor("#181825")
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)
        
        self.tree = ttk.Treeview(self, columns=("m", "v"), show="headings")
        self.tree.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        for c, t in zip(("m","v"),("Metric","Value")): self.tree.heading(c, text=t)
        
       
        self.v = {k: tk.StringVar(value=v) for k, v in {"Stock":"RELIANCE","Price":"500","Mu%":"0.05",
                                                        "Sigma%":"2.0","Days":"60","N":"200"}.items()}
        tk.Label(left, text="MONTE CARLO", fg="#89b4fa", bg="#1e1e2e", font=("Arial",14,"bold")).pack(pady=10)
        for k, v in self.v.items():
            f = tk.Frame(left, bg="#1e1e2e"); f.pack(fill="x", pady=3)
            tk.Label(f, text=k, width=8, bg="#1e1e2e", fg="#a6adc8", anchor="w").pack(side="left")
            tk.Entry(f, textvariable=v, width=12, bg="#313244", fg="#cdd6f4", relief="flat").pack(side="right")
            
        def btn(txt, cmd, bg): tk.Button(left, text=txt, command=cmd, bg=bg, fg="#11111b", font=("Arial", 10, "bold"), relief="flat").pack(fill="x", pady=5)
        tk.Frame(left, bg="#1e1e2e", height=10).pack()
        btn("Load CSV", self.ld, "#89dceb"); btn("History DB", self.hist, "#f9e2af")
        self.s_btn = tk.Button(left, text="START", command=self.tg, bg="#a6e3a1", fg="#11111b", font=("Arial",12,"bold"), relief="flat")
        self.s_btn.pack(fill="x", pady=10)

    def ld(self):
        f = fd.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not f: return
        try:
            df = pd.read_csv(f); pc = next((c for c in ["Close","close","Price"] if c in df), None)
            if pc:
                df["ret"] = pd.to_numeric(df[pc], 'coerce').pct_change().dropna()
                self.v["Price"].set(str(round(df[pc].iloc[-1],2)))
                self.v["Mu%"].set(str(round(df["ret"].mean()*100,4)))
                self.v["Sigma%"].set(str(round(df["ret"].std()*100,4)))
                self.v["Stock"].set(os.path.basename(f).split('.')[0].upper()[:10])
        except Exception as e: print("CSV Error:", e)

    def tg(self):
        if self.run:
            self.run = 0; self.s_btn.config(text="START", bg="#a6e3a1"); self.after_cancel(self.anim)
        else:
            self.p, self.mu, self.sig = float(self.v["Price"].get()), float(self.v["Mu%"].get())/100, float(self.v["Sigma%"].get())/100
            self.d, self.n = int(self.v["Days"].get()), int(self.v["N"].get())
            self.paths = np.full((self.n, 1), self.p); self.day, self.run = 0, 1
            self.s_btn.config(text="STOP", bg="#f38ba8"); self.ax.clear(); self.tick()

    def tick(self):
        if not self.run: return
        nxt = self.paths[:,-1] * np.exp(self.mu - 0.5*self.sig**2 + self.sig * np.random.randn(self.n))
        self.paths = np.hstack([self.paths, nxt.reshape(-1,1)]); self.day += 1
        
        self.ax.clear(); self.ax.set_facecolor("#181825"); self.ax.tick_params(colors="#a6adc8")
        x = np.arange(self.day+1); step = max(1, self.n//150)
        for y in self.paths[::step]: 
            self.ax.plot(x, y, color="#a6e3a1" if y[-1] >= self.p else "#f38ba8", alpha=0.3, lw=0.8)
        self.ax.plot(x, np.mean(self.paths, axis=0), color="#f9e2af", ls="-", lw=2, label='Mean')
        self.ax.plot(x, np.percentile(self.paths,95,axis=0), color="#89b4fa", ls="--", label='p95')
        self.ax.plot(x, np.percentile(self.paths,5,axis=0), color="#f38ba8", ls="--", label='p5')
        self.ax.axhline(self.p, color="#a6adc8", ls=":", lw=1.5, label='Start')
        self.ax.legend(facecolor="#313244", labelcolor="#cdd6f4", edgecolor="#1e1e2e"); self.canvas.draw()
        
        if self.day % 5 == 0 or self.day == self.d: self.stats()
        if self.day >= self.d:
            self.tg(); f = self.paths[:,-1]
            with sqlite3.connect(DB) as conn:
                conn.execute("INSERT INTO runs (ts, stock, price, days, N, mean, pnl) VALUES (?,?,?,?,?,?,?)",
                    (datetime.now().isoformat(' ', 'seconds'), self.v["Stock"].get(), self.p, self.d, self.n, f.mean(), (f.mean()-self.p)/self.p*100))
            return
        self.anim = self.after(50, self.tick)

    def stats(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        f = self.paths[:,-1]; prof = f[f>=self.p]
        data = [("Start Price", f"Rs. {self.p:.2f}"), ("Expected Mean", f"Rs. {f.mean():.2f}"),
                ("Median", f"Rs. {np.median(f):.2f}"), ("Best (p95)", f"Rs. {np.percentile(f,95):.2f}"),
                ("Worst (p5)", f"Rs. {np.percentile(f,5):.2f}"), ("Win Prob.", f"{len(prof)/self.n*100:.1f}%"),
                ("Loss Prob.", f"{(self.n-len(prof))/self.n*100:.1f}%"), ("Max Gain", f"Rs. {f.max()-self.p:.2f}"),
                ("Max Loss", f"Rs. {f.min()-self.p:.2f}")]
        for m, v in data: self.tree.insert("", "end", values=(m, v))

    def hist(self):
        w = tk.Toplevel(self); w.title("Run History"); w.geometry("700x350"); w.configure(bg="#1e1e2e")
        t = ttk.Treeview(w, columns=("id","ts","st","p","d","n","m","pnl"), show="headings")
        for c in t["columns"]: t.heading(c, text=c.upper()); t.column(c, width=80, anchor="center")
        t.pack(fill="both", expand=True, padx=10, pady=10)
        for r in pd.read_sql("SELECT * FROM runs ORDER BY id DESC LIMIT 100", sqlite3.connect(DB)).itertuples(index=False):
            t.insert("", "end", values=[round(x, 2) if isinstance(x, float) else x for x in r])

if __name__ == "__main__": App().mainloop()