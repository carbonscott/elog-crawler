# Elog-Crawler Installation Guide for macOS

This guide will help you install and set up the elog-crawler tool on your Mac to scrape experimental e-logbook data.

## Prerequisites

### 1. Install Conda

Conda is recommended for managing Python environments as it helps avoid conflicts with system Python:

```bash
# Download the Miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O ~/miniconda.sh
# Or for Apple Silicon Macs:
# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -O ~/miniconda.sh

# Run the installer
bash ~/miniconda.sh -b -p $HOME/miniconda

# Initialize conda in your shell
eval "$($HOME/miniconda/bin/conda shell.bash hook)"

# Add conda to your path permanently
conda init zsh  # or bash, depending on your shell
```

### 2. Install Chrome Browser

If you don't already have Google Chrome:

```bash
brew install --cask google-chrome
```

### 3. Install Homebrew (if needed)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Installation Steps

### 1. Create a Conda Environment

```bash
conda create -n elog-crawler python=3.9
conda activate elog-crawler
```

### 2. Download the elog-crawler

Clone the repository or download the code:

```bash
git clone <repository-url>
cd elog-crawler
```

### 3. Install Dependencies

```bash
pip install selenium pandas webdriver-manager cryptography humanfriendly
```

### 4. Install the Package

```bash
pip install -e .
```

## Usage

### Basic Commands

1. **Crawl e-Logbook entries**:

```bash
elog-crawler-logbook <experiment-id>
```

2. **Crawl File Manager data**:

```bash
elog-crawler-file-manager <experiment-id>
```

3. **Crawl Info page**:

```bash
elog-crawler-info <experiment-id>
```

4. **Crawl Run Table**:

```bash
elog-crawler-runtable <experiment-id>
```

5. **Save data to database**:

```bash
elog-crawler-save_to_db <path-to-files>
```

### Command Options

Reset credentials:

```bash
elog-crawler-logbook --reset-credentials
```

Run in GUI mode (non-headless):

```bash
elog-crawler-logbook --gui <experiment-id>
```

### Working with Multiple Experiments

You can process multiple experiments by providing space-separated IDs:

```bash
elog-crawler-logbook exp1 exp2 exp3
```

## Database Schema

The tool uses SQLite to store data with the following tables:
- Experiment - Basic experiment information
- ExperimentTabs - Content from experiment info tabs
- Run - Run details
- Detector - Detector status per run
- Logbook - E-logbook entries
- DataProduction - Run production statistics
- FileManager - File storage information

## Notes

- On first run, you'll be prompted to enter your credentials
- The tool will create encrypted credential storage for subsequent runs
- Data will be saved as CSV or JSON files in your current directory
- Using conda ensures isolation from your system Python, preventing potential conflicts

## Troubleshooting

If you encounter issues with ChromeDriver:

```bash
# Install ChromeDriver manually
brew install --cask chromedriver

# Ensure it's in your PATH
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.zshrc
source ~/.zshrc
```

For permission issues with ChromeDriver, run:

```bash
xattr -d com.apple.quarantine $(which chromedriver)
```

## Advanced Usage

To visualize file manager data from the database:

```bash
python utils/vi_file_manager.py experiment_database.db <experiment_id>
```
