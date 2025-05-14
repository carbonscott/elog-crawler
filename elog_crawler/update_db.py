import sqlite3
import json
import csv
import os
import argparse
import logging
import sys
from .save_to_db import ExperimentDBManager

class DatabaseUpdater(ExperimentDBManager):
    def __init__(self, db_name):
        # Initialize with parent constructor but ensure the database exists
        if not os.path.exists(db_name):
            raise FileNotFoundError(f"Database file not found: {db_name}")
        super().__init__(db_name)
        logging.info(f"Connected to existing database: {db_name}")

        # Override the file processors to use update methods
        self.file_processors = {
            'info'        : self.process_info_file,
            'file_manager': self.process_file_manager,
            'logbook'     : self.process_logbook,
            'runtable'    : self.process_runtable
        }

    def update_experiment(self, data):
        """Update experiment information if it exists, otherwise insert new record"""
        try:
            # Check if experiment exists
            self.cursor.execute(
                "SELECT experiment_id FROM Experiment WHERE experiment_id = ?",
                (data.get('experiment_id'),)
            )
            exists = self.cursor.fetchone()

            main_content = self.parse_main_content(data.get('main_content', ''))

            if exists:
                # Update existing record
                self.cursor.execute('''
                    UPDATE Experiment
                    SET name=?, instrument=?, start_time=?, end_time=?, pi=?,
                        pi_email=?, leader_account=?, description=?,
                        slack_channels=?, analysis_queues=?, urawi_proposal=?
                    WHERE experiment_id=?
                ''', (
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
                    main_content.get('URAWI Proposal'),
                    data.get('experiment_id')
                ))
                logging.info(f"Updated experiment: {data.get('experiment_id')}")
            else:
                # Insert new record
                super().insert_experiment(data)

            # Update tab information - first delete existing tabs for this experiment
            self.cursor.execute(
                "DELETE FROM ExperimentTabs WHERE experiment_id = ?",
                (data.get('experiment_id'),)
            )

            # Then insert updated tabs
            tabs = data.get('tabs', {})
            for tab_name, tab_content in tabs.items():
                self.cursor.execute('''
                    INSERT INTO ExperimentTabs
                    (experiment_id, tab_name, tab_content)
                    VALUES (?, ?, ?)
                ''', (data.get('experiment_id'), tab_name, json.dumps(tab_content)))

        except sqlite3.Error as e:
            logging.error(f"Error updating experiment data: {e}")
            raise

    def update_run(self, data):
        """Update run information if it exists, otherwise insert new record"""
        try:
            # Check if run exists
            self.cursor.execute(
                "SELECT run_number FROM Run WHERE run_number = ? AND experiment_id = ?",
                (data.get('Run'), data.get('experiment_id'))
            )
            exists = self.cursor.fetchone()

            if exists:
                # Update existing record
                self.cursor.execute('''
                    UPDATE Run
                    SET start_time=?, end_time=?, n_events=?, n_damaged=?
                    WHERE run_number=? AND experiment_id=?
                ''', (
                    data.get('start_time'),
                    data.get('end_time'),
                    data.get('n_events'),
                    data.get('n_damaged'),
                    data.get('Run'),
                    data.get('experiment_id')
                ))
                logging.info(f"Updated run: {data.get('Run')}")
            else:
                # Insert new record
                super().insert_run(data)
        except sqlite3.Error as e:
            logging.error(f"Error updating run data: {e}")
            raise

    def update_detector(self, data):
        """Update detector information if it exists, otherwise insert new record"""
        try:
            self.cursor.execute(
                "SELECT detector_id FROM Detector WHERE run_number = ? AND experiment_id = ? AND detector_name = ?",
                (data.get('run_number'), data.get('experiment_id'), data.get('detector_name'))
            )
            exists = self.cursor.fetchone()

            if exists:
                self.cursor.execute('''
                    UPDATE Detector
                    SET status=?
                    WHERE run_number=? AND experiment_id=? AND detector_name=?
                ''', (
                    data.get('status'),
                    data.get('run_number'),
                    data.get('experiment_id'),
                    data.get('detector_name')
                ))
                logging.info(f"Updated detector {data.get('detector_name')} for run {data.get('run_number')}")
            else:
                super().insert_detector(data)
        except sqlite3.Error as e:
            logging.error(f"Error updating detector data: {e}")
            raise

    def update_logbook(self, data):
        """Update logbook information if it exists, otherwise insert new record"""
        try:
            # For logbook entries, we need a more complex check because they don't have a unique ID
            # Let's use run_number, timestamp, and author as a composite key
            self.cursor.execute(
                "SELECT log_id FROM Logbook WHERE run_number = ? AND timestamp = ? AND author = ? AND experiment_id = ?",
                (data.get('run_number'), data.get('timestamp'), data.get('author'), data.get('experiment_id'))
            )
            exists = self.cursor.fetchone()

            if exists:
                log_id = exists[0]
                self.cursor.execute('''
                    UPDATE Logbook
                    SET content=?, tags=?
                    WHERE log_id=?
                ''', (
                    data.get('content'),
                    data.get('tags'),
                    log_id
                ))
                logging.info(f"Updated logbook entry {log_id} for run {data.get('run_number')}")
            else:
                super().insert_logbook(data)
        except sqlite3.Error as e:
            logging.error(f"Error updating logbook data: {e}")
            raise

    def update_data_production(self, data):
        """Update data production information if it exists, otherwise insert new record"""
        try:
            self.cursor.execute(
                "SELECT production_id FROM DataProduction WHERE run_number = ? AND experiment_id = ?",
                (data.get('run_number'), data.get('experiment_id'))
            )
            exists = self.cursor.fetchone()

            if exists:
                production_id = exists[0]
                self.cursor.execute('''
                    UPDATE DataProduction
                    SET n_events=?, n_damaged=?, n_dropped=?, prod_start=?, prod_end=?
                    WHERE production_id=?
                ''', (
                    data.get('n_events'),
                    data.get('n_damaged'),
                    data.get('n_dropped'),
                    data.get('prod_start'),
                    data.get('prod_end'),
                    production_id
                ))
                logging.info(f"Updated data production for run {data.get('run_number')}")
            else:
                super().insert_data_production(data)
        except sqlite3.Error as e:
            logging.error(f"Error updating data production data: {e}")
            raise

    def update_file_manager(self, data):
        """Update file manager information if it exists, otherwise insert new record"""
        try:
            self.cursor.execute(
                "SELECT file_id FROM FileManager WHERE run_number = ? AND experiment_id = ?",
                (data.get('run_number'), data.get('experiment_id'))
            )
            exists = self.cursor.fetchone()

            if exists:
                file_id = exists[0]
                self.cursor.execute('''
                    UPDATE FileManager
                    SET number_of_files=?, total_size_bytes=?
                    WHERE file_id=?
                ''', (
                    data.get('number_of_files'),
                    data.get('total_size_bytes'),
                    file_id
                ))
                logging.info(f"Updated file manager for run: {data.get('run_number')}")
            else:
                super().insert_file_manager(data)
        except sqlite3.Error as e:
            logging.error(f"Error updating file manager data: {e}")
            raise

    # Override the process methods to use the update methods

    def process_info_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            if data:
                experiment_id = os.path.basename(file_path).split('.')[0]
                data['experiment_id'] = experiment_id
                self.update_experiment(data)  # Use update instead of insert
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
                run_data = {
                    'experiment_id': experiment_id,
                    'Run': row['Run Number'],
                    'start_time': None,  # We don't have this info from file_manager
                    'end_time': None,
                    'n_events': None,
                    'n_damaged': None
                }
                self.update_run(run_data)  # Use update instead of insert

                file_manager_data = {
                    'experiment_id': experiment_id,
                    'run_number': row['Run Number'],
                    'number_of_files': row['Number of Files'],
                    'total_size_bytes': row['Total Size (bytes)']
                }
                self.update_file_manager(file_manager_data)  # Use update instead of insert
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
                    logbook_data = {
                        'experiment_id': experiment_id,
                        'run_number': last_run_number,
                        'timestamp': row['Posted'],
                        'content': row['Content'],
                        'tags': row['Tags'],
                        'author': row['Author']
                    }
                    self.update_logbook(logbook_data)  # Use update instead of insert
            logging.info(f"Processed logbook: {file_path}")
        else:
            logging.warning(f"Failed to process logbook: {file_path}")

    def process_runtable(self, file_path):
        data = self.parse_json(file_path)
        if data:
            experiment_id = os.path.basename(file_path).split('.')[0]

            # Process Data Production
            for run in data.get('Data Production', []):
                data_production_data = {
                    'experiment_id': experiment_id,
                    'run_number': run.get('Run', None),
                    'n_events': run.get('N events', None),
                    'n_damaged': run.get('N damaged', None),
                    'n_dropped': run.get('N dropped', None),
                    'prod_start': run.get('Prod Start', None),
                    'prod_end': run.get('Prod End', None),
                }
                self.update_data_production(data_production_data)  # Use update instead of insert

            # Process Detectors
            for detector in data.get('Detectors', []):
                for key, value in detector.items():
                    if key != 'Run' and value == 'Checked':
                        detector_data = {
                            'experiment_id': experiment_id,
                            'run_number': detector['Run'],
                            'detector_name': key,
                            'status': value
                        }
                        self.update_detector(detector_data)  # Use update instead of insert

            logging.info(f"Processed runtable: {file_path}")
        else:
            logging.warning(f"Failed to process runtable: {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Update experiment database with new data.")
    parser.add_argument('--db_file', required=True, help="Path to the existing SQLite database file")
    parser.add_argument('--files', required=True, nargs='+', help="Paths to the input files for updating the database")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        db_updater = DatabaseUpdater(args.db_file)

        for file_path in args.files:
            if os.path.exists(file_path):
                logging.info(f"Processing file: {file_path}")
                db_updater.process_file(file_path)
            else:
                logging.error(f"File not found: {file_path}")

        db_updater.close()
        logging.info("Database update completed successfully.")

    except FileNotFoundError as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
