"""
SCHEMA

-- Experiment Table (from info file)
CREATE TABLE Experiment (
    experiment_id TEXT PRIMARY KEY,
    name TEXT,
    instrument TEXT,
    start_time DATETIME,
    end_time DATETIME,
    pi TEXT,
    pi_email TEXT,
    leader_account TEXT,
    description TEXT,
    slack_channels TEXT,
    analysis_queues TEXT,
    urawi_proposal TEXT
);

CREATE TABLE ExperimentTabs (
    tab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    tab_name TEXT,
    tab_content TEXT,
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
);

-- Run Table (combines info from file_manager, runtable, and logbook)
CREATE TABLE Run (
    run_number INTEGER PRIMARY KEY,
    experiment_id TEXT,
    start_time DATETIME,
    end_time DATETIME,
    n_events INTEGER,
    n_damaged INTEGER,
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
);

-- Detector Table (from runtable)
CREATE TABLE Detector (
    detector_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    run_number INTEGER,
    detector_name TEXT,
    status TEXT,
    FOREIGN KEY (run_number) REFERENCES Run(run_number),
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
);

-- Logbook Table
CREATE TABLE Logbook (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    run_number INTEGER,
    timestamp DATETIME,
    content TEXT,
    tags TEXT,
    author TEXT,
    FOREIGN KEY (run_number) REFERENCES Run(run_number),
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
);

-- DataProduction Table (from runtable)
CREATE TABLE DataProduction (
    production_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    run_number INTEGER,
    n_events INTEGER,
    n_damaged INTEGER,
    n_dropped INTEGER,
    prod_start DATETIME,
    prod_end DATETIME,
    FOREIGN KEY (run_number) REFERENCES Run(run_number),
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
);

-- FileManager Table (new table for file manager data)
CREATE TABLE FileManager (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    run_number INTEGER,
    number_of_files INTEGER,
    total_size_bytes INTEGER,
    FOREIGN KEY (run_number) REFERENCES Run(run_number),
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
);
"""

import sqlite3
import json
import csv
from datetime import datetime
import os
import argparse
import logging
import sys

csv.field_size_limit(sys.maxsize)

class ExperimentDBManager:
    def __init__(self, db_name='experiment_database.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Dictionary mapping file types to processing methods
        self.file_processors = {
            'info'        : self.process_info_file,
            'file_manager': self.process_file_manager,
            'logbook'     : self.process_logbook,
            'runtable'    : self.process_runtable
        }

        # Dictionary mapping file extensions to file types
        self.file_types = {
            '.info.json'       : 'info',
            '.file_manager.csv': 'file_manager',
            '.logbook.csv'     : 'logbook',
            '.runtable.json'   : 'runtable'
        }

    def create_tables(self):
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS Experiment (
                experiment_id TEXT PRIMARY KEY,
                name TEXT,
                instrument TEXT,
                start_time DATETIME,
                end_time DATETIME,
                pi TEXT,
                pi_email TEXT,
                leader_account TEXT,
                description TEXT,
                slack_channels TEXT,
                analysis_queues TEXT,
                urawi_proposal TEXT
            );

            CREATE TABLE IF NOT EXISTS ExperimentTabs (
                tab_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT,
                tab_name TEXT,
                tab_content TEXT,
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS Run (
                run_number INTEGER PRIMARY KEY,
                experiment_id TEXT,
                start_time DATETIME,
                end_time DATETIME,
                n_events INTEGER,
                n_damaged INTEGER,
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS Detector (
                detector_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT,
                run_number INTEGER,
                detector_name TEXT,
                status TEXT,
                FOREIGN KEY (run_number) REFERENCES Run(run_number),
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS Logbook (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT,
                run_number INTEGER,
                timestamp DATETIME,
                content TEXT,
                tags TEXT,
                author TEXT,
                FOREIGN KEY (run_number) REFERENCES Run(run_number),
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS DataProduction (
                production_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT,
                run_number INTEGER,
                n_events INTEGER,
                n_damaged INTEGER,
                n_dropped INTEGER,
                prod_start DATETIME,
                prod_end DATETIME,
                FOREIGN KEY (run_number) REFERENCES Run(run_number),
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS FileManager (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT,
                run_number INTEGER,
                number_of_files INTEGER,
                total_size_bytes INTEGER,
                FOREIGN KEY (run_number) REFERENCES Run(run_number),
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );
        ''')
        self.conn.commit()

    def parse_json(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logging.error(f"Error parsing JSON file: {file_path}")
            return None
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return None

    def parse_csv(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return list(csv.DictReader(file))
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return None

    def parse_main_content(self, main_content):
        lines = main_content.split('\n')
        parsed_content = {}
        current_key = None
        current_value = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this line defines a new key (ends with a colon)
            if line.endswith(':'):
                # Save previous key-value pair if exists
                if current_key:
                    parsed_content[current_key] = ' '.join(current_value).strip()

                # Set new key (remove the trailing colon)
                current_key = line[:-1].strip()
                current_value = []

                # Look ahead to the next line for the value
                i += 1
                while i < len(lines) and not lines[i].endswith(':'):
                    current_value.append(lines[i].strip())
                    i += 1

                # Step back one since we'll increment in the main loop
                if i < len(lines):
                    i -= 1
            else:
                # If line doesn't define a key but there's a current key,
                # add it to the current value
                if current_key:
                    current_value.append(line)

            i += 1

        # Don't forget to add the last key-value pair
        if current_key:
            parsed_content[current_key] = ' '.join(current_value).strip()

        return parsed_content

    def insert_experiment(self, data):
        try:
            main_content = self.parse_main_content(data.get('main_content', ''))
            self.cursor.execute('''
                INSERT OR REPLACE INTO Experiment 
                (experiment_id, name, instrument, start_time, end_time, pi, pi_email, leader_account, description, slack_channels, analysis_queues, urawi_proposal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('experiment_id'),
                main_content.get('Name'),
                main_content.get('Instrument'),
                main_content.get('Start Time'),
                main_content.get('End Time'),
                main_content.get('PI'),
                main_content.get('PI Email'),
                main_content.get('Leader Account'),
                main_content.get('Description'),
                main_content.get('Slack channels'),
                main_content.get('Analysis Queues'),
                main_content.get('URAWI Proposal')
            ))

            # Insert tab information
            tabs = data.get('tabs', {})
            for tab_name, tab_content in tabs.items():
                self.cursor.execute('''
                    INSERT OR REPLACE INTO ExperimentTabs
                    (experiment_id, tab_name, tab_content)
                    VALUES (?, ?, ?)
                ''', (data.get('experiment_id'), tab_name, json.dumps(tab_content)))

            ## self.conn.commit()
            logging.info(f"Inserted experiment: {data.get('experiment_id')}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting experiment data: {e}")
        except Exception as e:
            logging.error(f"Unexpected error inserting experiment data: {e}")

    def insert_run(self, data):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO Run 
                (run_number, experiment_id, start_time, end_time, n_events, n_damaged)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('Run'),  # Changed from 'run_number' to 'Run'
                data.get('experiment_id'),
                data.get('start_time'),
                data.get('end_time'),
                data.get('n_events'),
                data.get('n_damaged')
            ))
            ## self.conn.commit()
            logging.info(f"Inserted run: {data.get('Run')}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting run data: {e}")
        except Exception as e:
            logging.error(f"Unexpected error inserting run data: {e}")

    def insert_detector(self, data):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO Detector 
                (experiment_id, run_number, detector_name, status)
                VALUES (?, ?, ?, ?)
            ''', (
                data.get('experiment_id'),
                data.get('run_number'),
                data.get('detector_name'),
                data.get('status')
            ))
            ## self.conn.commit()
            logging.info(f"Inserted detector: {data.get('detector_name')} for run {data.get('run_number')}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting detector data: {e}")
        except Exception as e:
            logging.error(f"Unexpected error inserting detector data: {e}")

    def insert_logbook(self, data):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO Logbook 
                (experiment_id, run_number, timestamp, content, tags, author)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('experiment_id'),
                data.get('run_number'),
                data.get('timestamp'),
                data.get('content'),
                data.get('tags'),
                data.get('author')
            ))
            ## self.conn.commit()
            logging.info(f"Inserted logbook entry for run {data.get('run_number')}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting logbook data: {e}")
        except Exception as e:
            logging.error(f"Unexpected error inserting logbook data: {e}")

    def insert_data_production(self, data):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO DataProduction 
                (experiment_id, run_number, n_events, n_damaged, n_dropped, prod_start, prod_end)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('experiment_id'),
                data.get('run_number'),
                data.get('n_events'),
                data.get('n_damaged'),
                data.get('n_dropped'),
                data.get('prod_start'),
                data.get('prod_end')
            ))
            ## self.conn.commit()
            logging.info(f"Inserted data production for run {data.get('run_number')}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting data production: {e}")
        except Exception as e:
            logging.error(f"Unexpected error inserting data production: {e}")

    def insert_file_manager(self, data):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO FileManager 
                (experiment_id, run_number, number_of_files, total_size_bytes)
                VALUES (?, ?, ?, ?)
            ''', (
                data.get('experiment_id'),
                data.get('run_number'),
                data.get('number_of_files'),
                data.get('total_size_bytes')
            ))
            ## self.conn.commit()
            logging.info(f"Inserted file manager data for run {data.get('run_number')}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting file manager data: {e}")
        except Exception as e:
            logging.error(f"Unexpected error inserting file manager data: {e}")

    def process_info_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            if data:
                experiment_id = os.path.basename(file_path).split('.')[0]
                data['experiment_id'] = experiment_id
                self.insert_experiment(data)
                logging.info(f"Processed info file: {file_path}")
            else:
                logging.warning(f"No data found in info file: {file_path}")
        except json.JSONDecodeError:
            logging.error(f"Error parsing JSON file: {file_path}")
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
        except Exception as e:
            logging.error(f"Unexpected error processing info file: {e}")

    def process_file_manager(self, file_path):
        data = self.parse_csv(file_path)
        if data:
            experiment_id = os.path.basename(file_path).split('.')[0]
            for row in data:
                self.insert_run(row)
                self.insert_file_manager({
                    'experiment_id' : experiment_id,
                    'run_number': row['Run Number'],
                    'number_of_files': row['Number of Files'],
                    'total_size_bytes': row['Total Size (bytes)']
                })
            logging.info(f"Processed file manager: {file_path}")
        else:
            logging.warning(f"Failed to process file manager: {file_path}")

    def process_logbook(self, file_path):
        data = self.parse_csv(file_path)
        if data:
            experiment_id = os.path.basename(file_path).split('.')[0]
            last_run_number = None
            for row in data:
                if row['Run']:
                    last_run_number = int(row['Run'])
                if last_run_number is not None:
                    self.insert_logbook({
                        'experiment_id': experiment_id,
                        'run_number': last_run_number,
                        'timestamp': row['Posted'],
                        'content': row['Content'],
                        'tags': row['Tags'],
                        'author': row['Author']
                    })
            logging.info(f"Processed logbook: {file_path}")
        else:
            logging.warning(f"Failed to process logbook: {file_path}")

    def process_runtable(self, file_path):
        data = self.parse_json(file_path)
        if data:
            experiment_id = os.path.basename(file_path).split('.')[0]
            for run in data.get('Data Production', []):
                self.insert_run({
                    'experiment_id': experiment_id,
                    'Run': run.get('Run'),
                    'start_time': None,
                    'end_time': None,
                    'n_events': run.get('N events'),
                    'n_damaged': run.get('N damaged')
                })
                self.insert_data_production({
                    'experiment_id': experiment_id,
                    'run_number'   : run.get('Run', None),
                    'n_events'     : run.get('N events', None),
                    'n_damaged'    : run.get('N damaged', None),
                    'n_dropped'    : run.get('N dropped', None),
                    'prod_start'   : run.get('Prod Start', None),
                    'prod_end'     : run.get('Prod End', None),
                })
            for detector in data.get('Detectors', []):
                for key, value in detector.items():
                    if key != 'Run' and value == 'Checked':
                        self.insert_detector({
                            'experiment_id': experiment_id,
                            'run_number': detector['Run'],
                            'detector_name': key,
                            'status': value
                        })
            logging.info(f"Processed runtable: {file_path}")
        else:
            logging.warning(f"Failed to process runtable: {file_path}")

    def process_file(self, file_path):
        file_type = self.get_file_type(file_path)
        processor = self.file_processors.get(file_type)
        if processor:
            self.conn.execute('BEGIN TRANSACTION')
            try:
                processor(file_path)
                self.conn.commit()
                logging.info(f"Successfully processed and committed: {file_path}")
            except Exception as e:
                self.conn.rollback()
                logging.error(f"Error processing {file_path}, transaction rolled back: {e}")
        else:
            logging.warning(f"Unknown file type: {file_path}")

    def get_file_type(self, file_path):
        for extension, file_type in self.file_types.items():
            if file_path.endswith(extension):
                return file_type
        return 'unknown'

    def close(self):
        self.conn.close()

def main():
    parser = argparse.ArgumentParser(description="Process experiment files and update the database.")
    parser.add_argument('files', nargs='+', help="Paths to the input files")
    parser.add_argument('--db', default='experiment_database.db', help="Path to the SQLite database file")
    args = parser.parse_args()

    db_manager = ExperimentDBManager(args.db)

    for file_path in args.files:
        db_manager.process_file(file_path)

    db_manager.close()

if __name__ == "__main__":
    main()
