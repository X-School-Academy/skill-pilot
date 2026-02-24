# Common WSL Issues and Solutions

## Installation Issues

### Issue: "WSL not recognized" after installation

**Symptoms:**
- Command `wsl` says "not recognized"
- Installed but not working

**Solutions:**
1. **Restart computer** (required after first install)
2. Check if WSL feature is enabled:
   ```powershell
   Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
   ```
3. Re-enable if needed:
   ```powershell
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
   ```

---

### Issue: Error 0x80370102 - Virtual machine platform not enabled

**Cause:** Virtualization not enabled in BIOS/UEFI

**Solutions:**
1. **Enable virtualization in BIOS:**
   - Restart computer
   - Press BIOS key during startup (F2, Del, F10, F12 - varies by manufacturer)
   - Find "Virtualization Technology", "Intel VT-x", or "AMD-V"
   - Enable it
   - Save and exit

2. **Manufacturer-specific guides:**
   - **Dell:** F2 during startup → Virtualization → Enable
   - **HP:** F10 → Advanced → System Options → Virtualization Technology
   - **Lenovo:** F1 or F2 → Configuration → Intel VT → Enable
   - **ASUS:** F2 or Del → Advanced → CPU Configuration → SVM Mode
   - **MSI:** Del → OC → CPU Features → SVM Mode

3. **Check if enabled in Windows:**
   ```powershell
   Get-ComputerInfo | Select-Object HyperVisorPresent, HyperVRequirementVirtualizationFirmwareEnabled
   ```

---

### Issue: Error 0x8007019e - Windows update required

**Solution:**
1. Go to Settings → Windows Update
2. Install all available updates
3. Restart computer
4. Try WSL install again

---

### Issue: Installation hangs at "Installing..."

**Solutions:**
1. **Wait longer** (can take 10+ minutes on slow internet)

2. **Cancel and retry:**
   ```powershell
   # Press Ctrl+C to cancel
   wsl --unregister Ubuntu-22.04
   wsl --install -d Ubuntu-22.04
   ```

3. **Manual distribution install:**
   - Download from Microsoft Store manually
   - Search "Ubuntu" in Store
   - Install from there

---

## Network Issues

### Issue: Can't access internet from WSL

**Solutions:**

**1. DNS fix (most common):**
```bash
# In WSL
sudo nano /etc/resolv.conf

# Change content to:
nameserver 8.8.8.8
nameserver 8.8.4.4

# Save: Ctrl+X, Y, Enter
```

**2. Make DNS fix permanent:**
```bash
# In WSL
sudo nano /etc/wsl.conf

# Add:
[network]
generateResolvConf = false

# Save, then in Windows PowerShell:
wsl --shutdown
wsl

# Then fix /etc/resolv.conf again (step 1)
```

**3. Windows firewall:**
- Windows Security → Firewall & network protection
- Allow an app through firewall
- Find WSL-related entries, ensure both Private and Public are checked

**4. VPN conflicts:**
- Disable VPN temporarily
- Test if WSL networking works
- If VPN is the issue, look for VPN-specific WSL guides

---

## File Access Issues

### Issue: Can't see Windows files from WSL

**Solution:**
Windows drives are mounted at `/mnt/`:
```bash
# C: drive
cd /mnt/c

# D: drive
cd /mnt/d

# Your user folder
cd /mnt/c/Users/YourWindowsUsername
```

---

### Issue: Can't see WSL files from Windows

**Solution:**
Access WSL filesystem via network path:
```
\\wsl$\Ubuntu-22.04\home\username\

# Or in File Explorer:
# Type in address bar: \\wsl$
```

---

## Performance Issues

### Issue: WSL is slow

**Solutions:**

**1. Ensure WSL 2 (not WSL 1):**
```powershell
wsl --list --verbose

# If VERSION shows "1", convert to 2:
wsl --set-version Ubuntu-22.04 2
```

**2. Don't work on Windows files from WSL:**
- Slow: `/mnt/c/Users/...` (Windows filesystem)
- Fast: `/home/username/` (WSL filesystem)
- Copy files to WSL if doing heavy work

**3. Limit memory usage:**
Create `.wslconfig` in `C:\Users\YourName\`:
```ini
[wsl2]
memory=4GB
processors=2
```

Then restart WSL:
```powershell
wsl --shutdown
wsl
```

---

## Permission Issues

### Issue: "Permission denied" errors

**Solution:**
Use `sudo` for administrative tasks:
```bash
# Instead of:
apt install something

# Use:
sudo apt install something

# Enter your password
```

---

### Issue: Forgot WSL password

**Solution:**
Reset password from Windows:
```powershell
# Open PowerShell as Admin
wsl -u root

# In WSL (as root):
passwd username

# Enter new password twice
exit
```

---

## Distribution Issues

### Issue: Want to install different Linux distribution

**Available distributions:**
```powershell
# List available
wsl --list --online

# Install specific one
wsl --install -d Debian
wsl --install -d kali-linux
wsl --install -d Ubuntu-20.04
```

---

### Issue: Want to uninstall/remove a distribution

**Solution:**
```powershell
# List installed
wsl --list

# Unregister (deletes all data!)
wsl --unregister Ubuntu-22.04

# Reinstall
wsl --install -d Ubuntu-22.04
```

---

## Update Issues

### Issue: Need to update WSL itself

**Solution:**
```powershell
# Update WSL
wsl --update

# Check version
wsl --version
```

---

### Issue: Ubuntu packages fail to update

**Solution:**
```bash
# Fix broken packages
sudo apt --fix-broken install

# Update package lists
sudo apt update

# Upgrade packages
sudo apt upgrade
```

---

## Complete Reset

### Nuclear option: Start fresh

**Uninstall everything:**
```powershell
# Unregister all distributions
wsl --unregister Ubuntu-22.04

# Uninstall WSL features
Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
Disable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform

# Restart computer
Restart-Computer
```

**Then reinstall:**
- Follow installation steps from scratch
- Start clean

---

## Getting Help

**Check WSL version and status:**
```powershell
wsl --version
wsl --status
wsl --list --verbose
```

**Official resources:**
- Microsoft docs: https://docs.microsoft.com/windows/wsl
- GitHub issues: https://github.com/microsoft/wsl/issues
- Community: r/bashonubuntuonwindows

**When asking for help, provide:**
1. Windows version (`winver`)
2. WSL version (`wsl --version`)
3. Error message (exact text)
4. What you were trying to do
5. What step failed
