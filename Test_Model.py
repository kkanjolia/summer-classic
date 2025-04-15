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
      - Win bet: amount is split equally among Win, Place, and Show.
      - Place bet: half goes to Place and half to Show.
      - Show bet: 100% goes to Show.
    """
    if bet_type == "Win":
        return amount / 3.0
    elif bet_type == "Place":
        return amount / 2.0 if pool_category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if pool_category == "Show" else 0
    return 0

def eligible_for_pool(row, pool, finishing_order):
    """
    Determines if a bet (row) is eligible for a given pool.
    For pool "win": only Win bets on the finishing-order winner.
    For pool "place": bets on the winner (if Win/Place) OR on the runner‑up (if Place).
    For pool "show": bets on the winner (all types); on runner‑up if bet as Place/Show; on third if bet as Show.
    """
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
        finish_order = st.session_state.finishing_order
    
    if finish_order:
        winner = finish_order["winner"]
        second = finish_order["second"]
        third = finish_order["third"]
    
        # Mark eligibility for each pool.
        df["win_eligible"] = df.apply(lambda r: (r["Betting On"] == winner and r["Bet Type"] == "Win"), axis=1)
        df["place_eligible"] = df.apply(lambda r: eligible_for_pool(r, "place", finish_order), axis=1)
        df["show_eligible"] = df.apply(lambda r: eligible_for_pool(r, "show", finish_order), axis=1)
    
        # Compute raw payout ratios per pool.
        eligible_win_total = df.loc[df["win_eligible"], "Win Contrib"].sum()
        eligible_place_total = df.loc[df["place_eligible"], "Place Contrib"].sum()
        eligible_show_total = df.loc[df["show_eligible"], "Show Contrib"].sum()
    
        raw_win_ratio = (total_win / eligible_win_total) if eligible_win_total > 0 else 0
        raw_place_ratio = (total_place / eligible_place_total) if eligible_place_total > 0 else 0
        raw_show_ratio = (total_show / eligible_show_total) if eligible_show_total > 0 else 0
    
        # NEW: A simplified function to compute pool payouts
        def compute_pool_payout_simple(df, pool, pool_total, finish_order):
            if pool == "win":
                eligible_mask = (df["Betting On"] == finish_order["winner"]) & (df["Bet Type"] == "Win")
                fallback_mask = eligible_mask  # For win, fallback same as eligible.
                pool_category = "Win"
                contrib_col = "Win Contrib"
            elif pool == "place":
                eligible_mask = df.apply(lambda r: (r["Betting On"] == finish_order["winner"] and r["Bet Type"] in ["Win", "Place"]) or 
                                                    (r["Betting On"] == finish_order["second"] and r["Bet Type"] == "Place"), axis=1)
                fallback_mask = eligible_mask
                pool_category = "Place"
                contrib_col = "Place Contrib"
            else:
                eligible_mask = df.apply(lambda r: (r["Betting On"] == finish_order["winner"]) or 
                                                    (r["Betting On"] == finish_order["second"] and r["Bet Type"] in ["Place", "Show"]) or 
                                                    (r["Betting On"] == finish_order["third"] and r["Bet Type"] == "Show"), axis=1)
                fallback_mask = eligible_mask
                pool_category = "Show"
                contrib_col = "Show Contrib"
            
            # For each row, the effective contribution is as defined.
            df[pool + "_eff"] = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], pool_category), axis=1)
            total_eff = df.loc[eligible_mask, pool + "_eff"].sum()
            if total_eff > 0:
                ratio = pool_total / total_eff
                df[pool + "_raw"] = df.apply(lambda r: r[pool + "_eff"] * ratio if eligible_mask.loc[r.name] else 0, axis=1)
            else:
                total_fb = df.loc[fallback_mask, "Bet Amount"].sum()
                if total_fb > 0:
                    ratio = pool_total / total_fb
                    df[pool + "_raw"] = df.apply(lambda r: r["Bet Amount"] * ratio if fallback_mask.loc[r.name] else 0, axis=1)
                else:
                    df[pool + "_raw"] = 0
            
            raw_total = df[pool + "_raw"].sum()
            remainder = pool_total - raw_total
            if total_eff > 0 and remainder != 0:
                df[pool + "_extra"] = df.apply(lambda r: r[pool + "_eff"] / total_eff * remainder if eligible_mask.loc[r.name] else 0, axis=1)
            else:
                df[pool + "_extra"] = 0
            df[pool + "_final"] = df[pool + "_raw"] + df[pool + "_extra"]
            return df
        
        df = compute_pool_payout_simple(df, "win", total_win, finish_order)
        df = compute_pool_payout_simple(df, "place", total_place, finish_order)
        df = compute_pool_payout_simple(df, "show", total_show, finish_order)
    
        df["Final Payout"] = df["win_final"] + df["place_final"] + df["show_final"]
    
        final_df = df[df["Final Payout"] > 0].copy()
    
        st.header("Individual Payouts (Final)")
        st.markdown("Breakdown per wager (only showing bets with a positive final payout):")
        st.dataframe(final_df[[
            "Bettor Name", "Betting On", "Bet Type", "Bet Amount",
            "win_final", "place_final", "show_final", "Final Payout"
        ]])
    
        st.write(f"**Total Wagered:** ${total_pool:.2f}")
        tot_paid = final_df["Final Payout"].sum()
        st.write(f"**Total Paid Out:** ${tot_paid:.2f}")
    else:
        st.write("No finishing order set by the admin.")
else:
    st.write("No bets placed yet.")