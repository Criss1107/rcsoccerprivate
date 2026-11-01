from base_player import BasePlayer
import sys


class Goalkeeper(BasePlayer):
    def play(self):
        """Arquero se queda en el arco y gira un poco la cabeza"""
        self.send("(turn 10)")  # mirar a la derecha lentamente


if __name__ == "__main__":
    number = int(sys.argv[1])
    role = sys.argv[2]
    player = Goalkeeper(team_name="MYTEAMUD", number=number, role=role)
    player.start()
