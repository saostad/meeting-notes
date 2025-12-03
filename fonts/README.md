# Fonts Directory

This directory contains fonts used for video overlay text rendering.

## Included Fonts

- **Open Sans** - Google's Open Sans font family
- License: Apache License 2.0
- Website: https://fonts.google.com/specimen/Open+Sans
- File: OpenSans.ttf (Variable font with multiple weights and widths)

## Usage

The chapter overlay feature automatically uses fonts from this directory to ensure consistent rendering across all platforms.

## Font Fallback Order

1. **Project fonts** (this directory) - Bundled fonts for consistency
2. **System fonts** (platform-specific) - Windows, macOS, Linux system fonts
3. **ffmpeg default** - Built-in fallback font

This ensures the overlay feature works reliably on Windows, macOS, and Linux without requiring additional font installation.

## License Compliance

Open Sans is licensed under the Apache License 2.0, which allows:
- Commercial and personal use
- Distribution and modification
- Patent use

The font is included to ensure consistent cross-platform rendering of chapter title overlays.