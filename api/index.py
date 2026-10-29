import sys
from pathlib import Path

# Add project root and services/api to sys.path
root_dir = Path(__file__).resolve().parent.parent
services_api_dir = root_dir / "services" / "api"

for p in [str(root_dir), str(services_api_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.api.app import app  # noqa: E402
