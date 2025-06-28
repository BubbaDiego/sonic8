import asyncio
from data.data_locker import DataLocker
from cyclone.services.position_service import CyclonePositionService

def run_console():
    svc = CyclonePositionService(DataLocker.get_instance())
    while True:
        print("\nCyclone » Positions")
        print("1) Sync from Jupiter")
        print("2) Enrich positions")
        print("3) View positions")
        print("0) Back")
        ch = input("→ ").strip()
        if ch == "1":
            svc.update_positions_from_jupiter()
        elif ch == "2":
            asyncio.run(svc.enrich_positions())
        elif ch == "3":
            svc.view_positions()
        elif ch == "0":
            break
