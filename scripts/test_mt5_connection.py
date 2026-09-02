"""Test MT5 connection via Python MetaTrader5 package."""
import MetaTrader5 as mt5

print("Initializing MT5...")
if not mt5.initialize():
    print(f"MT5 initialize failed: {mt5.last_error()}")
    exit(1)

terminal = mt5.terminal_info()
print(f"Terminal: {terminal.name}")
print(f"Build: {terminal.build}")
print(f"Path: {terminal.path}")
print(f"Connected: {terminal.connected}")

account = mt5.account_info()
if account:
    print(f"\nAccount: {account.login}")
    print(f"Server: {account.server}")
    print(f"Name: {account.name}")
    print(f"Balance: {account.balance}")
    print(f"Equity: {account.equity}")
    print(f"Leverage: {account.leverage}")
    print(f"Currency: {account.currency}")
else:
    print(f"Account info failed: {mt5.last_error()}")

# Test getting symbols
symbols = mt5.symbols_get()
if symbols:
    print(f"\nAvailable symbols: {len(symbols)}")
    for s in symbols[:5]:
        print(f"  - {s.name}: {s.bid}/{s.ask}")
else:
    print(f"Symbols fetch failed: {mt5.last_error()}")

mt5.shutdown()
print("\nMT5 connection test complete!")
