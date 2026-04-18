import pandas as pd
import streamlit as st

# ---------------------------------
# Page config
# ---------------------------------
st.set_page_config(
    page_title="Winstons World Cup Fun",
    page_icon="⚽",
    layout="wide"
)

# ---------------------------------
# Scoring rules
# ---------------------------------
POINTS = {
    "GS": 0,    # Group Stage exit
    "R16": 1,   # Round of 16
    "QF": 2,    # Quarterfinal
    "SF": 4,    # Semifinal
    "RU": 6,    # Runner-up
    "W": 8      # Winner
}

STAGE_LABELS = {
    "GS": "Group Stage",
    "R16": "Round of 16",
    "QF": "Quarterfinal",
    "SF": "Semifinal",
    "RU": "Runner-up",
    "W": "Winner"
}

# ---------------------------------
# Load data
# ---------------------------------
@st.cache_data
def load_data():
    picks = pd.read_csv("picks.csv")
    results = pd.read_csv("results.csv")
    return picks, results

try:
    picks, results = load_data()
except FileNotFoundError as e:
    st.error(f"Could not find file: {e}")
    st.stop()

# ---------------------------------
# Validate columns
# ---------------------------------
required_picks_cols = {"player", "team"}
required_results_cols = {"team", "stage_reached"}

if not required_picks_cols.issubset(picks.columns):
    st.error("`picks.csv` must contain columns: `player`, `team`")
    st.stop()

if not required_results_cols.issubset(results.columns):
    st.error("`results.csv` must contain columns: `team`, `stage_reached`")
    st.stop()

# ---------------------------------
# Clean whitespace
# ---------------------------------
picks["player"] = picks["player"].astype(str).str.strip()
picks["team"] = picks["team"].astype(str).str.strip()
results["team"] = results["team"].astype(str).str.strip()
results["stage_reached"] = results["stage_reached"].astype(str).str.strip()

# ---------------------------------
# Validate stages
# ---------------------------------
invalid_stages = results.loc[~results["stage_reached"].isin(POINTS.keys())]

if not invalid_stages.empty:
    st.error("`results.csv` contains invalid `stage_reached` values.")
    st.write("Allowed values are:")
    st.code(", ".join(POINTS.keys()))
    st.dataframe(invalid_stages, use_container_width=True)
    st.stop()

# ---------------------------------
# Merge picks with results
# ---------------------------------
df = picks.merge(results, on="team", how="left")

missing_results = df[df["stage_reached"].isna()]["team"].unique().tolist()

# If team is missing from results, default to GS
df["stage_reached"] = df["stage_reached"].fillna("GS")
df["points"] = df["stage_reached"].map(POINTS)
df["stage_label"] = df["stage_reached"].map(STAGE_LABELS)

# ---------------------------------
# Leaderboard
# ---------------------------------
leaderboard = (
    df.groupby("player", as_index=False)["points"].sum().sort_values(by=["points", "player"], ascending=[False, True]).reset_index(drop=True)
)

leaderboard.index += 1
leaderboard = leaderboard.reset_index().rename(columns={"index": "Rank"})

# ---------------------------------
# Detailed breakdown
# ---------------------------------
details = df[["player", "team", "stage_label", "points"]].rename(
    columns={"stage_label": "Stage Reached"}
).sort_values(
    by=["player", "points", "team"],
    ascending=[True, False, True]
)

# ---------------------------------
# Summary stats
# ---------------------------------
total_players = picks["player"].nunique()
total_picks = len(picks)
total_teams = picks["team"].nunique()

# ---------------------------------
# UI
# ---------------------------------
st.title("⚽ World Cup Family Pool")
st.caption("Manually update `results.csv` as the tournament progresses, then refresh this app.")

if missing_results:
    st.warning(
        "These teams appear in `picks.csv` but are missing from `results.csv`: "
        + ", ".join(missing_results)
        + ". They are currently being scored as `GS` (0 points)."
    )

col1, col2, col3 = st.columns(3)
col1.metric("Players", total_players)
col2.metric("Total Picks", total_picks)
col3.metric("Teams Picked", total_teams)

st.subheader("Leaderboard")
st.dataframe(leaderboard, use_container_width=True, hide_index=True)

st.subheader("Detailed Breakdown")
selected_player = st.selectbox(
    "Filter by player",
    options=["All"] + sorted(details["player"].unique().tolist())
)

if selected_player != "All":
    filtered_details = details[details["player"] == selected_player]
else:
    filtered_details = details

st.dataframe(filtered_details, use_container_width=True, hide_index=True)

st.subheader("Scoring Rules")
scoring_df = pd.DataFrame({
    "Stage Code": list(POINTS.keys()),
    "Stage": [STAGE_LABELS[s] for s in POINTS.keys()],
    "Points": list(POINTS.values())
})
st.dataframe(scoring_df, use_container_width=True, hide_index=True)

# ---------------------------------
# Download buttons
# ---------------------------------
leaderboard_csv = leaderboard.to_csv(index=False).encode("utf-8")
details_csv = details.to_csv(index=False).encode("utf-8")

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    st.download_button(
        label="Download Leaderboard CSV",
        data=leaderboard_csv,
        file_name="leaderboard.csv",
        mime="text/csv"
    )

with col_dl2:
    st.download_button(
        label="Download Breakdown CSV",
        data=details_csv,
        file_name="breakdown.csv",
        mime="text/csv"
    )