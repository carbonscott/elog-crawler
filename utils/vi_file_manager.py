import sqlite3
from ascii_graph import Pyasciigraph
import argparse

def fetch_data(db_file, experiment_id):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            run_number,
            ROUND(total_size_bytes / 1000000000.0, 2) AS total_size_gb
        FROM FileManager
        WHERE experiment_id LIKE ?
        ORDER BY run_number
    """, ('%' + experiment_id + '%',))
    data = cursor.fetchall()
    conn.close()
    return data

def plot_ascii(run_numbers, total_sizes):
    graph = Pyasciigraph()
    data_for_ascii = [(f'Run {run}', size) for run, size in zip(run_numbers, total_sizes)]
    for line in graph.graph('Run Number vs Total Size (GB)', data_for_ascii):
        print(line)

def plot_ascii(run_numbers, total_sizes):
    max_size = max(total_sizes)
    max_bar_width = 40

    print("\nRun Number vs Total Size (GB)")
    print("------------------------------")
    print("Run Number | Total Size (GB) | Bar Graph")
    print("-----------|-----------------|-" + "-" * max_bar_width)

    for run, size in zip(run_numbers, total_sizes):
        bar_width = int((size / max_size) * max_bar_width)
        bar = '█' * bar_width
        print(f"{run:10} | {size:15.2f} | {bar}")

def main():
    parser = argparse.ArgumentParser(description='Plot data from SQLite database')
    parser.add_argument('db_file', help='Path to the SQLite database file')
    parser.add_argument('experiment_id', help='Experiment ID to filter data')
    args = parser.parse_args()

    data = fetch_data(args.db_file, args.experiment_id)
    run_numbers = [row[0] for row in data]
    total_sizes = [row[1] for row in data]

    plot_ascii(run_numbers, total_sizes)

if __name__ == "__main__":
    main()
