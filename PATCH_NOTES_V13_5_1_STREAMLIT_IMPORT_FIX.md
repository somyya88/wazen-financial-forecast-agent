# Patch Notes V13.5.1 — Streamlit Import Fix

## Fixed

- Added missing Wazen theme constants to `config.py`:
  - `WAZEN_BLUE`
  - `WAZEN_ORANGE`
  - `WAZEN_LIGHT_BG`
  - `WAZEN_TEXT`
  - supporting UI colors
- Updated app title/sidebar labels from V13.4 to V13.5.

## Why

Streamlit Cloud failed at startup because `theme.py` imported brand constants that were not exported by `config.py`.
