## How to run

python src/cli.py 

or if you jus want to use the scheduler module

python -i src/scheduler.py




## How to run tests locally

set PYTHONPATH=src
python -m pytest -q


## Complexity Notes
Briefly justify:

- Each queue is implemented as a simple FIFO list (acting like a circular buffer) that stores Task objects with remaining time.

- enqueue() and dequeue() → amortized O(1)

run() → O(#turns + total_minutes_worked) since each operation per task or turn is constant.

- O(N) — where N is the total number of active tasks plus small metadata (queues, counters, flags).
