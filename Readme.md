# Real-Time Stock Trading Engine

### Problem Statement
This project implements a real-time stock trading engine that efficiently processes Buy and Sell orders while ensuring concurrent execution and fairness. The system adheres to the following core requirements:

1. **Order Management:**
   - Supports adding Buy and Sell orders with the parameters:
     - Order Type (`BUY` or `SELL`)
     - Ticker Symbol (Supports 1,024 tickers)
     - Quantity
     - Price
   - Simulates real-time stock transactions with randomly generated orders.

2. **Order Matching:**
   - Matches Buy orders with the lowest available Sell orders for the same ticker where the Buy price is greater than or equal to the Sell price.
   - Ensures fair execution using a lock-free order book structure.
   - Handles race conditions in a multi-threaded environment to prevent data corruption or duplicate processing.

3. **Performance Considerations:**
   - Uses lock-free linked lists for concurrent access.
   - Ensures that order matching occurs in O(n) time complexity.
   - Prevents the use of dictionaries, maps, or equivalent data structures to maintain a pure implementation.

---
## For Execution
```
python3 stock_engine.py
```
## System Architecture

### **1. Order Structure (`Order` Class)**

Each order represents a stock transaction request, containing essential attributes:
- `type`: Order type (`BUY` or `SELL`).
- `ticker`: Stock ticker ID (integer, range 0-1023).
- `quantity`: Number of shares in the order.
- `price`: Price per share.
- `next`: Pointer to the next order in the linked list (simulating a lock-free queue).
- `lock`: Per-order lock to handle concurrent processing.

### **2. Order Book (`OrderBook` Class)**

The `OrderBook` class maintains a lock-free linked list that stores all Buy and Sell orders. It provides:
- **`add_order(order: Order) -> None`**:
  - Inserts an order into the book while ensuring thread safety.
  - Uses a Compare-And-Swap (CAS) operation for atomic updates.
- **`match_order(incoming: Order, thread_id: int) -> bool`**:
  - Scans the order book for a matching order.
  - Matches Buy orders with the lowest Sell orders and vice versa.
  - Ensures atomic operations by locking individual orders using `with cur.lock:`.
  - Removes fully matched orders from the order book.
- **`process_orders(thread_id: int) -> None`**:
  - Iterates over the order book and calls `match_order` for each unprocessed order.
- **`display(title: str) -> None`**:
  - Displays the final state of the order book with unmatched orders.
- **`reset() -> None`**:
  - Clears the order book before new transactions begin.

### **3. Trading Engine (`TradingEngine` Class)**

The `TradingEngine` manages order processing and random order generation:
- **`load_orders_from_csv(filename: str) -> None`**:
  - Reads orders from a CSV file and queues them for processing.
- **`process_dataset_orders(thread_id: int) -> None`**:
  - Processes orders from the queue using multiple threads.
- **`simulate_random_trading(thread_id: int, iterations: int) -> None`**:
  - Generates random Buy/Sell orders and adds them to the order book.
  - Uses multiple threads to simulate concurrent trading.

### **4. Utility (`Printer` Class)**

Formats and prints structured output:
- **`print_table_header(title: str) -> None`**: Prints a header for order book tables.
- **`print_trading_header(title: str) -> None`**: Prints formatted trading simulation output.

---

## Order Matching Algorithm

### **Matching Rules**
1. **For `BUY` orders**:
   - Find the lowest `SELL` order for the same ticker where `SELL.price <= BUY.price`.
   - Trade up to the smaller of `BUY.quantity` or `SELL.quantity`.
   - If `SELL` order is fully executed, remove it.
   - If `BUY` order is fully executed, exit matching.

2. **For `SELL` orders**:
   - Find the highest `BUY` order for the same ticker where `BUY.price >= SELL.price`.
   - Trade up to the smaller of `BUY.quantity` or `SELL.quantity`.
   - If `BUY` order is fully executed, remove it.
   - If `SELL` order is fully executed, exit matching.

### **Concurrency & Thread Safety**
- Uses **per-order locks** (`with cur.lock:`) to prevent multiple threads from modifying the same order.
- Implements **Compare-And-Swap (CAS)** for atomic linked list updates.
- **Multiple threads** process orders in parallel without data corruption.

---

## Performance Analysis

### **Time Complexity**
- **`add_order`**: **O(1)** (Linked list insertion with CAS)
- **`match_order`**: **O(n)** (Iterating over orders to find a match)
- **`process_orders`**: **O(n²) worst-case** (if no immediate matches found)

### **Scalability**
- Lock-free linked lists ensure high concurrency.
- Per-order locking prevents race conditions in a multi-threaded environment.
- Efficient data structure allows real-time stock matching with minimal overhead.

---

## Example Execution

### **Input (orders.csv)**
```csv
order_type,ticker,quantity,price
BUY,100,50,200
SELL,100,50,190
BUY,101,60,300
SELL,101,40,250
SELL,105,40,250
BUY,105,70,300
```

### **Execution Output**
```
📥 Loading dataset into queue...
📈 Dataset Trading Simulation
🟢 Order Added: BUY    | 100    | 50      | 200   
🟢 Order Added: SELL   | 100    | 50      | 190   
✅ [Thread 1] Match Found: BUY    | 100    | 50      | 200   -> Traded 50 shares
...
📘 Final Order Book
SELL   | 105    | 10      | 240   
BUY    | 103    | 30      | 300   
SELL   | 102    | 50      | 150   
BUY    | 102    | 50      | 100   
```

