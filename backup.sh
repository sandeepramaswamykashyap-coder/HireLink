#!/bin/bash

# Generates a clean backup of the project
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="HireLink_Backup_$TIMESTAMP.zip"
DEST_DIR="$HOME/Desktop"

echo "📦 Creating backup: $BACKUP_NAME"

# Zip excluding heavy/temp/git files
zip -r "$BACKUP_NAME" . -x "*.git*" "*__pycache__*" "data/chrome_profile/*" "logs/*" "*.DS_Store*" "venv/*" "node_modules/*"

# Move to Desktop
mv "$BACKUP_NAME" "$DEST_DIR/"

echo "✅ Backup moved to Desktop: $DEST_DIR/$BACKUP_NAME"
echo "👉 You can drag this file to Google Drive now."
