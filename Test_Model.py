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
        return pd.DataFrame(columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])

st.session_state.bets = load_bets()

# ----- User Identification -----
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
    selected_name = st.selectbox(
        "Select Your Name",
        ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
         "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
         "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"],
        key="current_user_select"
    )
    if st.button("Confirm Name"):
        st.session_state.current_user = selected_name
        st.success(f"Name confirmed: {selected_name}")
else:
    st.write("Current user:", st.session_state.current_user)
    if st.button("Back / Change Name"):
        st.session_state.current_user = None
        st.experimental_rerun()

# --- Helper Functions for Each-Way Processing ---
def effective_contribution(bet_type, amount, category):
    """
    Returns the effective contribution for a bet to a pool category:
      - For Win bets: split equally among Win, Place, and Show (amount/3 each)
      - For Place bets: split equally between Place and Show (amount/2 each)
      - For Show bets: full amount goes to Show pool.
    """
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
    st.subheader("Admin: Manage Bets (Delete Erroneous Bets)")
    if not st.session_state.bets.empty:
        to_delete = st.multiselect("Select wager row indices to delete", options=list(st.session_state.bets.index))
        if st.button("Delete Selected Bets", key="delete_wagers"):
            if to_delete:
                st.session_state.bets = st.session_state.bets.drop(to_delete).reset_index(drop=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
                st.success("Selected wagers deleted.")
            else:
                st.error("No wagers selected.")
    else:
        st.info("No wagers to delete.")

# ========= Public Bet Form =========
if not st.session_state.wagering_closed:
    with st.form("bet_form", clear_on_submit=True):
        st.subheader("Place a Bet")
        st.write("Bettor Name:", st.session_state.current_user)
        horse = st.selectbox("Betting On", 
            ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
             "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
             "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"], key="betting_on")
        bet_type = st.selectbox("Bet Type", ["Win", "Place", "Show"], key="bet_type")
        bet_amount = st.number_input("Bet Amount ($)", min_value=1, step=1, key="bet_amount")
        submitted = st.form_submit_button("Submit Bet")
        if submitted:
            new_row = pd.DataFrame([[st.session_state.current_user, horse, bet_type, bet_amount]],
                                   columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])
            st.session_state.bets = pd.concat([st.session_state.bets, new_row], ignore_index=True)
            st.session_state.bets.to_csv(BETS_FILE, index=False)
            st.success(f"Bet placed: {st.session_state.current_user} bets ${bet_amount} on {horse} ({bet_type})")
else:
    st.error("Betting is closed; no new bets accepted.")

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
bets_df = st.session_state.bets.copy()
bets_df["Win Contrib"] = bets_df.apply(lambda row: effective_contribution(row["Bet Type"], row["Bet Amount"], "Win"), axis=1)
bets_df["Place Contrib"] = bets_df.apply(lambda row: effective_contribution(row["Bet Type"], row["Bet Amount"], "Place"), axis=1)
bets_df["Show Contrib"] = bets_df.apply(lambda row: effective_contribution(row["Bet Type"], row["Bet Amount"], "Show"), axis=1)

total_win_eff = bets_df["Win Contrib"].sum()
total_place_eff = bets_df["Place Contrib"].sum()
total_show_eff = bets_df["Show Contrib"].sum()

st.write("**Effective Win Pool:** $", total_win_eff)
st.write("**Effective Place Pool:** $", total_place_eff)
st.write("**Effective Show Pool:** $", total_show_eff)

# ========= Detailed Wager Summary (by Outcome) =========
st.header("Detailed Wager Summary")
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
    summary["Payout Ratio Win"] = summary["Total Bet Win"].apply(lambda x: (total_win / x) if x > 0 else 0)
    summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(lambda x: (total_place / x) if x > 0 else 0)
    summary["Payout Ratio Show"] = summary["Total Bet Show"].apply(lambda x: (total_show / x) if x > 0 else 0)
    return summary

detailed_summary = create_summary()
st.dataframe(detailed_summary)

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

# ========= Compute Eligible Raw Sums for Payout Calculation =========
win_eligible_total = bets_df.loc[bets_df["Betting On"] == winner, "Win Contrib"].sum()
place_eligible_total = bets_df.loc[bets_df["Betting On"].isin([winner, second]), "Place Contrib"].sum()
show_eligible_total = bets_df.loc[bets_df["Betting On"].isin([winner, second, third]), "Show Contrib"].sum()

# ========= Redistribution: If any pool has zero eligible bets, redistribute its funds =========
win_pool_eff = total_win_eff
place_pool_eff = total_place_eff
show_pool_eff = total_show_eff

pools = [
    {"name": "Win", "pool": total_win_eff, "eligible": win_eligible_total},
    {"name": "Place", "pool": total_place_eff, "eligible": place_eligible_total},
    {"name": "Show", "pool": total_show_eff, "eligible": show_eligible_total},
]

no_winner_pools = [p for p in pools if p["eligible"] == 0 and p["pool"] > 0]
yes_winner_pools = [p for p in pools if p["eligible"] > 0]

extra_funds = sum(p["pool"] for p in no_winner_pools)
sum_winner_pools = sum(p["pool"] for p in yes_winner_pools)

if extra_funds > 0 and sum_winner_pools > 0:
    for p in yes_winner_pools:
        share = p["pool"] / sum_winner_pools
        addition = extra_funds * share
        if p["name"] == "Win":
            win_pool_eff += addition
        elif p["name"] == "Place":
            place_pool_eff += addition
        elif p["name"] == "Show":
            show_pool_eff += addition
    for p in no_winner_pools:
        if p["name"] == "Win":
            win_pool_eff = 0
        elif p["name"] == "Place":
            place_pool_eff = 0
        elif p["name"] == "Show":
            show_pool_eff = 0

st.write(f"**Effective Win Pool (post-redistribution):** ${win_pool_eff:.2f}")
st.write(f"**Effective Place Pool (post-redistribution):** ${place_pool_eff:.2f}")
st.write(f"**Effective Show Pool (post-redistribution):** ${show_pool_eff:.2f}")

# ========= Calculate Final Payout Ratios =========
win_ratio   = (win_pool_eff / win_eligible_total)   if win_eligible_total > 0 else 0
place_ratio = (place_pool_eff / place_eligible_total) if place_eligible_total > 0 else 0
show_ratio  = (show_pool_eff / show_eligible_total)   if show_eligible_total > 0 else 0

st.write("**Final Win Ratio:**", win_ratio)
st.write("**Final Place Ratio:**", place_ratio)
st.write("**Final Show Ratio:**", show_ratio)

# ========= Final Payout Calculation =========
def calculate_payout(row):
    payout = 0.0
    # Sum the payout from each pool this wager qualifies for:
    if row["Betting On"] == winner and row["Win Contrib"] > 0:
        payout += row["Win Contrib"] * win_ratio
    if row["Betting On"] in [winner, second] and row["Place Contrib"] > 0:
        payout += row["Place Contrib"] * place_ratio
    if row["Betting On"] in [winner, second, third] and row["Show Contrib"] > 0:
        payout += row["Show Contrib"] * show_ratio
    return payout

bets_df["Raw Payout"] = bets_df.apply(calculate_payout, axis=1)

# Scale raw payouts so that the sum equals the total bet pool.
total_raw = bets_df["Raw Payout"].sum()
scale_factor = (total_pool / total_raw) if total_raw > 0 else 0
bets_df["Payout"] = bets_df["Raw Payout"] * scale_factor
bets_df.loc[bets_df["Payout"].isna(), "Payout"] = 0

# Remove rows with 0 payout for display
final_df = bets_df[bets_df["Payout"] > 0].copy()

st.header("Individual Payouts")
st.markdown("Only bets with nonzero payouts:")
st.dataframe(final_df[["Bettor Name", "Betting On", "Bet Type", "Bet Amount", "Win Contrib", "Place Contrib", "Show Contrib", "Payout"]])

total_pool_amt = st.session_state.bets["Bet Amount"].sum()
total_payouts = final_df["Payout"].sum()
st.write(f"**Total Wagered:** ${total_pool_amt:.2f}")
st.write(f"**Total Paid Out:** ${total_payouts:.2f}")