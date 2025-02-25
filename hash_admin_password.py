from password_utils import hash_password
import json

# Load current settings
with open('settings.json', 'r') as f:
    settings = json.load(f)

# Hash only the admin password
admin_password = settings['ui']['adminPassword']
hashed_admin_password = hash_password(admin_password)

# Update only the admin password
settings['ui']['adminPassword'] = hashed_admin_password

# Save updated settings
with open('settings.json', 'w') as f:
    json.dump(settings, f, indent=2)

print(f"Admin password hashed successfully")