import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time

ser = None
reading = False


def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]


def refresh_ports():
    ports = list_ports()
    port_combo["values"] = ports
    if ports:
        port_var.set(ports[0])


def connect():
    global ser, reading
    try:
        ser = serial.Serial(port_var.get(), int(baud_var.get()), timeout=1)
        time.sleep(2)
        ser.flushInput()
        log(f"Conectado em {port_var.get()} @ {baud_var.get()} baud")
        reading = True
        threading.Thread(target=read_loop, daemon=True).start()
        btn_connect.config(text="Desconectar", command=disconnect)
    except Exception as e:
        log(f"Erro ao conectar: {e}")


def disconnect():
    global ser, reading
    reading = False
    if ser and ser.is_open:
        ser.close()
    log("Desconectado")
    btn_connect.config(text="Conectar", command=connect)


def read_loop():
    while reading and ser and ser.is_open:
        try:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if line:
                log(f"<< {line}")
        except Exception:
            break


def send_line(cmd):
    cmd = cmd.strip()
    if not cmd:
        return
    if not ser or not ser.is_open:
        log("Não conectado!")
        return
    ser.write((cmd + "\n").encode())
    log(f">> {cmd}")


def send_gcode_area():
    content = txt_gcode.get("1.0", tk.END)
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith(";")]
    if not lines:
        log("Nenhum G-code para enviar.")
        return
    for line in lines:
        send_line(line)


def insert_at_cursor(text):
    try:
        txt_gcode.delete(tk.SEL_FIRST, tk.SEL_LAST)
    except tk.TclError:
        pass
    txt_gcode.insert(tk.INSERT, text)
    txt_gcode.focus_set()


def macro_move_xyz():
    x = entry_x.get().strip()
    y = entry_y.get().strip()
    z = entry_z.get().strip()
    f = entry_feed.get().strip()
    if not x and not y and not z:
        log("Informe ao menos X, Y ou Z.")
        return
    cmd = "G1"
    if x:
        cmd += f" X{x}"
    if y:
        cmd += f" Y{y}"
    if z:
        cmd += f" Z{z}"
    if f:
        cmd += f" F{f}"
    insert_at_cursor(cmd + "\n")


def log(msg):
    txt_log.config(state="normal")
    txt_log.insert(tk.END, msg + "\n")
    txt_log.see(tk.END)
    txt_log.config(state="disabled")


# ── GUI ────────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("GRBL Controller")
root.minsize(800, 560)

# ── Barra de conexão (topo, largura total) ──
frame_conn = ttk.LabelFrame(root, text="Conexão Serial")
frame_conn.pack(fill="x", padx=8, pady=(8, 4))

ttk.Label(frame_conn, text="Porta:").grid(row=0, column=0, padx=4, pady=6)
port_var = tk.StringVar()
port_combo = ttk.Combobox(frame_conn, textvariable=port_var, width=12)
port_combo.grid(row=0, column=1, padx=4)

ttk.Button(frame_conn, text="⟳ Atualizar", command=refresh_ports).grid(row=0, column=2, padx=4)

ttk.Label(frame_conn, text="Baud:").grid(row=0, column=3, padx=4)
baud_var = tk.StringVar(value="115200")
ttk.Combobox(frame_conn, textvariable=baud_var, values=["9600", "115200"], width=9).grid(row=0, column=4, padx=4)

btn_connect = ttk.Button(frame_conn, text="Conectar", command=connect)
btn_connect.grid(row=0, column=5, padx=12)

# ── Área principal: duas colunas ──
frame_main = ttk.Frame(root)
frame_main.pack(fill="both", expand=True, padx=8, pady=4)

frame_main.columnconfigure(0, weight=0)  # esquerda: macros (largura fixa)
frame_main.columnconfigure(1, weight=1)  # direita: gcode + console (expande)
frame_main.rowconfigure(0, weight=1)

# ── Coluna esquerda: Macros ──
frame_macros = ttk.LabelFrame(frame_main, text="Macros")
frame_macros.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

# — Macro: Mover X/Y/Z —
frame_move = ttk.LabelFrame(frame_macros, text="Mover para X / Y / Z")
frame_move.pack(fill="x", padx=6, pady=6, ipadx=4, ipady=4)

fields = [("X:", "entry_x"), ("Y:", "entry_y"), ("Z:", "entry_z"), ("Feed\n(mm/min):", "entry_feed")]
entries = {}
for i, (label, name) in enumerate(fields):
    ttk.Label(frame_move, text=label).grid(row=i, column=0, sticky="e", padx=(6, 2), pady=3)
    e = ttk.Entry(frame_move, width=10)
    e.grid(row=i, column=1, padx=(2, 6), pady=3)
    entries[name] = e

entry_x    = entries["entry_x"]
entry_y    = entries["entry_y"]
entry_z    = entries["entry_z"]
entry_feed = entries["entry_feed"]

ttk.Button(frame_move, text="Inserir G-code", command=macro_move_xyz).grid(
    row=len(fields), column=0, columnspan=2, pady=(6, 4)
)

# ── Coluna direita: G-code + Console ──
frame_right = ttk.Frame(frame_main)
frame_right.grid(row=0, column=1, sticky="nsew")
frame_right.rowconfigure(0, weight=1)
frame_right.rowconfigure(1, weight=0)
frame_right.columnconfigure(0, weight=1)

frame_gcode = ttk.LabelFrame(frame_right, text="G-code")
frame_gcode.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
frame_gcode.rowconfigure(0, weight=1)
frame_gcode.columnconfigure(0, weight=1)

txt_gcode = scrolledtext.ScrolledText(
    frame_gcode,
    bg="white", fg="black",
    font=("Courier New", 10),
    undo=True,
)
txt_gcode.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 0))

ttk.Button(frame_gcode, text="Enviar G-code", command=send_gcode_area).grid(
    row=1, column=0, pady=6
)

frame_log = ttk.LabelFrame(frame_right, text="Console")
frame_log.grid(row=1, column=0, sticky="ew")

txt_log = scrolledtext.ScrolledText(
    frame_log, height=6, state="disabled",
    bg="#1e1e1e", fg="#00ff88", font=("Courier New", 9),
)
txt_log.pack(fill="x", padx=4, pady=4)

refresh_ports()
root.mainloop()
