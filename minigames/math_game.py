import random
import time
import threading
import queue

TOTAL_TIME = 30            # total time allowed
COINS_PER_CORRECT = 10     # base reward
FAST_BONUS_TIME = 10       # must answer within this sec for bonus
FAST_BONUS_COINS = 5       # bonus reward

def timed_input(prompt, timeout):
    """Reads input with timeout. Returns None if time exceeded."""
    q = queue.Queue()

    def _thread():
        try:
            q.put(input(prompt))
        except:
            q.put(None)

    threading.Thread(target=_thread, daemon=True).start()

    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None

def make_problem():
    """Produce integer-only multiplication or clean division."""
    if random.choice(["mul", "div"]) == "mul":
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        return f"{a} * {b}", a * b
    else:
        divisor = random.randint(2, 12)
        result = random.randint(2, 12)
        dividend = divisor * result
        return f"{dividend} / {divisor}", result

def run_quiz():
    problems = [make_problem() for _ in range(3)]
    answers = []
    correct_count = 0
    coins = 0

    print(f"You have {TOTAL_TIME} seconds to answer 3 questions.\n")

    start = time.monotonic()

    for i, (text, correct_answer) in enumerate(problems, start=1):
        elapsed = time.monotonic() - start
        remaining = TOTAL_TIME - elapsed

        if remaining <= 0:
            print("\nTime's up!")
            answers.extend([None] * (3 - len(answers)))
            break

        print(f"(Remaining total time: {remaining:.1f}s)")

        # Start timer for fast-answer bonus
        question_start = time.monotonic()

        user_in = timed_input(f"Q{i}: {text} = ", remaining)

        if user_in is None:
            print("\nTime's up for this question!")
            answers.append(None)
            answers.extend([None] * (3 - len(answers)))
            break

        try:
            user_ans = int(user_in.strip())
        except:
            user_ans = None

        answers.append(user_ans)

        time_taken = time.monotonic() - question_start

        if user_ans == correct_answer:
            print(" → Correct! +10 coins")

            coins += COINS_PER_CORRECT
            correct_count += 1

            if time_taken <= FAST_BONUS_TIME:
                coins += FAST_BONUS_COINS
                print(f" → Fast answer bonus! +{FAST_BONUS_COINS} coins (answered in {time_taken:.2f}s)")
            print()
        else:
            print(f" → Wrong. Correct answer: {correct_answer}\n")

    # Summary
    print("===== SUMMARY =====")
    for i, (text, correct_answer) in enumerate(problems, start=1):
        your = answers[i-1]
        shown = "(no answer)" if your is None else str(your)
        status = "OK" if your == correct_answer else "WRONG"
        print(f"Q{i}: {text} = {correct_answer} | your answer: {shown} → {status}")

    print("-------------------")
    print(f"Correct answers: {correct_count} / 3")
    print(f"Total coins earned: {coins}")
    print(f"Total time used: {time.monotonic() - start:.2f}s")
    print("===================")

if __name__ == "__main__":
    run_quiz()
