import pandas as pd
import streamlit as st
""
st.set_page_config(
    page_title="Winston's World Cup Fun",
    page_icon="⚽",
    layout="wide"
)

POINTS = {
    "GS": 0,
    "R32": 1,
    "R16": 2,
    "QF": 4,
    "SF": 6,
    "RU": 9,
    "W": 12
}

STAGE_LABELS = {
    "GS": "Group Stage",
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF": "Quarterfinal",
    "SF": "Semifinal",
    "RU": "Runner-up",
    "W": "Winner"
}

STAGE_ORDER = ["Group Stage", "Round of 16", "Quarterfinal", "Semifinal", "Runner-up", "Winner"]

@st.cache_data
def load_data():
    picks = pd.read_csv("picks.csv")
    results = pd.read_csv("results.csv")
    return picks, results

def medal_for_rank(rank):
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    return ""

try:
    picks, results = load_data()
except FileNotFoundError as e:
    st.error(f"Could not find file: {e}")
    st.stop()

required_picks_cols = {"player", "team"}
required_results_cols = {"team", "stage_reached"}

if not required_picks_cols.issubset(picks.columns):
    st.error("`picks.csv` must contain columns: `player`, `team`")
    st.stop()

if not required_results_cols.issubset(results.columns):
    st.error("`results.csv` must contain columns: `team`, `stage_reached`")
    st.stop()

picks["player"] = picks["player"].astype(str).str.strip()
picks["team"] = picks["team"].astype(str).str.strip()
results["team"] = results["team"].astype(str).str.strip()
results["stage_reached"] = results["stage_reached"].astype(str).str.strip()

invalid_stages = results.loc[~results["stage_reached"].isin(POINTS.keys())]
if not invalid_stages.empty:
    st.error("`results.csv` contains invalid `stage_reached` values.")
    st.write("Allowed values are:")
    st.code(", ".join(POINTS.keys()))
    st.dataframe(invalid_stages, use_container_width=True)
    st.stop()

df = picks.merge(results, on="team", how="left")
missing_results = df[df["stage_reached"].isna()]["team"].unique().tolist()

df["stage_reached"] = df["stage_reached"].fillna("GS")
df["points"] = df["stage_reached"].map(POINTS)
df["stage_label"] = df["stage_reached"].map(STAGE_LABELS)

leaderboard = (
    df.groupby("player", as_index=False)["points"].sum().sort_values(by=["points", "player"], ascending=[False, True]).reset_index(drop=True)
)

leaderboard["Rank"] = leaderboard["points"].rank(method="min", ascending=False).astype(int)
leaderboard = leaderboard.sort_values(by=["Rank", "player"]).reset_index(drop=True)
leaderboard["Medal"] = leaderboard["Rank"].apply(medal_for_rank)
leaderboard = leaderboard.rename(columns={"player": "Player", "points": "Points"})
leaderboard = leaderboard[["Rank", "Medal", "Player", "Points"]]

details = df[["player", "team", "stage_label", "points"]].rename(
    columns={
        "player": "Player",
        "team": "Team",
        "stage_label": "Stage Reached",
        "points": "Points"
    }
).sort_values(
    by=["Player", "Points", "Team"],
    ascending=[True, False, True]
)

player_summary = (
    df.groupby("player").agg(
        total_points=("points", "sum"),
        teams_picked=("team", lambda x: ", ".join(sorted(x)))
    ).reset_index().sort_values(by=["total_points", "player"], ascending=[False, True]).rename(columns={"player": "Player", "total_points": "Points", "teams_picked": "Teams Picked"})
)

pick_matrix = picks.assign(Picked="✅").pivot_table(
    index="team",
    columns="player",
    values="Picked",
    aggfunc="first",
    fill_value=""
).reset_index()

stage_counts = df["stage_label"].value_counts().reindex(STAGE_ORDER, fill_value=0)

st.title("⚽ Winston's World Cup Fun")
st.markdown("### Family leaderboard, team tracking, and bragging rights")

if missing_results:
    st.warning(
        "These teams appear in `picks.csv` but are missing from `results.csv`: "
        + ", ".join(missing_results)
        + ". They are currently being scored as `GS` (0 points)."
    )

col1, col2, col3 = st.columns(3)
col1.metric("Players", picks["player"].nunique())
col2.metric("Total Picks", len(picks))
col3.metric("Teams Picked", picks["team"].nunique())

tab1, tab2, tab3, tab4 = st.tabs(["🏆 Leaderboard", "📋 Player Breakdown", "📊 Charts", "🛠 Data"])

with tab1:
    st.subheader("Leaderboard")
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)

    st.subheader("Score Chart")
    chart_df = leaderboard.set_index("Player")["Points"]
    st.bar_chart(chart_df)

with tab2:
    selected_player = st.selectbox(
        "Filter by player",
        options=["All"] + sorted(details["Player"].unique().tolist())
    )

    if selected_player == "All":
        filtered_details = details
    else:
        filtered_details = details[details["Player"] == selected_player]

        player_points = int(filtered_details["Points"].sum())
        player_teams = len(filtered_details)
        best_pick = filtered_details.sort_values(by=["Points", "Team"], ascending=[False, True]).iloc[0]["Team"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Points", player_points)
        c2.metric("Teams Picked", player_teams)
        c3.metric("Best Pick", best_pick)

    st.subheader("Detailed Breakdown")
    st.dataframe(filtered_details, use_container_width=True, hide_index=True)

    st.subheader("Player Summary")
    st.dataframe(player_summary, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Picked Teams by Tournament Stage")
    stage_chart_df = pd.DataFrame({
        "Stage": stage_counts.index,
        "Teams": stage_counts.values
    }).set_index("Stage")
    st.bar_chart(stage_chart_df)

with tab4:
    st.subheader("Pick Matrix")
    st.dataframe(pick_matrix, use_container_width=True, hide_index=True)

    st.subheader("Scoring Rules")
    scoring_df = pd.DataFrame({
        "Stage Code": list(POINTS.keys()),
        "Stage": [STAGE_LABELS[s] for s in POINTS.keys()],
        "Points": list(POINTS.values())
    })
    st.dataframe(scoring_df, use_container_width=True, hide_index=True)

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