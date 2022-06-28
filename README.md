# About
Create relationship graph from Facebook friends.

### Features
- No **API keys** are needed.
- Data can be opened in **Obsidian** to show **graph with connections**.
- Currently only **Windows** is supported.

# Requirements
- [Python 3](https://python.org)
- [Firefox](https://firefox.com)
- [Obsidian](https://obsidian.md)

# Setup
Go to project directory.\
Install required Python modules:
```
pip3 install -r .\requirements.txt
```
Download [Firefox webdriver](https://github.com/mozilla/geckodriver/releases) and extract to project directory.\
Login to Facebook and save session:
```
py .\login.py
```

# Usage

### Example usage
Get *username*'s friends and their friends:
```
py .\main.py "username" --depth 2
```
Now you can open output folder `Friends` in Obsidian as a vault and see the [graph view](https://help.obsidian.md/Plugins/Graph+view).

### Blacklist
You can blacklist usernames from scanning by creating `blacklist.txt` (usernames separated with newlines) or from other file with `--blacklist /path/to/file.txt`.

### Clear data
To clear all collected data:
```
rm .\Friends\*.md
```

### Help
Check more info about usage with `--help`.
