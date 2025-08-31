# Swiss Ephemeris Files

⚠️ **Large files not included in Git repository**

Swiss ephemeris files (*.se1, *.eph) are excluded from version control due to their large size.

## 📥 Setup Instructions

1. **Download Swiss ephemeris files** from https://www.astro.com/swisseph/
2. **Place files in this directory** (`data/ephemeris/`)
3. **Restart the stack** to pick up the files:
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
