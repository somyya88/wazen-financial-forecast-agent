# Wazen CFO Intelligence Agent V11.7

## Performance & UX fixes
- Setup phase is hidden after model build.
- Upload / period confirmation / expense mapping do not re-render after the model is ready unless setup is enabled.
- Removed duplicate pre-tabs dashboard and executive summary.
- Added rerun after model build to move directly to the analysis view.
- Dashboard appears only inside the Dashboard tab.

## Why it was slow
Streamlit reruns the entire script on each interaction. Before V11.7, the app rebuilt preview revenue, preview expense, expense mapping, validation, and dashboard together on each interaction.
