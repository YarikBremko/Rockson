#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Rockson Performance — Schedule App  |  install.sh
# Run this once on a fresh Linux machine to set everything up.
# ─────────────────────────────────────────────────────────────────────────────
APP_NAME="rockson-schedule"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PORT=5002

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo "════════════════════════════════════════════════"
echo "  Rockson Performance — Schedule App  |  Setup  "
echo "════════════════════════════════════════════════"
echo ""

# ── 1. Install / verify Python 3.10+ ────────────────────────────────────────
info "Checking Python 3..."

# Auto-install Python if missing (apt-based systems only)
if ! command -v python3 &>/dev/null; then
  warn "Python 3 not found. Attempting to install..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv
  else
    error "Python 3 not found and cannot auto-install on this system. Please install Python 3.10 or higher manually."
  fi
fi

PYTHON=$(command -v python3)
PYVER=$($PYTHON --version 2>&1 | awk '{print $2}')
info "Found Python $PYVER"

# Enforce minimum version 3.10
PYVER_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
PYVER_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
if [ "$PYVER_MAJOR" -lt 3 ] || { [ "$PYVER_MAJOR" -eq 3 ] && [ "$PYVER_MINOR" -lt 10 ]; }; then
  error "Python 3.10 or higher is required. Found $PYVER. Please upgrade Python and re-run this script."
fi
info "Python version OK ($PYVER >= 3.10)"

# ── 2. Install pip and venv if missing ───────────────────────────────────────
info "Checking pip and venv..."
if ! $PYTHON -m pip --version > /dev/null 2>&1; then
  warn "pip not found. Attempting to install..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get install -y -qq python3-pip
  else
    error "pip not found and cannot auto-install. Please install python3-pip manually."
  fi
fi

if ! $PYTHON -m venv --help > /dev/null 2>&1; then
  warn "venv module not found. Attempting to install..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get install -y -qq python3-venv
  else
    error "venv not found and cannot auto-install. Please install python3-venv manually."
  fi
fi
info "pip and venv OK"

# ── 3. System packages for WeasyPrint ────────────────────────────────────────
info "Installing system dependencies for PDF export (WeasyPrint)..."
if command -v apt-get &>/dev/null; then
  sudo apt-get update -qq

  # Core packages — required on all Debian/Ubuntu/Raspberry Pi OS versions
  sudo apt-get install -y -qq \
    python3-venv libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libcairo2-dev libffi-dev shared-mime-info

  # libgdk-pixbuf was renamed in Debian 12 (Bookworm) / Raspberry Pi OS 2023+
  # Try the new name first, fall back to the old name
  if apt-cache show libgdk-pixbuf-2.0-0 &>/dev/null 2>&1; then
    sudo apt-get install -y -qq libgdk-pixbuf-2.0-0
  elif apt-cache show libgdk-pixbuf2.0-0 &>/dev/null 2>&1; then
    sudo apt-get install -y -qq libgdk-pixbuf2.0-0
  else
    warn "Could not find libgdk-pixbuf — PDF image rendering may not work, but the rest of the app will."
  fi

elif command -v dnf &>/dev/null; then
  sudo dnf install -y python3-virtualenv pango cairo gdk-pixbuf2 libffi-devel
elif command -v pacman &>/dev/null; then
  sudo pacman -Sy --noconfirm python-virtualenv pango cairo gdk-pixbuf2 libffi
else
  warn "Unknown package manager — skipping system packages. WeasyPrint may not work."
fi

# ── 4. Create virtual environment ────────────────────────────────────────────
info "Creating Python virtual environment..."
$PYTHON -m venv "$VENV_DIR"
info "Virtual environment created at $VENV_DIR"

# ── 5. Install Python packages ────────────────────────────────────────────────
info "Installing Python packages (Flask, WeasyPrint)..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q
info "Python packages installed."

# ── 6. Create folder structure ────────────────────────────────────────────────
info "Creating folder structure..."
mkdir -p "$APP_DIR/instance"
mkdir -p "$APP_DIR/static/images/exercises"
mkdir -p "$APP_DIR/static/images"
info "Folders ready."

# ── 7. Initialise database ────────────────────────────────────────────────────
info "Initialising database..."
"$VENV_DIR/bin/python" - <<'PYEOF'
import sys, os
sys.path.insert(0, os.getcwd())
from app import init_db
init_db()
print("Database initialised.")
PYEOF

# ── 8. Write start script ─────────────────────────────────────────────────────
info "Writing start.sh..."
cat > "$APP_DIR/start.sh" <<STARTEOF
#!/usr/bin/env bash
cd "\$(dirname "\${BASH_SOURCE[0]}")"
echo "Starting Rockson Schedule App on http://localhost:${PORT}"
echo "Press Ctrl+C to stop."
./venv/bin/python app.py
STARTEOF
chmod +x "$APP_DIR/start.sh"

# ── 9. Optional systemd service ───────────────────────────────────────────────
echo ""
read -p "$(echo -e "${YELLOW}Set up auto-start on boot (systemd service)? [y/N]: ${NC}")" setup_service
if [[ "$setup_service" =~ ^[Yy]$ ]]; then
  SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
  CURRENT_USER=$(whoami)
  sudo tee "$SERVICE_FILE" > /dev/null <<SVCEOF
[Unit]
Description=Rockson Performance Schedule App
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${VENV_DIR}/bin/python ${APP_DIR}/app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

  sudo systemctl daemon-reload
  sudo systemctl enable "$APP_NAME"
  sudo systemctl start  "$APP_NAME"
  info "Service installed and started. Manage it with:"
  echo "  sudo systemctl start   $APP_NAME"
  echo "  sudo systemctl stop    $APP_NAME"
  echo "  sudo systemctl restart $APP_NAME"
  echo "  sudo systemctl status  $APP_NAME"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════"
echo -e "  ${GREEN}Installation complete!${NC}"
echo "════════════════════════════════════════════════"
echo ""
echo "  To start the app:  ./start.sh"
echo "  Then open:         http://localhost:${PORT}"
echo ""
