import json
import os
import re
import socket
import time
from perception import World, parse_see, parse_sense_body_stamina

SERVER_HOST = "localhost"
SERVER_PORT = 6000
BUFFER_SIZE = 4096


class BasePlayer:
    def __init__(self, team_name, number, role):
        self.team_name = team_name
        self.number = number
        self.role = role

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))  # puerto local aleatorio

    def send_to(self, msg, port):
        """Envia mensaje a un puerto específico"""
        self.sock.sendto(msg.encode(), (SERVER_HOST, port))
        print(f"[{self.role}-{self.number}] -> {msg} (puerto={port})")

    def send(self, msg):
        """Envia mensaje al puerto del servidor"""
        self.send_to(msg, SERVER_PORT)

    def receive(self, timeout=None):
        """Recibe mensajes del servidor"""
        if timeout:
            self.sock.settimeout(timeout)
        else:
            self.sock.settimeout(None)
        try:
            data, _ = self.sock.recvfrom(BUFFER_SIZE)
            msg = data.decode()
            return msg
        except socket.timeout:
            return ""
        except Exception as e:
            print(e)
            return ""

    def start_position(self):
        """Devuelve la posición inicial de cada jugador."""
        positions_map = {
            1: (-52.5, 0),     # Goalkeeper
            2: (-35, -20),     # Defenders
            3: (-35, -7),
            4: (-35, 7),
            5: (-35, 20),
            6: (-10, 15),      # Attackers line 1
            7: (0, 15),
            8: (10, 15),
            9: (-10, 25),      # Attackers line 2
            10: (0, 25),
            11: (10, 25),
        }
        return positions_map.get(self.number, (0, 0))

    def init_connection(self):
        """Enviar INIT al servidor y colocarse antes del kickoff"""
        if self.role == "goalkeeper":
            init_msg = f"(init {self.team_name} (goalie))"
        else:
            init_msg = f"(init {self.team_name})"

        self.send(init_msg)

        while True:
            msg = self.receive()
            if msg and self.is_pre_kickoff_or_play(msg):
                print(f"[{self.role}-{self.number}] <- INIT OK")

                x, y = self.start_position()
                self.send(f"(move {x} {y})")
                print(f"[{self.role}-{self.number}] -> MOVE a ({x},{y})")
                break

    def play(self):
        """Método base que puede sobrescribirse en cada rol"""
        self.send("(dash 50)")

    def is_pre_kickoff_or_play(self, msg: str) -> bool:
        """Devuelve True si el mensaje indica pre-kickoff, init o play_on."""
        keywords = ["before_kick_off", "(init", "play_on"]
        return any(keyword in msg for keyword in keywords)

    def action_loop(self):
        """Loop principal de acciones durante el juego"""
        while True:
            msg = self.receive()
            if msg and self.is_pre_kickoff_or_play(msg):
                x, y = self.start_position()
                self.send(f"(move {x} {y})")
            else:
                self.play()
            time.sleep(0.1)

    def start(self):
        """Inicia la conexión y el loop de acción"""
        self.init_connection()
        self.action_loop()
