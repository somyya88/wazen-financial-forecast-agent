# Wazen CFO Intelligence Agent V11.7.1

## Critical hotfix
- Removes accidental unconditional `st.rerun()` that caused the app to remain in a loading / greyed-out state.
- Keeps setup hidden after model build without forcing an infinite rerun loop.
- Adds a manual button to show setup again when needed.

## Symptom fixed
The app was staying for several minutes in a faded/disabled Streamlit state around Expense Mapping / model build.
