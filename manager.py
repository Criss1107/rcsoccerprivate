import json
import os
import subprocess
import sys
import threading
import time

ROLES = {"goalkeeper": 1, "defender": 4, "attacker": 6}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LAUNCH_DELAY = 0.4    # el servidor numera por orden de conexion lanzar en orden
RESTART_DELAY = 2.0   # evita bucles de reinicio muy rapidos


def launch_player(role, number):
    """Lanza un jugador y devuelve un diccionario con informacion."""
    path = os.path.join(BASE_DIR, "players", f"{role}.py")
    proc = subprocess.Popen(
        [sys.executable, "-u", path, str(number), role],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # un solo flujo: no se bloquea leyendo stderr
        text=True,
        bufsize=1,
        cwd=BASE_DIR,
    )
    print(f"  -> {role.capitalize()} #{number} pid={proc.pid}", flush=True)
    return {"proc": proc, "number": number, "role": role, "restarts": 0}


def monitor_process(player):
    """Muestra la salida de un jugador en tiempo real."""
    for line in player["proc"].stdout:
        print(line.rstrip(), flush=True)


def start_monitor(player):
    threading.Thread(target=monitor_process, args=(player,), daemon=True).start()


def save_manager_metrics(processes, t0):
    """Guarda reinicios por jugador (metrica de estabilidad)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    data = {
        "seconds": round(time.time() - t0, 1),
        "restarts": {f"{p['role']}-{p['number']}": p["restarts"] for p in processes},
        "total_restarts": sum(p["restarts"] for p in processes),
    }
    with open(os.path.join(LOG_DIR, "manager.json"), "w") as f:
        json.dump(data, f, indent=2)


def main():
    processes = []
    t0 = time.time()

    number = 1
    plan = [("goalkeeper", ROLES["goalkeeper"]),
            ("defender", ROLES["defender"]),
            ("attacker", ROLES["attacker"])]
    for role, count in plan:
        for _ in range(count):
            p = launch_player(role, number)
            start_monitor(p)
            processes.append(p)
            number += 1
            time.sleep(LAUNCH_DELAY)

    print("\nTodos los jugadores lanzados. Monitoreando... (Ctrl+C para salir)\n",
          flush=True)

    # Bucle de reinicio automatico
    try:
        while True:
            time.sleep(1)
            for i, player in enumerate(processes):
                if player["proc"].poll() is not None:  # proceso muerto
                    print(f"[manager] {player['role']}-{player['number']} murio "
                          f"(codigo {player['proc'].returncode}). Reiniciando...",
                          flush=True)
                    time.sleep(RESTART_DELAY)
                    restarts = player["restarts"] + 1
                    new_player = launch_player(player["role"], player["number"])
                    new_player["restarts"] = restarts
                    start_monitor(new_player)
                    processes[i] = new_player
    except KeyboardInterrupt:
        print("\nCerrando todos los jugadores...", flush=True)
        for player in processes:
            player["proc"].terminate()      # SIGTERM cada jugador guarda sus metricas
        for player in processes:
            try:
                player["proc"].wait(timeout=3)
            except subprocess.TimeoutExpired:
                player["proc"].kill()
        save_manager_metrics(processes, t0)
        print("Hecho. Metricas en logs/", flush=True)


if __name__ == "__main__":
    main()
