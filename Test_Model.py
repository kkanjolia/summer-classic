import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone

########################################
# Session State & Persistence Setup
########################################
BETS_FILE = "bets_data.csv"

def load_bets():
    if os.path.exists(BETS_FILE):
        return pd.read_csv(BETS_FILE)
    else:
        return pd.DataFrame(columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])

if "bets" not in st.session_state:
    st.session_state["bets"] = load_bets()
else:
    st.session_state["bets"] = load_bets()

for key in ["current_user", "admin_logged_in", "wagering_closed", "finishing_order"]:
    if key not in st.session_state:
        if key == "current_user":
            st.session_state[key] = None
        elif key == "admin_logged_in":
            st.session_state[key] = False
        elif key == "wagering_closed":
            st.session_state[key] = False
        else:
            st.session_state[key] = None

########################################
# Title and User Identification
########################################
st.title("2025 Summer Classic")

all_names = [
    "Select a name...",
    "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
    "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
    "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
]

user_choice = st.selectbox("Select Your Name:", all_names, index=0, key="user_select")
if user_choice != "Select a name...":
    st.session_state.current_user = user_choice
else:
    st.session_state.current_user = None

if st.session_state.current_user:
    st.write(f"**Current user:** {st.session_state.current_user}")
else:
    st.warning("Please select your name to place bets.")

########################################
# Helper Functions: Each-Way Processing
########################################
def effective_contribution(bet_type, amount, pool_category):
    """
    Splits each bet into contributions for each pool:
      - For a Win bet: the amount is split equally among Win, Place, and Show.
      - For a Place bet: half goes to Place and half to Show.
      - For a Show bet: 100% goes to Show.
    """
    if bet_type == "Win":
        return amount / 3.0
    elif bet_type == "Place":
        return amount / 2.0 if pool_category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if pool_category == "Show" else 0
    return 0

# Determines eligibility for a given pool based on finishing order.
def eligible_for_pool(row, pool, finishing_order):
    if not finishing_order:
        return False
    win_horse = finishing_order["winner"]
    second_horse = finishing_order["second"]
    third_horse = finishing_order["third"]
    bt = row["Bet Type"]
    outcome = row["Betting On"]
    if pool == "win":
        return (outcome == win_horse and bt == "Win")
    elif pool == "place":
        if outcome == win_horse:
            return bt in ["Win", "Place"]
        elif outcome == second_horse:
            return bt == "Place"
        else:
            return False
    elif pool == "show":
        if outcome == win_horse:
            return True
        elif outcome == second_horse:
            return bt in ["Place", "Show"]
        elif outcome == third_horse:
            return bt == "Show"
        else:
            return False
    return False

########################################
# Admin Login (Sidebar)
########################################
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
admin_login()
if st.session_state.admin_logged_in:
    if st.sidebar.button("Logout Admin", key="logout_button"):
        st.session_state.admin_logged_in = False
        st.success("Logged out.")

########################################
# Wagering Lock Toggle (Admin Only)
########################################
if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock", key="toggle_lock"):
        st.session_state.wagering_closed = not st.session_state.wagering_closed

if st.session_state.wagering_closed:
    st.warning("Betting is closed; no new bets accepted.")
else:
    st.info("Wagering is OPEN.")

########################################
# Admin View: All Wagers
########################################
if st.session_state.admin_logged_in:
    st.subheader("All Wagers (Admin View)")
    st.dataframe(st.session_state.bets)

########################################
# Admin: Delete Bets
########################################
if st.session_state.admin_logged_in:
    st.subheader("Admin: Manage Bets (Delete)")
    if not st.session_state.bets.empty:
        idx_to_delete = st.multiselect("Select wagers to delete", list(st.session_state.bets.index))
        if st.button("Delete Selected Bets", key="delete_wagers"):
            if idx_to_delete:
                st.session_state.bets.drop(idx_to_delete, inplace=True)
                st.session_state.bets.reset_index(drop=True, inplace=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
                st.success("Wagers deleted.")
            else:
                st.error("No wagers selected.")
    else:
        st.info("No wagers to delete.")

########################################
# Public Bet Form
########################################
if (not st.session_state.wagering_closed) and st.session_state.current_user:
    st.subheader("Place a Bet")
    with st.form("bet_form", clear_on_submit=True):
        st.write(f"**Bettor Name:** {st.session_state.current_user}")
        horse = st.selectbox("Betting On", [
            "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
            "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
            "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
        ], key="betting_on")
        btype = st.selectbox("Bet Type", ["Win", "Place", "Show"], key="bet_type")
        amt = st.number_input("Bet Amount ($)", min_value=1, step=1, key="bet_amount")
        submitted = st.form_submit_button("Submit Bet")
        if submitted:
            new_row = pd.DataFrame([[st.session_state.current_user, horse, btype, amt]],
                                   columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])
            st.session_state.bets = pd.concat([st.session_state.bets, new_row], ignore_index=True)
            st.session_state.bets.to_csv(BETS_FILE, index=False)
            st.success(f"Bet placed: {st.session_state.current_user} bet ${amt} on {horse} ({btype})")
else:
    st.error("No name selected or wagering is locked; no new bets accepted.")

########################################
# Pool Calculations & Detailed Summary
########################################
if not st.session_state.bets.empty:
    st.header("Total Pool Size")
    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Win", "Bet Amount"].sum()
    total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Place", "Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Show", "Bet Amount"].sum()
    st.write(f"**Total Pool:** ${total_pool}")
    st.write(f"**Win Pool:** ${total_win}")
    st.write(f"**Place Pool:** ${total_place}")
    st.write(f"**Show Pool:** ${total_show}")
    
    # Compute effective contributions for each bet.
    df = st.session_state.bets.copy()
    df["Win Contrib"] = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Win"), axis=1)
    df["Place Contrib"] = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Place"), axis=1)
    df["Show Contrib"] = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Show"), axis=1)
    
    tw_eff = df["Win Contrib"].sum()
    tp_eff = df["Place Contrib"].sum()
    ts_eff = df["Show Contrib"].sum()
    
    st.write("**Effective Win Pool:** $", tw_eff)
    st.write("**Effective Place Pool:** $", tp_eff)
    st.write("**Effective Show Pool:** $", ts_eff)
    
    st.header("Detailed Wager Summary")
    def create_summary():
        summary = st.session_state.bets.pivot_table(
            index="Betting On",
            columns="Bet Type",
            values="Bet Amount",
            aggfunc="sum",
            fill_value=0
        ).reset_index()
        summary.columns.name = None
        if "Win" in summary.columns:
            summary.rename(columns={"Win": "Total Bet Win"}, inplace=True)
        else:
            summary["Total Bet Win"] = 0
        if "Place" in summary.columns:
            summary.rename(columns={"Place": "Total Bet Place"}, inplace=True)
        else:
            summary["Total Bet Place"] = 0
        if "Show" in summary.columns:
            summary.rename(columns={"Show": "Total Bet Show"}, inplace=True)
        else:
            summary["Total Bet Show"] = 0
        summary["Payout Ratio Win"] = summary["Total Bet Win"].apply(lambda x: (total_win / x) if x > 0 else 0)
        summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(lambda x: (total_place / x) if x > 0 else 0)
        summary["Payout Ratio Show"] = summary["Total Bet Show"].apply(lambda x: (total_show / x) if x > 0 else 0)
        cols = ["Betting On", "Total Bet Win", "Total Bet Place", "Total Bet Show",
                "Payout Ratio Win", "Payout Ratio Place", "Payout Ratio Show"]
        summary = summary[cols]
        return summary
    
    summary_df = create_summary()
    st.dataframe(summary_df)
    
    ########################################
    # Finishing Order & Final Payout Calculation
    ########################################
    finishing_opts = [
        "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
        "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
        "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia", "Mike Leonard"
    ]
    if st.session_state.admin_logged_in:
        st.header("Enter Finishing Order (Admin Only)")
        finish_order = {}
        finish_order["winner"] = st.selectbox("Winner (1st)", finishing_opts, key="winner_select")
        finish_order["second"] = st.selectbox("2nd Place", finishing_opts, key="second_select")
        finish_order["third"] = st.selectbox("3rd Place", finishing_opts, key="third_select")
        st.session_state.finishing_order = finish_order
    else:
        st.info("Only admins can adjust finishing order.")
        if st.session_state.finishing_order:
            finish_order = st.session_state.finishing_order
        else:
            finish_order = None
    
    if finish_order:
        winner = finish_order["winner"]
        second = finish_order["second"]
        third = finish_order["third"]
    
        # Mark eligibility for each pool.
        df["win_eligible"] = df.apply(lambda r: eligible_for_pool(r, "win", finish_order), axis=1)
        df["place_eligible"] = df.apply(lambda r: eligible_for_pool(r, "place", finish_order), axis=1)
        df["show_eligible"] = df.apply(lambda r: eligible_for_pool(r, "show", finish_order), axis=1)
    
        # Compute raw payout ratios per pool.
        eligible_win_total = df.loc[df["win_eligible"], "Win Contrib"].sum()
        eligible_place_total = df.loc[df["place_eligible"], "Place Contrib"].sum()
        eligible_show_total = df.loc[df["show_eligible"], "Show Contrib"].sum()
    
        raw_win_ratio = (total_win / eligible_win_total) if eligible_win_total > 0 else 0
        raw_place_ratio = (total_place / eligible_place_total) if eligible_place_total > 0 else 0
        raw_show_ratio = (total_show / eligible_show_total) if eligible_show_total > 0 else 0
    
        # Compute raw payout for each bet per pool, but extra funds are given only to eligible bets that got 0 raw payout.
        def compute_pool_payout(df, pool, pool_total):
            if pool == "win":
                contrib_col = "Win Contrib"
                raw_col = "win_raw"
                extra_col = "win_extra"
                final_col = "win_final"
            elif pool == "place":
                contrib_col = "Place Contrib"
                raw_col = "place_raw"
                extra_col = "place_extra"
                final_col = "place_final"
            elif pool == "show":
                contrib_col = "Show Contrib"
                raw_col = "show_raw"
                extra_col = "show_extra"
                final_col = "show_final"
            else:
                return df
            eligible_mask = df[pool + "_eligible"]
            total_eligible = df.loc[eligible_mask, contrib_col].sum()
            if total_eligible > 0:
                df[raw_col] = df.apply(lambda r: r[contrib_col] * (pool_total / total_eligible) if r[pool + "_eligible"] else 0, axis=1)
            else:
                df[raw_col] = 0
            claimed = df.loc[eligible_mask, raw_col].sum()
            unclaimed = pool_total - claimed
            # Only distribute extra to eligible bets that got EXACTLY 0 raw payout.
            mask_extra = eligible_mask & (df[raw_col] == 0)
            total_bet = df.loc[mask_extra, "Bet Amount"].sum()
            if total_bet > 0:
                df[extra_col] = df.apply(lambda r: (r["Bet Amount"] / total_bet * unclaimed) if (r[pool + "_eligible"] and r[raw_col] == 0) else 0, axis=1)
            else:
                df[extra_col] = 0
            # Final payout from this pool: if raw payout is > 0, use raw; else, use extra.
            df[final_col] = df.apply(lambda r: r[raw_col] if r[raw_col] > 0 else r[extra_col], axis=1)
            return df
    
        df = compute_pool_payout(df, "win", total_win)
        df = compute_pool_payout(df, "place", total_place)
        df = compute_pool_payout(df, "show", total_show)
    
        # The overall raw payout and extra adjustment:
        df["Raw Payout"] = df["win_raw"] + df["place_raw"] + df["show_raw"]
        df["Extra Adj"] = df["win_extra"] + df["place_extra"] + df["show_extra"]
        df["Final Payout"] = df["win_final"] + df["place_final"] + df["show_final"]
    
        # To ensure the entire pool is paid out, we can adjust any minor rounding differences.
        # (Optionally, you can check if sum(final_payout) equals total_pool and adjust if necessary.)
    
        final_df = df[df["Final Payout"] > 0].copy()
    
        st.header("Individual Payouts (Final)")
        st.markdown("Breakdown per wager: Raw Payout, Extra Adj (extra from unclaimed funds for a pool with zero raw payout), and Final Payout.")
        st.dataframe(final_df[[
            "Bettor Name", "Betting On", "Bet Type", "Bet Amount",
            "Win Contrib", "Place Contrib", "Show Contrib",
            "win_raw", "place_raw", "show_raw",
            "win_extra", "place_extra", "show_extra",
            "Raw Payout", "Extra Adj", "Final Payout"
        ]])
    
        tot_pool_amt = st.session_state.bets["Bet Amount"].sum()
        tot_paid = final_df["Final Payout"].sum()
        st.write(f"**Total Wagered:** ${tot_pool_amt:.2f}")
        st.write(f"**Total Paid Out:** ${tot_paid:.2f}")
    else:
        st.write("No finishing order set by the admin.")
else:
    st.write("No bets placed yet.")