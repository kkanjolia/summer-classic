import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone
from math import isclose

# ======= Persistence Setup: Load bets from file =======
BETS_FILE = "bets_data.csv"

def load_bets():
    if os.path.exists(BETS_FILE):
        return pd.read_csv(BETS_FILE)
    else:
        # Create an empty DataFrame with appropriate columns.
        return pd.DataFrame(columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])

st.session_state.bets = load_bets()

# --- Helper Functions for Each-Way Processing ---
# (These functions compute effective pool totals based on each-way splitting.
#  They still factor in the splitting of the wager for pool building.)
def effective_contribution(bet_type, amount, category):
    if bet_type == "Win":
        return amount / 3.0
    elif bet_type == "Place":
        return amount / 2.0 if category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if category == "Show" else 0
    else:
        return 0

def total_effective_pool(category):
    total = 0
    for _, row in st.session_state.bets.iterrows():
        total += effective_contribution(row["Bet Type"], row["Bet Amount"], category)
    return total

# ========= Admin Login Section in the Sidebar =========
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")

def admin_login():
    with st.sidebar:
        st.header("Admin Login")
        admin_pw = st.text_input("Enter admin password", type="password", key="admin_pw")
        if st.button("Login as Admin", key="login_admin"):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Logged in as admin.")
            else:
                st.error("Incorrect password.")

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

admin_login()
if st.session_state.admin_logged_in:
    if st.button("Logout", key="logout_button"):
        st.session_state.admin_logged_in = False
        st.success("Logged out.")

st.title("2025 Summer Classic")

# ========= Betting Lock Toggle (Admin Only) =========
if "wagering_closed" not in st.session_state:
    st.session_state.wagering_closed = False

if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock", key="toggle_lock"):
        st.session_state.wagering_closed = not st.session_state.wagering_closed
        if st.session_state.wagering_closed:
            st.success("Wagering locked. Final payout ratios computed.")
        else:
            st.info("Wagering unlocked.")

if not st.session_state.wagering_closed:
    st.info("Wagering is OPEN. New bets are accepted.")
else:
    st.warning("Wagering is LOCKED. No new bets accepted.")

# ========= Admin Wager Management: Delete Bets =========
if st.session_state.admin_logged_in:
    st.subheader("Admin: Manage Wagers (Delete Erroneous Bets)")
    if not st.session_state.bets.empty:
        indices = st.multiselect("Select wager row indices to delete", options=list(st.session_state.bets.index))
        if st.button("Delete Selected Wagers", key="delete_wagers"):
            if indices:
                st.session_state.bets = st.session_state.bets.drop(indices).reset_index(drop=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
                st.success("Selected wagers deleted.")
            else:
                st.error("No wagers selected.")
    else:
        st.info("No wagers to delete.")

# ========= Public Bet Form =========
if not st.session_state.wagering_closed:
    def bet_form():
        with st.form("bet_form", clear_on_submit=True):
            Bettor_Name = st.selectbox("Bettor Name", 
                ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
                 "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
                 "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"], key="bettor_name")
            Who_You_Bet_On = st.selectbox("Betting On", 
                ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
                 "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
                 "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"], key="betting_on")
            bet_type = st.selectbox("Bet Type", ["Win", "Place", "Show"], key="bet_type")
            bet_amount = st.number_input("**Bet Amount:** $", min_value=0, step=1, key="bet_amount")
            submitted = st.form_submit_button("Submit Bet")
            if submitted:
                new_bet = pd.DataFrame([[Bettor_Name, Who_You_Bet_On, bet_type, bet_amount]],
                                       columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])
                st.session_state.bets = pd.concat([st.session_state.bets, new_bet], ignore_index=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
    bet_form()
else:
    st.error("Betting is closed; no new bets accepted.")

# (The "Current Bets" section has been removed as requested.)

# ========= Raw Total Pools =========
def calculate_pools():
    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Win", "Bet Amount"].sum()
    total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Place", "Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Show", "Bet Amount"].sum()
    return total_pool, total_win, total_place, total_show

total_pool, total_win, total_place, total_show = calculate_pools()

st.header("Total Pool Size")
st.markdown("Total wagered amounts:")
st.write("**Total Pool:** $", total_pool)
st.write("**Win Pool:** $", total_win)
st.write("**Place Pool:** $", total_place)
st.write("**Show Pool:** $", total_show)

# ========= Effective Pool Totals (Each-Way Splitting) =========
total_win_eff = total_effective_pool("Win")
total_place_eff = total_effective_pool("Place")
total_show_eff = total_effective_pool("Show")

st.write("**Effective Win Pool:** $", total_win_eff)
st.write("**Effective Place Pool:** $", total_place_eff)
st.write("**Effective Show Pool:** $", total_show_eff)

# ========= Hypothetical Payout Ratios (Raw) =========
st.header("Bet Summary and Raw Payout Ratios")
st.markdown("""
This table summarizes bets by outcome (the horse) and shows raw payout ratios,
calculated as: (Total Pool for the category) / (Total bets on that outcome).
""")
def create_summary():
    summary = st.session_state.bets.pivot_table(
        index="Betting On", 
        columns="Bet Type", 
        values="Bet Amount", 
        aggfunc="sum", 
        fill_value=0
    ).reset_index()
    for bt in ["Win", "Place", "Show"]:
        if bt in summary.columns:
            summary = summary.rename(columns={bt: f"Total Bet {bt}"})
        else:
            summary[f"Total Bet {bt}"] = 0
    summary["Payout Ratio Win"] = summary["Total Bet Win"].apply(lambda x: total_win / x if x > 0 else 0)
    summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(lambda x: total_place / x if x > 0 else 0)
    summary["Payout Ratio Show"] = summary["Total Bet Show"].apply(lambda x: total_show / x if x > 0 else 0)
    return summary
summary = create_summary()
st.dataframe(summary)

# ========= Finishing Order Section (Admin Only) =========
options = ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", 
           "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", 
           "Kunal Kanjolia", "Mike Leonard"]

if st.session_state.admin_logged_in:
    st.header("Enter Finishing Order (Admin Only)")
    winner = st.selectbox("Winner (1st)", options, key="winner_select")
    second = st.selectbox("2nd Place", options, key="second_select")
    third = st.selectbox("3rd Place", options, key="third_select")
    st.session_state.finishing_order = {"winner": winner, "second": second, "third": third}
else:
    st.info("Finishing order can only be adjusted by the admin.")
    if "finishing_order" in st.session_state:
        order = st.session_state.finishing_order
        winner = order["winner"]
        second = order["second"]
        third = order["third"]
    else:
        winner = second = third = None

# ========= Compute Eligible Raw Sums (Full Bet Amounts) for Payout Calculation =========
# For each pool, we use the raw bet amounts (not fractions) for eligible bets.
eligible_win_raw = st.session_state.bets.loc[(st.session_state.bets["Bet Type"]=="Win") & 
                                               (st.session_state.bets["Betting On"]==winner), "Bet Amount"].sum()
eligible_place_raw = st.session_state.bets.loc[(st.session_state.bets["Bet Type"]=="Place") & 
                                                 (st.session_state.bets["Betting On"].isin([winner, second])), "Bet Amount"].sum()
eligible_show_raw = st.session_state.bets.loc[(st.session_state.bets["Bet Type"]=="Show") & 
                                                (st.session_state.bets["Betting On"].isin([winner, second, third])), "Bet Amount"].sum()

# Effective pools remain based on the split:
# (Redistribution logic remains unchanged.)
total_win_eff = total_effective_pool("Win")
total_place_eff = total_effective_pool("Place")
total_show_eff = total_effective_pool("Show")

eligible_info = {
    "Win": {"E": eligible_win_raw, "T": total_win_eff},
    "Place": {"E": eligible_place_raw, "T": total_place_eff},
    "Show": {"E": eligible_show_raw, "T": total_show_eff}
}
extra_total = sum(info["T"] for pool, info in eligible_info.items() if info["E"] == 0)
sum_T_for_eligible = sum(info["T"] for pool, info in eligible_info.items() if info["E"] > 0)
payout_ratios = {}
for pool, info in eligible_info.items():
    if info["E"] > 0:
        extra_for_pool = extra_total * (info["T"] / sum_T_for_eligible) if sum_T_for_eligible > 0 else 0
        effective_total = info["T"] + extra_for_pool
        payout_ratios[pool] = effective_total / info["E"]
    else:
        payout_ratios[pool] = 0

# ========= Lock/Unlock Final Payout Ratios (Admin Toggle) =========
if "wagering_closed" not in st.session_state:
    st.session_state.wagering_closed = False
if st.session_state.admin_logged_in and st.button("Toggle Wagering Lock", key="toggle_lock_button"):
    st.session_state.wagering_closed = not st.session_state.wagering_closed
    if st.session_state.wagering_closed:
        st.session_state.final_payout_ratios = payout_ratios
        st.success("Wagering locked. Final payout ratios computed.")
    else:
        st.info("Wagering unlocked.")

if st.session_state.get("wagering_closed", False):
    final_win_ratio = st.session_state.final_payout_ratios.get("Win", 0)
    final_place_ratio = st.session_state.final_payout_ratios.get("Place", 0)
    final_show_ratio = st.session_state.final_payout_ratios.get("Show", 0)
else:
    final_win_ratio = payout_ratios["Win"]
    final_place_ratio = payout_ratios["Place"]
    final_show_ratio = payout_ratios["Show"]

st.write("**Final Win Payout Ratio:**", final_win_ratio)
st.write("**Final Place Payout Ratio:**", final_place_ratio)
st.write("**Final Show Payout Ratio:**", final_show_ratio)

# ========= Raw Bet Summary =========
st.header("Bet Summary")
summary_df = st.session_state.bets.groupby(["Betting On", "Bet Type"])["Bet Amount"].sum().reset_index()
st.dataframe(summary_df)

# ========= Each-Way Payout Calculation =========
# For payout calculations, use the following logic:
# - If the chosen outcome (the horse) is the winner:
#   • If bet type is "Win": raw payout = stake * (win_ratio + place_ratio + show_ratio)
#   • If bet type is "Place": raw payout = stake * (place_ratio + show_ratio)
#   • If bet type is "Show": raw payout = stake * (show_ratio)
# - Else, if bet type is "Place" and the chosen outcome is second:
#      raw payout = stake * (place_ratio + show_ratio)
# - Else, if bet type is "Show" and the chosen outcome is third:
#      raw payout = stake * (show_ratio)
# (This model ensures that a win bet on the winning horse gets all three pools,
#  a place bet gets only place+show, and a show bet gets only show.)
def calculate_payout(row):
    payout = 0
    if winner is not None:
        if row["Betting On"] == winner:
            if row["Bet Type"] == "Win":
                payout = row["Bet Amount"] * (final_win_ratio + final_place_ratio + final_show_ratio)
            elif row["Bet Type"] == "Place":
                payout = row["Bet Amount"] * (final_place_ratio + final_show_ratio)
            elif row["Bet Type"] == "Show":
                payout = row["Bet Amount"] * (final_show_ratio)
        elif row["Bet Type"] == "Place" and row["Betting On"] == second:
            payout = row["Bet Amount"] * (final_place_ratio + final_show_ratio)
        elif row["Bet Type"] == "Show" and row["Betting On"] == third:
            payout = row["Bet Amount"] * (final_show_ratio)
    return payout

bets_df = st.session_state.bets.copy()
bets_df["Raw Payout"] = bets_df.apply(calculate_payout, axis=1)

# Scale raw payouts so that the sum equals the total bet pool.
total_raw = bets_df["Raw Payout"].sum()
scale_factor = (total_pool / total_raw) if total_raw > 0 else 0
bets_df["Payout"] = bets_df["Raw Payout"] * scale_factor
bets_df.loc[bets_df["Payout"].isna(), "Payout"] = 0

# Remove rows where payout is 0
bets_df = bets_df[bets_df["Payout"] > 0]

st.header("Individual Payouts")
st.markdown("Final Payouts once tournament is over (scaled so total payout equals total bet pool)")
st.dataframe(bets_df[["Bettor Name", "Betting On", "Bet Type", "Bet Amount", "Payout"]])

st.write("**Total Wagered:** $", total_pool)
st.write("**Total Payout (Scaled):** $", round(bets_df["Payout"].sum(), 2))