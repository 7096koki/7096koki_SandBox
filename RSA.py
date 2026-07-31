import random

# =========================================================
# 1. 解く関数 (※変更なし)
# =========================================================
def rsa_solve(c, n, e):
    p = 0
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            p = i
            break

    q = n // p
    l = (p - 1) * (q - 1)

    d = 1
    while (e * d) % l != 1:
        d += 1

    m = pow(c, d, n)
    return m


# =========================================================
# 2. 問題を作る関数 (※変更なし)
# =========================================================
def rsa_define(target_bit, m=None):
    half_bit = target_bit // 2

    min_val = 1 << (half_bit - 1)
    max_val = (1 << half_bit) - 1

    primes = [
        x
        for x in range(min_val, max_val + 1)
        if x > 1 and all(x % d != 0 for d in range(2, int(x**0.5) + 1))
    ]

    e = 17

    while True:
        p = random.choice(primes)
        q = random.choice(primes)
        if p == q:
            continue

        n = p * q
        l = (p - 1) * (q - 1)

        target_m = m if m is not None else random.randint(2, n - 1)
        if target_m >= n:
            continue

        d = 1
        found_d = False
        while d < l:
            if (e * d) % l == 1:
                found_d = True
                break
            d += 1

        if found_d:
            break

    c = pow(target_m, e, n)

    return c, n, e


# =========================================================
# 関数の外側だけで「サマーウォーズ」の平文を再現！
# =========================================================
text = "The Magic Words are Squeamish Ossifrage"

# 1. 1文字ずつ ASCII コード（数値）に変換して暗号化！
cipher_list = []
keys = []

print("--- 暗号化中 ---")
for char in text:
    m_code = ord(char)  # 文字を数値（ASCII）に変換
    # 既存の rsa_define を 16 ビットで呼び出し
    c, n, e = rsa_define(16, m=m_code)
    cipher_list.append(c)
    keys.append((n, e))

print(f"暗号文（数値列）: {cipher_list}")
print(f"{keys}")


print("\n--- 解読中 (rsa_solve を実行) ---")
# 2. 解読して文字に戻す！
decrypted_chars = []
for c, (n, e) in zip(cipher_list, keys):
    decrypted_m = rsa_solve(c, n, e)
    decrypted_chars.append(chr(decrypted_m))  # 数値を文字に戻す

# 復元された文字列を合体
result_text = "".join(decrypted_chars)

print(f"\n解読された平文: {result_text}")