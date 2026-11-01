# Robot Soccer -- Multi-Agent Python Simulation

## 🎮 Description

This project simulates **11 Robot Soccer players**, each running as  
**independent Python processes**.  
Included roles:

- **1 Goalkeeper**  
- **4 Defenders**  
- **6 Attackers**

The `manager.py` script launches and manages all processes. Each  
player executes its own behavior defined in the `players/` folder.

------------------------------------------------------------------------

## 📁 Project Structure

```
robot_soccer/
│
├── requirements.txt
├── run_all.sh
├── manager.py
│
└── players/
    ├── base_player.py
    ├── defender.py
    ├── attacker.py
    ├── goalkeeper.py
```

------------------------------------------------------------------------

## 🐍 Create Virtual Environment

```bash
python3 -m venv env
source env/bin/activate
```

Deactivate:

```bash
deactivate
```

------------------------------------------------------------------------

## 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## ▶️ Execution

### Using the `.sh` Script

```bash
chmod +x run_all.sh
./run_all.sh
```

### Or Running the Manager:

```bash
python3 manager.py
```

------------------------------------------------------------------------

## 📡 Logs

Each process prints messages like:

```
[DEFENDER #2] Defending the zone...
[ATTACKER #5] Attacking and going for goal...
[GOALKEEPER #1] Protecting the goal...
```

------------------------------------------------------------------------

## 🧩 Customization

Edit `manager.py` to change the numbers:

```python
ROLES = {
    "goalkeeper": 1,
    "defender": 4,
    "attacker": 6
}
```

------------------------------------------------------------------------

## ❤️ Contributions

You can add AI, sockets, strategies, or new positions.

