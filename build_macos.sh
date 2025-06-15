#!/bin/bash

# Clean previous builds
rm -rf build dist

# Ensure Python environment is activated
source venv/bin/activate 2>/dev/null || true

# Set Python path to include source directory
export PYTHONPATH=src:${PYTHONPATH}

# Enable verbose output for debugging
export PYTHONVERBOSE=1

# Build the app using PyInstaller
python3 -m PyInstaller ModbusBaby.spec

# Create frameworks directory and copy required frameworks
mkdir -p dist/ModbusBaby.app/Contents/Frameworks
ln -sf /System/Library/Frameworks/CoreFoundation.framework dist/ModbusBaby.app/Contents/Frameworks/
ln -sf /System/Library/Frameworks/IOKit.framework dist/ModbusBaby.app/Contents/Frameworks/

# Remove quarantine attribute if present
xattr -rd com.apple.quarantine dist/ModbusBaby.app 2>/dev/null || true

# First, let's check if we have a Developer ID certificate
CERT_NAME=$(security find-identity -v -p codesigning | grep "Developer ID Application" | awk -F '"' '{print $2}')

if [ -n "$CERT_NAME" ]; then
    echo "Found Developer ID: $CERT_NAME"
    # Sign the app with the entitlements
    codesign --force --deep --options runtime \
        --entitlements entitlements.plist \
        --sign "$CERT_NAME" \
        --timestamp \
        dist/ModbusBaby.app

    # Verify the signing
    codesign --verify --deep --strict --verbose=2 dist/ModbusBaby.app
else
    echo "No Developer ID Application certificate found. The app will be built unsigned."
    echo "To sign the app later, you'll need to obtain a Developer ID from Apple."
fi

echo "Build complete. The app is in the dist folder."
