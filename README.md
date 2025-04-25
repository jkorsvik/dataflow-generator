## Optional: Speed up file search with `fd`

For large projects, file discovery is much faster if the [`fd`](https://github.com/sharkdp/fd) command-line tool is installed.  
If `fd` is not available, the tool will fall back to a pure Python implementation (which is slower for large directory trees).

**Install `fd` for your platform:**

- **macOS:**  
  `brew install fd`
- **Debian/Ubuntu:**  
  `sudo apt install fd-find`  
  (You may need to use `fdfind` instead of `fd`.)
- **Windows (with Chocolatey):**  
  `choco install fd`

If you do not install `fd`, everything will still work, but file search may be slower.
