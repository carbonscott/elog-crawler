# Elog-Crawler Installation Guide for Windows

This guide will help you install and set up the elog-crawler tool on Windows to scrape experimental e-logbook data.

## Prerequisites

### 1. Install Conda

Conda is recommended for managing Python environments as it helps avoid conflicts with system Python:

1. Download the Miniconda installer for Windows from [the official site](https://docs.conda.io/en/latest/miniconda.html)
2. Run the installer and follow the prompts
   - Recommended: Check the option to add Miniconda to your PATH variable
   - Recommended: Register Miniconda as your default Python
3. Open Anaconda Prompt from the Start menu after installation is complete

### 2. Install Google Chrome

If you don't already have Google Chrome:

1. Download Chrome from [https://www.google.com/chrome/](https://www.google.com/chrome/)
2. Run the installer and follow the prompts

Alternatively, if you have Windows Package Manager (winget) installed:

```cmd
winget install Google.Chrome
```

### 3. Install Git (Optional)

If you want to clone the repository:

1. Download Git from [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. Run the installer and use the default options

## Installation Steps

### 1. Create a Conda Environment

Open Anaconda Prompt and run:

```cmd
conda create -n elog-crawler python=3.9
conda activate elog-crawler
```

### 2. Download the elog-crawler

Using Git (if installed):

```cmd
git clone <repository-url>
cd elog-crawler
```

Or download the ZIP file from the repository and extract it, then navigate to the folder in Anaconda Prompt:

```cmd
cd path\to\elog-crawler
```

### 3. Install Dependencies

```cmd
pip install selenium pandas webdriver-manager cryptography humanfriendly
```

### 4. Install the Package

```cmd
pip install -e .
```

## Usage

Always make sure to activate your conda environment before running commands:

```cmd
conda activate elog-crawler
```

### Basic Commands

1. **Crawl e-Logbook entries**:

```cmd
elog-crawler-logbook <experiment-id>
```

2. **Crawl File Manager data**:

```cmd
elog-crawler-file-manager <experiment-id>
```

3. **Crawl Info page**:

```cmd
elog-crawler-info <experiment-id>
```

4. **Crawl Run Table**:

```cmd
elog-crawler-runtable <experiment-id>
```

5. **Save data to database**:

```cmd
elog-crawler-save_to_db <path-to-files>
```

### Command Options

Reset credentials:

```cmd
elog-crawler-logbook --reset-credentials
```

Run in GUI mode (non-headless):

```cmd
elog-crawler-logbook --gui <experiment-id>
```

### Working with Multiple Experiments

You can process multiple experiments by providing space-separated IDs:

```cmd
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

## Troubleshooting

### ChromeDriver Issues

If WebDriver Manager fails to set up ChromeDriver automatically:

1. Download ChromeDriver manually from [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
   - Make sure to download the version that matches your Chrome browser
2. Extract the ZIP file and place chromedriver.exe in a directory of your choice
3. Add that directory to your PATH:
   - Right-click on 'This PC' or 'My Computer'
   - Click 'Properties' → 'Advanced system settings' → 'Environment Variables'
   - Under "System variables" find the "Path" variable and click Edit
   - Click "New" and add the directory containing chromedriver.exe
   - Click OK on all dialog boxes
   - Restart your Anaconda Prompt

### Running as Administrator

If you encounter permission issues:
1. Close the Anaconda Prompt
2. Right-click on Anaconda Prompt in the Start menu
3. Select "Run as administrator"
4. Navigate back to your project directory and try again

### Firewall/Antivirus Issues

If your security software blocks ChromeDriver:
1. Add exceptions in your antivirus for ChromeDriver
2. Allow ChromeDriver through Windows Defender Firewall if prompted

## Notes

- On first run, you'll be prompted to enter your credentials
- The tool will create encrypted credential storage for subsequent runs
- Data will be saved as CSV or JSON files in your current directory
- The Windows command prompt uses backslashes (`\`) in file paths, not forward slashes (`/`)

## Advanced Usage

To visualize file manager data from the database:

```cmd
python utils\vi_file_manager.py experiment_database.db <experiment_id>
```

## Updating the Tool

To update the tool to the latest version:

1. Navigate to the elog-crawler directory
2. Pull the latest changes (if using Git):
   ```cmd
   git pull
   ```
3. Update the installation:
   ```cmd
   pip install -e .
   ```
