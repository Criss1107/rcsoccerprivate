import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

_OBJ = re.compile(r"\(\(([^()]*)\)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)")
_PLAYER = re.compile(r'^[pP]\s*(?:"([^"]*)")?\s*(\d+)?')
_STAMINA = re.compile(r"\(stamina\s+(-?\d+\.?\d*)")


@dataclass
class Obj:
    dist: float
    dir: float  # grados, relativo a la direccion del cuerpo


@dataclass
class Mate(Obj):
    unum: Optional[int] = None


@dataclass
class World:
    ball: Optional[Obj] = None
    own_goal: Optional[Obj] = None
    opp_goal: Optional[Obj] = None
    mates: List[Mate] = field(default_factory=list)
    opps: List[Obj] = field(default_factory=list)
    stamina: Optional[float] = None


def parse_see(msg: str, team: str, side: str) -> World:
    """Convierte '(see t ...)' en un World. side es 'l' o 'r'."""
    w = World()
    opp_side = "r" if side == "l" else "l"
    for name, d, a in _OBJ.findall(msg):
        dist, ang = float(d), float(a)
        n = name.strip()
        if n in ("b", "B"):
            w.ball = Obj(dist, ang)
        elif n[:1] in ("g", "G"):
            parts = n.split()
            if len(parts) == 2:
                if parts[1] == opp_side:
                    w.opp_goal = Obj(dist, ang)
                elif parts[1] == side:
                    w.own_goal = Obj(dist, ang)
        elif n[:1] in ("p", "P"):
            m = _PLAYER.match(n)
            pteam = m.group(1) if m else None
            unum = int(m.group(2)) if (m and m.group(2)) else None
            if pteam == team:
                w.mates.append(Mate(dist, ang, unum))
            elif pteam is not None:
                w.opps.append(Obj(dist, ang))
    return w


def parse_sense_body_stamina(msg: str) -> Optional[float]:
    m = _STAMINA.search(msg)
    return float(m.group(1)) if m else None


def dist_between(a: Obj, b: Obj) -> float:
    """Distancia entre dos objetos vistos (ley de cosenos)."""
    da = math.radians(a.dir - b.dir)
    v = a.dist ** 2 + b.dist ** 2 - 2 * a.dist * b.dist * math.cos(da)
    return math.sqrt(max(v, 0.0))