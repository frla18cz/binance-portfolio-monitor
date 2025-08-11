from utils.database_manager import get_supabase_client

db = get_supabase_client()

# Podívejme se na všechny NAV záznamy pro Habitanti
nav_data = db.table("nav_history").select("*").eq("account_id", "f98f3f42-1cc7-4125-b57e-738d40336026").order("timestamp").execute()

print(f"Celkem NAV záznamů: {len(nav_data.data)}")
print("\nVšechny NAV záznamy:")
for nav in nav_data.data:
    print(f"  {nav['timestamp']}: NAV=${nav['nav']:.2f}, Benchmark=${nav['benchmark_value']:.2f}, Alpha={nav.get('alpha_percentage', 0):.2f}%")

# Podívejme se také na benchmark modifications
print("\nBenchmark modifications:")
mods = db.table("benchmark_modifications").select("*").eq("account_id", "f98f3f42-1cc7-4125-b57e-738d40336026").order("modification_timestamp").execute()
if mods.data:
    for mod in mods.data:
        print(f"  {mod['modification_timestamp']}: {mod['modification_type']} ${mod.get('cashflow_amount', 0):.2f}")
        print(f"    BTC: {mod.get('btc_units_before', 0)} -> {mod.get('btc_units_after', 0)}")
        print(f"    ETH: {mod.get('eth_units_before', 0)} -> {mod.get('eth_units_after', 0)}")
else:
    print("  Žádné modifications")

# A rebalance history
print("\nRebalance history:")
rebalances = db.table("benchmark_rebalance_history").select("*").eq("account_id", "f98f3f42-1cc7-4125-b57e-738d40336026").order("rebalance_timestamp").execute()
if rebalances.data:
    for reb in rebalances.data:
        print(f"  {reb['rebalance_timestamp']}: {reb['status']}")
        print(f"    Total value: ${reb.get('total_value_before', 0):.2f}")
        print(f"    BTC: {reb.get('btc_units_before', 0)} -> {reb.get('btc_units_after', 0)}")
        print(f"    ETH: {reb.get('eth_units_before', 0)} -> {reb.get('eth_units_after', 0)}")
else:
    print("  Žádné rebalances")

# Processed transactions
print("\nProcessed transactions:")
txns = db.table("processed_transactions").select("*").eq("account_id", "f98f3f42-1cc7-4125-b57e-738d40336026").order("timestamp").execute()
if txns.data:
    for txn in txns.data:
        print(f"  {txn['timestamp']}: {txn['type']} ${txn.get('amount', 0):.2f}")
else:
    print("  Žádné transakce")
