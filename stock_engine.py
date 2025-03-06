import threading
import time
import csv
import ctypes
from queue import Queue
import random
from typing import Optional, List

# -------------------------
# Order & OrderBook Classes
# -------------------------


class OrderType:
    BUY = "BUY"
    SELL = "SELL"


class Order:
    def __init__(self, order_type: str, ticker: int, quantity: int, price: int):
        self.type = order_type
        self.ticker = ticker
        # Ensure quantity is at least 1
        self.quantity = max(1, quantity)
        self.price = price
        # Simulate an atomic pointer for the next order.
        self.next: ctypes.py_object = ctypes.py_object(None)
        # Each order has its own lock to ensure only one thread processes it at a time.
        self.lock = threading.Lock()

    def __str__(self) -> str:
        # Format the order as a table row.
        return f"{self.type:<6} | {self.ticker:<6} | {self.quantity:<8} | {self.price:<6}"


class OrderBook:
    def __init__(self):
        # Global pointer to the head of the order book (linked list).
        self.head: ctypes.py_object = ctypes.py_object(None)
        # Lock used for simulating atomic CAS operations.
        self._cas_lock = threading.Lock()

    def atomic_compare_and_swap(self, ptr: ctypes.py_object, old, new) -> bool:
        """Simulated atomic Compare-And-Swap (CAS) operation using a lock."""
        with self._cas_lock:
            if ptr.value is old:
                ptr.value = new
                return True
            return False

    def add_order(self, order: Order) -> None:
        """Lock-free insertion of an order into the order book."""
        while True:
            old_head = self.head.value
            order.next = ctypes.py_object(old_head)
            if self.atomic_compare_and_swap(self.head, old_head, order):
                print(f"🟢 Order Added:            {order}")
                return

    def match_order(self, incoming: Order, thread_id: int) -> bool:
        """
        Ensures that a BUY order is matched with the lowest SELL price available.
        Ensures that a SELL order is matched with the highest BUY price available.
        """
        prev = None
        best_match = None
        best_match_prev = None
        cur = self.head.value

        # Find the best matching order (lowest SELL for BUY, highest BUY for SELL)
        while cur is not None:
            # Skip orders that are already fully matched
            if cur.quantity <= 0:
                cur = cur.next.value if hasattr(
                    cur.next, 'value') else cur.next
                continue

            if ((incoming.type == OrderType.BUY and cur.type == OrderType.SELL and
                cur.ticker == incoming.ticker and cur.price <= incoming.price) or
                (incoming.type == OrderType.SELL and cur.type == OrderType.BUY and
                    cur.ticker == incoming.ticker and cur.price >= incoming.price)):

                # For BUY: Find the lowest SELL price
                # For SELL: Find the highest BUY price
                if best_match is None or \
                    (incoming.type == OrderType.BUY and cur.price < best_match.price) or \
                        (incoming.type == OrderType.SELL and cur.price > best_match.price):
                    best_match = cur
                    best_match_prev = prev

            prev = cur
            cur = cur.next.value if cur.next and hasattr(
                cur.next, 'value') else cur.next

        # If no best match is found, return
        if best_match is None:
            return False

        # Acquire lock before modifying best match
        with best_match.lock:
            traded_qty = min(incoming.quantity, best_match.quantity)
            if traded_qty == 0:
                return False  # Skip logging zero-quantity matches

            print(
                f"✅ [Thread {thread_id}] Match Found: {best_match} -> Traded {traded_qty} shares @ {best_match.price}")

            incoming.quantity -= traded_qty
            best_match.quantity -= traded_qty

            # Remove fully executed orders
            if best_match.quantity == 0:
                if best_match_prev is None:
                    self.atomic_compare_and_swap(self.head, best_match,
                                                 best_match.next.value if hasattr(best_match.next, 'value') else best_match.next)
                else:
                    best_match_prev.next = best_match.next

        return True

    def process_orders(self, thread_id: int) -> None:
        """Scan the order book to match orders."""
        cur: Optional[Order] = self.head.value
        while cur is not None:
            if cur.quantity > 0:
                if self.match_order(cur, thread_id):
                    # Restart scanning if a match occurred.
                    cur = self.head.value
                    continue
            cur = cur.next.value if cur.next and hasattr(
                cur.next, 'value') else cur.next

    def display(self, title: str = "Final Order Book") -> None:
        """Display the final state of the order book (only orders with positive quantity)."""
        orders: List[str] = []
        cur: Optional[Order] = self.head.value
        while cur:
            if cur.quantity > 0:
                orders.append(str(cur))
            cur = cur.next.value if cur.next and hasattr(
                cur.next, 'value') else cur.next
        Printer.print_table_header(title)
        if orders:
            for order in orders:
                print(order)
        else:
            print("📭 Order book is empty")
        print("-" * 50)

    def reset(self) -> None:
        """Reset the order book."""
        self.head.value = None

    def get_order_list(self) -> List[Order]:
        """Return a list of orders currently in the order book."""
        orders: List[Order] = []
        cur: Optional[Order] = self.head.value
        while cur:
            orders.append(cur)
            cur = cur.next.value if cur.next and hasattr(
                cur.next, 'value') else cur.next
        return orders

# -------------------------
# Printer Utility Class
# -------------------------


class Printer:
    @staticmethod
    def print_table_header(title: str = "Order Book") -> None:
        header = f"{'Type':<6} | {'Ticker':<6} | {'Qty':<8} | {'Price':<6}"
        line = "-" * len(header)
        print(f"\n📘 {title}")
        print(header)
        print(line)

    @staticmethod
    def print_trading_header(title: str = "Trading Simulation") -> None:
        header = " " * 27 + "Action" + " | " + \
            f"{'Ticker':<6} | {'Qty':<8} | {'Price':<6}"
        # print(f"\n📈 {title}")
        print(header)
        print("-" * len(header))

# -------------------------
# Trading Engine Class
# -------------------------


class TradingEngine:
    def __init__(self):
        self.order_book = OrderBook()
        self.order_queue: Queue = Queue()

    def load_orders_from_csv(self, filename: str) -> None:
        """Load orders from a CSV file into the order queue."""
        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                order_data = {
                    'order_type': row['order_type'].strip().upper(),
                    'ticker': int(row['ticker']),
                    'quantity': int(row['quantity']),
                    'price': int(row['price'])
                }
                self.order_queue.put(order_data)

    def process_dataset_orders(self, thread_id: int) -> None:
        """Worker function: process dataset orders from the queue."""
        while not self.order_queue.empty():
            order_data = self.order_queue.get()
            order = Order(order_data['order_type'],
                          order_data['ticker'],
                          order_data['quantity'],
                          order_data['price'])
            self.order_book.add_order(order)
            self.order_book.process_orders(thread_id)
            time.sleep(0.01)
        print(f"🚀 Dataset Thread {thread_id} done.")

    def simulate_random_trading(self, thread_id: int, iterations: int, ticker_range: int = 10) -> None:
        """Worker function: simulate random trading orders."""
        for _ in range(iterations):
            order = Order(
                random.choice([OrderType.BUY, OrderType.SELL]),
                # For higher match probability.
                random.randint(0, ticker_range),
                random.randint(1, 100),
                random.randint(1, 500)
            )
            self.order_book.add_order(order)
            self.order_book.process_orders(thread_id)
            time.sleep(0.01)
        print(f"🚀 Random Trading Thread {thread_id} done.")

# -------------------------
# Main Execution
# -------------------------


if __name__ == "__main__":
    engine = TradingEngine()

    # --- Part 1: Process dataset orders ---
    dataset_file = "orders.csv"  # Path to your CSV dataset
    print("📥 Loading dataset into queue...")
    engine.load_orders_from_csv(dataset_file)

    num_dataset_threads = 4
    dataset_threads = []
    Printer.print_trading_header("Dataset Trading Simulation")
    for i in range(num_dataset_threads):
        t = threading.Thread(target=engine.process_dataset_orders, args=(i,))
        dataset_threads.append(t)
        t.start()
    for t in dataset_threads:
        t.join()
    print("✅ Dataset processing completed.")
    engine.order_book.display("Final Order Book after Dataset Orders")
    engine.order_book.reset()

    # --- Part 2: Simulate random trading orders ---
    print("\n🔀 Simulating random trading orders...")
    num_random_threads = int(input("Enter number of random trading threads: "))
    iterations = int(input("Enter number of iterations per thread: "))
    # Random orders per thread
    # Ticker range for random
    ticker_range = int(input("Enter ticker range for random orders: "))
    random_threads = []
    Printer.print_trading_header("Random Trading Simulation")
    for i in range(num_random_threads):
        t = threading.Thread(
            target=engine.simulate_random_trading, args=(i, iterations, ticker_range))
        random_threads.append(t)
        t.start()
    for t in random_threads:
        t.join()
    print("🎯 All trading processing completed.")
    engine.order_book.display("Final Order Book after Random Trading")
