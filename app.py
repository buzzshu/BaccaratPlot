
from flask import Flask, render_template, request, send_file, jsonify
import random
from collections import Counter
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

def card_value(card):
    return min(card, 10) % 10

def total(cards):
    return sum(card_value(c) for c in cards) % 10

def banker_draws(banker, player_third):
    b_total = total(banker)
    if not player_third:
        return b_total <= 5
    pt = card_value(player_third[0])
    if b_total <= 2: return True
    if b_total == 3: return pt != 8
    if b_total == 4: return 2 <= pt <= 7
    if b_total == 5: return 4 <= pt <= 7
    if b_total == 6: return 6 <= pt <= 7
    return False

def create_shoe(num_decks=6):
    shoe = [i for i in range(1, 14)] * 4 * num_decks
    random.shuffle(shoe)
    burn = card_value(shoe[0])
    shoe = shoe[1 + burn:]
    return shoe

def play_game_from_shoe(shoe):
    while True:
        if len(shoe) < 6:
            shoe[:] = create_shoe()
            continue
        player = [shoe.pop(), shoe.pop()]
        banker = [shoe.pop(), shoe.pop()]
        player_third, banker_third = [], []

        if total(player) <= 5:
            player_third = [shoe.pop()]
            player.append(player_third[0])
        if banker_draws(banker, player_third):
            banker_third = [shoe.pop()]
            banker.append(banker_third[0])

        p_total = total(player)
        b_total = total(banker)

        if p_total > b_total:
            return "Player"
        elif b_total > p_total:
            return "Banker"
        else:
            return "Tie"

def simulate_strategy(rounds=1000, base_bet=10, strategy="fixed", initial_funds=1000,
                      bet_target="Player", rebate_rate=0.0):
    shoe = create_shoe()
    balance = initial_funds
    bet = base_bet
    history = [balance]
    stats = Counter()
    last_result = "Player"

    total_bet = 0
    total_payout = 0
    total_rebate = 0
    actual_bet_rounds = 0

    for _ in range(rounds):
        if balance < bet:
            break

        result = play_game_from_shoe(shoe)
        stats[result] += 1

        current_bet = last_result if bet_target == "Follow" and last_result != "Tie" else bet_target
        payout = 0
        win = False
        actual_bet_rounds += 1
        total_bet += bet

        if result == current_bet:
            payout = bet * 1.95 if current_bet == "Banker" else bet * 2
            win = True
        elif result == "Tie":
            payout = bet
            win = True
        else:
            payout = 0
            win = False

        rebate = bet * rebate_rate
        total_rebate += rebate

        total_payout += payout
        balance = balance - bet + payout + rebate
        history.append(balance)
        last_result = result

        bet = base_bet if strategy == "fixed" or win else min(balance, bet * 2)
        if balance <= 0:
            break

    return history, stats, total_bet, total_payout, total_rebate, actual_bet_rounds

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/simulate", methods=["POST"])
def simulate():
    data = request.form
    rounds = int(data.get("rounds", 1000))
    base_bet = int(data.get("base_bet", 10))
    initial_funds = int(data.get("initial_funds", 1000))
    strategy = data.get("strategy", "fixed")
    bet_target = data.get("bet_target", "Player")
    rebate_rate = float(data.get("rebate_rate", 0.0))

    history, stats, tb, tp, tr, ab = simulate_strategy(rounds, base_bet, strategy, initial_funds, bet_target, rebate_rate)
    rtp_base = tp / tb if tb > 0 else 0
    rtp_total = (tp + tr) / tb if tb > 0 else 0

    # 產生圖表
    fig, ax = plt.subplots()
    ax.plot(history)
    ax.set_title("Funds-Games")
    ax.set_xlabel("Games")
    ax.set_ylabel("Funds")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()

    return jsonify({
        "chart": chart_base64,
        "result": {
            "Banker": stats["Banker"],
            "Player": stats["Player"],
            "Tie": stats["Tie"],
            "actual_bets": ab,
            "total_bet": tb,
            "total_payout": tp,
            "total_rebate": tr,
            "rtp_base": f"{rtp_base:.2%}",
            "rtp_total": f"{rtp_total:.2%}",
            "final_balance": history[-1]
        }
    })

if __name__ == "__main__":
    app.run(debug=True)
