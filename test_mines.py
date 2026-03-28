
import math

def calculate_multiplier(bombs, gems):
    if gems <= 0:
        return 1.0
    if gems > (25 - bombs):
        return 0.0
    def nCr(n, r):
        if r < 0 or r > n:
            return 0
        if r == 0 or r == n:
            return 1
        if r > n // 2:
            r = n - r
        f = math.factorial
        try:
            return f(n) // (f(r) * f(n - r))
        except (ValueError, OverflowError):
            return 0
    try:
        num_safe = 25 - bombs
        total_combos = nCr(25, gems)
        safe_combos = nCr(num_safe, gems)
        if total_combos == 0 or safe_combos == 0:
            return 0.0
        prob = safe_combos / total_combos
        multiplier = 0.98 / prob
        return round(multiplier, 2)
    except (ZeroDivisionError, ValueError):
        return 0.0
    except Exception:
        return 1.0

def test_parsing(content, current_prefix):
    cmd_trigger = f"{current_prefix}mines"
    words = content.split()
    print(f"Content: '{content}'")
    print(f"Prefix: '{current_prefix}'")
    print(f"Trigger: '{cmd_trigger}'")
    print(f"Words: {words}")
    
    if not words or not words[0].startswith(cmd_trigger):
        print("Skipped: doesn't start with trigger")
        return

    if words[0] != cmd_trigger and not words[0].startswith(cmd_trigger):
         print("Skipped: second check failed")
         return

    try:
        if words[0] == cmd_trigger:
            raw_args = words[1:]
        else:
            amount_part = words[0][len(cmd_trigger):]
            raw_args = [amount_part] + words[1:]
        
        print(f"Raw Args: {raw_args}")
        
        if not raw_args or not raw_args[0]:
            print("Error: No args")
            return

        amount_str = raw_args[0].replace(",", "").replace(".", "")
        print(f"Amount Str: '{amount_str}'")
        
        if amount_str == "all":
            amount = 1000000 # Dummy
        else:
            amount = int(amount_str)
        
        print(f"Parsed Amount: {amount}")

        bombs = 3
        if len(raw_args) >= 2:
            try:
                bombs = int(raw_args[1])
                print(f"Parsed Bombs: {bombs}")
            except ValueError:
                print("Error: Bombs count not a number")
                return
        
        initial_mult = calculate_multiplier(bombs, 1)
        print(f"Initial Mult: {initial_mult}")
        print("SUCCESS")

    except ValueError as e:
        print(f"VALUE ERROR: {e}")
    except Exception as e:
        print(f"OTHER ERROR: {e}")

print("--- Test 1: Space ---")
test_parsing("imines 100000 3", "i")
print("\n--- Test 2: No Space ---")
test_parsing("imines100000 3", "i")
print("\n--- Test 3: Multiple Spaces ---")
test_parsing("imines   100000   3", "i")
print("\n--- Test 4: Commas ---")
test_parsing("imines 100,000 3", "i")
