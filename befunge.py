class Befunge:
    def __init__(self, code):
        # 渡されたコードをインスタンス変数として保持
        self.code = code
        self.x = 0
        self.y = 0
        self.dir = ">"  # 初期方向は右向きにしておくと安全
        self.str_check = False
        self.stack = []

    def execute(self):
        while True:
            # 現在のポインタ位置の文字を取得
            t = self.code[self.y][self.x]

            # --- 1. 文字列モード中の処理 ---
            if self.str_check and t != '"':
                self.stack.append(t)
            
            # --- 2. 通常の命令処理 ---
            else:
                match t:
                    case "^" | "v" | ">" | "<":
                        self.dir = t
                    case '"':
                        self.str_check = not self.str_check
                    case ",":
                        # スタックに入っている文字を出力
                        print("".join(self.stack), end="")
                        self.stack.clear()  # 出力したらスタックを空に
                    case "@":
                        print()  # 最後に改行
                        break
                    case " ":
                        pass  # 空白は何もしない
                    case _:
                        print(f'\nエラー: "{t}" は未定義の命令です。')

            # --- 3. ポインタの移動 ---
            match self.dir:
                case "^":
                    self.y -= 1
                case "v":
                    self.y += 1
                case ">":
                    self.x += 1
                case "<":
                    self.x -= 1

            # 範囲外チェック（簡易版）
            if self.y >= len(self.code) or self.x >= len(self.code[self.y]):
                break


# --- 実行部分 ---
code = [
    [">", '"', "H", "e", "l", "l", "o", " ", '"', "v"],
    [" ", " ", " ", " ", " ", " ", " ", " ", " ", " "],  # 行の調整
    ["@", ',', '"', "d", "l", "r", "o", "W", '"', "<"]   # 下から左へ流れて @ で終わる
]

# 1. インスタンス化（初期化）
interpreter = Befunge(code)

# 2. 実行！
interpreter.execute()