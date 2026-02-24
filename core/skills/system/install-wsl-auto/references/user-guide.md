# WSL User Quick Reference

## Opening WSL

**Method 1:** Type `wsl` in Command Prompt or PowerShell
```cmd
wsl
```

**Method 2:** Click "Ubuntu" (or your distro name) in Start menu

**Method 3:** Windows Terminal (if installed)
- Has Ubuntu tab built-in

**Method 4:** Right-click in folder (Windows 11)
- Right-click folder → "Open in Terminal" → Select Ubuntu tab

---

## Basic Linux Commands

### Navigation
```bash
pwd                 # Show current directory
ls                  # List files and folders
ls -la              # List all files including hidden, with details
cd folder           # Change to folder
cd ..               # Go up one directory
cd ~                # Go to home directory
cd /mnt/c           # Go to Windows C: drive
```

### File Operations
```bash
mkdir folder        # Create folder
touch file.txt      # Create empty file
cp file.txt copy.txt    # Copy file
mv old.txt new.txt     # Rename/move file
rm file.txt         # Delete file
rm -r folder        # Delete folder and contents
cat file.txt        # Display file contents
nano file.txt       # Edit file (Ctrl+X to exit)
```

### File Information
```bash
ls -lh              # List with human-readable sizes
du -sh folder       # Show folder size
df -h               # Show disk space
```

---

## Installing Software

### APT Package Manager (Ubuntu/Debian)

```bash
# Update package list (do this first!)
sudo apt update

# Install a package
sudo apt install package-name

# Example: Install Node.js
sudo apt install nodejs

# Example: Install Python
sudo apt install python3 python3-pip

# Remove a package
sudo apt remove package-name

# Update all installed packages
sudo apt upgrade

# Full system upgrade
sudo apt update && sudo apt upgrade -y
```

### Common Packages

```bash
# Developer tools
sudo apt install build-essential  # C/C++ compiler
sudo apt install git              # Version control
sudo apt install curl             # Download files
sudo apt install wget             # Download files

# Languages
sudo apt install nodejs npm       # Node.js + npm
sudo apt install python3-pip      # Python + pip
sudo apt install ruby             # Ruby

# Utilities
sudo apt install htop             # System monitor
sudo apt install tree             # Directory tree view
sudo apt install unzip            # Unzip files
```

---

## Accessing Files

### Windows Files from WSL

Windows drives are at `/mnt/`:

```bash
# C: drive
cd /mnt/c

# Your Windows user folder
cd /mnt/c/Users/YourWindowsUsername

# Example: Desktop
cd /mnt/c/Users/YourWindowsUsername/Desktop

# Example: Documents
cd /mnt/c/Users/YourWindowsUsername/Documents
```

### WSL Files from Windows

**In File Explorer, type:**
```
\\wsl$\Ubuntu-22.04\home\username\
```

Or browse to:
```
\\wsl$\
```

You'll see all your WSL distributions.

**Tip:** Pin this to Quick Access for easy access!

---

## User & Permissions

### sudo (Administrator Access)

```bash
# Run command as administrator
sudo command

# Example: Install software
sudo apt install nodejs

# Example: Edit system file
sudo nano /etc/hosts

# Become root user
sudo su

# Exit root
exit
```

**Your password:**
- You set this during first WSL setup
- Won't show while typing (normal!)
- Just type and press Enter

### Change Password

```bash
passwd
# Enter old password
# Enter new password
# Confirm new password
```

### Forgot Password?

**From Windows PowerShell:**
```powershell
wsl -u root
# Now in WSL as root:
passwd your-username
# Enter new password
exit
```

---

## System Management

### Shutdown WSL

**From Windows PowerShell:**
```powershell
wsl --shutdown
```

This:
- Stops all WSL instances
- Frees up memory
- Good to do when finished

### Restart WSL

**From Windows PowerShell:**
```powershell
wsl --shutdown
wsl
```

### Update Ubuntu

```bash
sudo apt update        # Refresh package list
sudo apt upgrade       # Install updates
sudo apt autoremove    # Clean up old packages
```

---

## Network & Internet

### Check Internet Connection

```bash
ping -c 3 google.com
```

Should see responses. If not, see Troubleshooting.

### DNS Issues?

**Fix DNS:**
```bash
sudo nano /etc/resolv.conf

# Change to:
nameserver 8.8.8.8

# Save: Ctrl+X, Y, Enter
```

---

## Useful Tips

### Copy & Paste

**In WSL terminal:**
- **Copy:** Select text (auto-copies)
- **Paste:** Right-click or Ctrl+Shift+V

### Tab Completion

Press **Tab** to auto-complete:
```bash
cd /mnt/c/Us[TAB]    # Completes to "Users"
```

### Command History

- **Up arrow:** Previous command
- **Down arrow:** Next command
- `history`: Show command history
- `Ctrl+R`: Search command history

### Clear Screen

```bash
clear
# Or: Ctrl+L
```

### Stop Running Command

**Ctrl+C** - Stops current command

---

## File Paths

### WSL Path

```bash
/home/username/        # Your home directory (~)
/mnt/c/               # Windows C: drive
/etc/                 # System configuration
/tmp/                 # Temporary files
```

### Windows Path to WSL

```
C:\Users\You\AppData\Local\Packages\CanonicalGroupLimited...\LocalState\rootfs
```

**But use `\\wsl$\` instead!** Much easier.

---

## Getting Help

### Manual Pages

```bash
man command            # Show manual for command
man ls                # List manual
man cp                # Copy manual

# Navigate:
# Space - Next page
# b - Previous page
# q - Quit
```

### Command Help

```bash
command --help        # Show command help
ls --help
apt --help
```

### Search for Package

```bash
apt search keyword
# Example:
apt search python
```

---

## Common Tasks

### Create Project Folder

```bash
cd ~                  # Go home
mkdir projects        # Create folder
cd projects           # Enter folder
```

### Download File

```bash
wget https://example.com/file.zip
# or
curl -O https://example.com/file.zip
```

### Extract Archive

```bash
unzip file.zip                # Unzip
tar -xzf file.tar.gz         # Extract .tar.gz
tar -xjf file.tar.bz2        # Extract .tar.bz2
```

### Find Files

```bash
find . -name "*.txt"          # Find all .txt files
find /mnt/c -name "document.pdf"  # Find specific file
```

### Disk Usage

```bash
df -h                 # Show disk space
du -sh folder         # Show folder size
du -sh *              # Show size of all items
```

---

## Next Steps

**Learning Resources:**
- Linux Journey: https://linuxjourney.com
- Ubuntu tutorials: https://ubuntu.com/tutorials
- The Linux Command Line book (free PDF)

**What to learn:**
1. Basic navigation (cd, ls, pwd)
2. File operations (cp, mv, rm)
3. Package management (apt)
4. Text editing (nano or vim)
5. Permissions (chmod, chown)

**Practice:**
```bash
# Make a practice folder
mkdir ~/practice
cd ~/practice

# Create some files
touch test.txt
mkdir subfolder
cd subfolder
echo "Hello Linux!" > hello.txt
cat hello.txt
```

---

**Remember:**
- Google is your friend
- `--help` is built into most commands
- WSL is real Linux - most Linux tutorials work!
- Don't be afraid to experiment in your home directory

**Have fun exploring! 🐧**
