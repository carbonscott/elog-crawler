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

    # Similar update methods for other tables (logbook, detector, data_production, file_manager)
    # Each would check if the record exists and update or insert accordingly

    def update_file_manager(self, data):
        """Update file manager information if it exists, otherwise insert new record"""
        try:
            self.cursor.execute(
                "SELECT file_id FROM FileManager WHERE run_number = ? AND experiment_id = ?", 
                (data.get('run_number'), data.get('experiment_id'))
            )
            exists = self.cursor.fetchone()

            if exists:
                self.cursor.execute('''
                    UPDATE FileManager 
                    SET number_of_files=?, total_size_bytes=?
                    WHERE run_number=? AND experiment_id=?
                ''', (
                    data.get('number_of_files'),
                    data.get('total_size_bytes'),
                    data.get('run_number'),
                    data.get('experiment_id')
                ))
                logging.info(f"Updated file manager for run: {data.get('run_number')}")
            else:
                super().insert_file_manager(data)
        except sqlite3.Error as e:
            logging.error(f"Error updating file manager data: {e}")
            raise

    def process_file(self, file_path):
        """Override process_file to use update methods instead of insert methods"""
        file_type = self.get_file_type(file_path)
        processor = self.file_processors.get(file_type)

        if processor:
            self.conn.execute('BEGIN TRANSACTION')
            try:
                processor(file_path)
                self.conn.commit()
                logging.info(f"Successfully processed and committed updates from: {file_path}")
            except Exception as e:
                self.conn.rollback()
                logging.error(f"Error processing {file_path}, transaction rolled back: {e}")
        else:
            logging.warning(f"Unknown file type: {file_path}")

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
