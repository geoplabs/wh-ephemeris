
# Swiss Ephemeris Files

⚠️ **Large files not included in Git repository**

Swiss ephemeris files (*.se1, *.eph) are excluded from version control due to their large size.

## 📥 Setup Instructions

1. **Run the helper script** (recommended): make sure `curl` and `unzip` are available on your system, then execute
   ```bash
   ./scripts/download_ephemeris.sh
   ```
   The script fetches the recommended data set (`seas_18.se1`, `semo_18.se1`, `sepl_18.se1`, and `de406.eph`) directly from Astro.com and stores it in this folder. Pass a custom destination as the first argument to download elsewhere (e.g., inside a CI workspace).
2. **Or download manually** from https://www.astro.com/swisseph/ if you prefer.
3. **Place files in this directory** (`data/ephemeris/`)
4. **Restart the stack** to pick up the files:
   ```bash
   docker compose down -v
   docker compose up --build -d
   ```

## 📋 Recommended Files

- `seas_18.se1` - Main planetary ephemeris
- `semo_18.se1` - Moon ephemeris  
- `sepl_18.se1` - Planet positions
- `de406.eph` - High-precision JPL ephemeris (optional, large file)

## 🔧 Verification

After adding files, test with:
```bash
docker compose exec -T api python -c "import swisseph as swe; swe.set_ephe_path('/app/data/ephemeris'); print('Swiss Ephemeris path set:', swe.get_ephe_path())"
```

Files will be automatically mounted in containers at `/app/data/ephemeris/`.
