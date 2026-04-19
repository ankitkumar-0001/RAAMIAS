import requests
import time
import threading

TARGET_URL = "http://localhost:8000/login"


def simulate_brute_force():
    target_email = input("Enter target email to attack: ")
    print(f"\n🚀 [SIMULATOR] Launching Brute Force against {target_email}...")
    for i in range(1, 6):
        print(f"   -> Attempt {i}: Injecting payload...")
        try:
            response = requests.post(
                TARGET_URL, json={"email": target_email, "password": f"fake_pass_{i}"})
            if response.status_code == 403:
                print("   🛑 [DEFENSE TRIGGERED] WAF Blocked the attack!")
                break
        except Exception as e:
            pass
        time.sleep(0.5)


def simulate_mini_dos():
    print(f"\n🌊 [SIMULATOR] Launching Application-Layer DoS Simulation...")

    def flood():
        for _ in range(10):
            requests.post(TARGET_URL, json={
                          "email": "random@gmail.com", "password": "123"})

    threads = []
    for _ in range(5):
        t = threading.Thread(target=flood)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print("   ✅ [SIMULATOR] DoS wave complete.")


while True:
    print("\n" + "="*30)
    print("🔥 RAAMIAS THREAT SIMULATOR 🔥")
    print("="*30)
    print("1. Simulate Brute-Force Attack")
    print("2. Simulate App-Layer DoS Wave")
    print("3. Exit")

    choice = input("Select an attack vector: ")

    if choice == '1':
        simulate_brute_force()
    elif choice == '2':
        simulate_mini_dos()
    elif choice == '3':
        break
