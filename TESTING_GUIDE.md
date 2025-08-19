# Testing Guide - iOS to Android Migration Assistant

## 🔧 Initial Setup (One Time)

### 1. Create Virtual Environment
```bash
# From project root
cd /Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent

# Create virtual environment
python3.11 -m venv .venv

# Activate it
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Install photo-migration as editable package
pip install -e mcp-tools/photo-migration/

# Install Playwright browser (for photo-migration)
playwright install chromium
```

### 2. Configure Environment
```bash
# Copy your existing .env if not already done
# Should contain at minimum:
# APPLE_ID=your.email@icloud.com
# APPLE_PASSWORD=your_password
```

## 📝 Testing Order

### Phase 1: Verify Infrastructure
```bash
# Always activate virtual environment first
source .venv/bin/activate

# 1. Test shared infrastructure
python scripts/test_shared_infrastructure.py

# 2. Test photo-migration can read root .env
python scripts/test_photo_migration_env.py

# 3. Initialize database (first time only)
python scripts/setup_database.py

# 4. Check migration status
python scripts/migration_status.py
```

### Phase 2: Test Photo Migration Tool
```bash
# From project root (with venv activated)
cd mcp-tools/photo-migration

# Test the existing functionality
python test_client.py

# With options:
python test_client.py --fresh  # Force new login
python test_client.py --clear  # Clear saved session
```

## 🎯 Quick Daily Testing

For daily development, create this alias in your shell:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias migrate-test='cd /path/to/project && source .venv/bin/activate'
```

Then just run:
```bash
migrate-test
python scripts/migration_status.py
```

## 📊 Expected Results

### Infrastructure Test
- ✅ All modules import correctly
- ✅ Settings load from root .env
- ✅ Database connects successfully
- ✅ Logging configured properly

### Photo Migration Test
- ✅ Loads Apple credentials from root .env
- ✅ Can connect to iCloud
- ✅ Session persistence works
- ✅ Returns real photo counts

## 🚀 Next Steps After Testing

Once all tests pass:
1. Begin Phase 2: Google APIs Integration
2. Update `mcp-tools/photo-migration/pyproject.toml` with new dependencies
3. Create `google_photos.py` and `gmail_monitor.py`
4. Implement new MCP tools (start_transfer, check_progress, etc.)

## 🔍 Troubleshooting

### Virtual Environment Issues
```bash
# If 'source .venv/bin/activate' fails:
which python3.11  # Verify Python 3.11 is installed

# Recreate if needed:
rm -rf .venv
python3.11 -m venv .venv
```

### Import Errors
```bash
# Verify you're in virtual environment
which python  # Should show .venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Errors
```bash
# Check database exists
ls -la ~/.ios_android_migration/

# Reset database if needed
rm -rf ~/.ios_android_migration/migration.db
python scripts/setup_database.py
```

## 📁 Project Structure Reference

```
project-root/
├── .venv/                    # Virtual environment (git ignored)
├── .env                      # Your credentials (git ignored)
├── requirements.txt          # All Python dependencies
├── shared/                   # Shared infrastructure
├── mcp-tools/               # MCP tool implementations
├── scripts/                 # Utility scripts
└── activate.sh             # Quick activation helper
```

## 🔐 Security Notes

- Never commit `.env` file
- Never commit `.venv/` directory
- Add both to `.gitignore`
- Keep credentials in root `.env` only