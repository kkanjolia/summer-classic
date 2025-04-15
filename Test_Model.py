import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone

########################################
#  Session State & Persistence Setup
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

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "wagering_closed" not in st.session_state:
    st.session_state["wagering_closed"] = False

########################################
#  Title and User Identification
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
#  Helper Functions: Each-Way Processing
########################################
def effective_contribution(bet_type, amount, pool_category):
    """
    Splits each bet into contributions for the Win, Place, and Show pools:
      - Win bet: split 1/3 to Win, 1/3 to Place, 1/3 to Show.
      - Place bet: split 50/50 between Place and Show.
      - Show bet: 100% to Show.
    """
    if bet_type == "Win":
        return amount / 3.0
    elif bet_type == "Place":
        return amount / 2.0 if pool_category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if pool_category == "Show" else 0
    return 0

########################################
#  Admin Login (Sidebar)
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
#  Wagering Lock Toggle (Admin Only)
########################################
if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock", key="toggle_lock"):
        st.session_state.wagering_closed = not st.session_state.wagering_closed

if st.session_state.wagering_closed:
    st.warning("Betting is closed; no new bets accepted.")
else:
    st.info("Wagering is OPEN.")

########################################
#  Admin View: All Wagers
########################################
if st.session_state.admin_logged_in:
    st.subheader("All Wagers (Admin View)")
    st.dataframe(st.session_state.bets)

########################################
#  Admin: Delete Bets
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
#  Public Bet Form
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
#  Pool Calculations & Detailed Summary
########################################
if not st.session_state.bets.empty:
    st.header("Total Pool Size")
    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Win", "Bet Amount"].sum()
    total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Place", "Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Show", "Bet Amount"].sum()
    st.write(f"**Total Pool:** ${total_pool}")
    st.write(f"**Win Pool:** ${total_win}")
    st.write(f"**Place Pool:** ${total_place}")
    st.write(f"**Show Pool:** ${total_show}")
    
    # Calculate effective contributions (each-way splits)
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
    #  Finishing Order & Final Payout Calculation
    ########################################
    finishing_opts = [
        "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
        "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
        "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia", "Mike Leonard"
    ]
    if st.session_state.admin_logged_in:
        st.header("Enter Finishing Order (Admin Only)")
        winner = st.selectbox("Winner (1st)", finishing_opts, key="winner_select")
        second = st.selectbox("2nd Place", finishing_opts, key="second_select")
        third = st.selectbox("3rd Place", finishing_opts, key="third_select")
        st.session_state.finishing_order = {"winner": winner, "second": second, "third": third}
    else:
        st.info("Only admins can adjust finishing order.")
        if "finishing_order" in st.session_state:
            order = st.session_state.finishing_order
            winner = order["winner"]
            second = order["second"]
            third = order["third"]
        else:
            winner = second = third = None
    
    if winner:
        # Calculate eligible contributions for each pool
        weff = df.loc[df["Betting On"] == winner, "Win Contrib"].sum()
        peff = df.loc[df["Betting On"].isin([winner, second]), "Place Contrib"].sum()
        seff = df.loc[df["Betting On"].isin([winner, second, third]), "Show Contrib"].sum()
    
        # For raw payout ratios, compute based on total pool per category.
        raw_win_ratio = (total_win / weff) if weff > 0 else 0
        raw_place_ratio = (total_place / peff) if peff > 0 else 0
        raw_show_ratio = (total_show / seff) if seff > 0 else 0
    
        # Compute raw payout for each bet based on its eligibility:
        def calculate_raw_payout(row):
            win_part = 0
            place_part = 0
            show_part = 0
            if row["Betting On"] == winner:
                if row["Bet Type"] == "Win":
                    win_part = row["Win Contrib"] * raw_win_ratio
                    place_part = row["Place Contrib"] * raw_place_ratio
                    show_part = row["Show Contrib"] * raw_show_ratio
                elif row["Bet Type"] == "Place":
                    place_part = row["Place Contrib"] * raw_place_ratio
                    show_part = row["Show Contrib"] * raw_show_ratio
                elif row["Bet Type"] == "Show":
                    show_part = row["Show Contrib"] * raw_show_ratio
            elif row["Betting On"] == second:
                if row["Bet Type"] == "Place":
                    place_part = row["Place Contrib"] * raw_place_ratio
                    show_part = row["Show Contrib"] * raw_show_ratio
                elif row["Bet Type"] == "Show":
                    show_part = row["Show Contrib"] * raw_show_ratio
            elif row["Betting On"] == third:
                if row["Bet Type"] == "Show":
                    show_part = row["Show Contrib"] * raw_show_ratio
            return win_part + place_part + show_part
    
        df["Raw Payout"] = df.apply(calculate_raw_payout, axis=1)
        total_raw = df["Raw Payout"].sum()
    
        # Compute the total unclaimed funds.
        total_unclaimed = total_pool - total_raw
    
        # Distribute unclaimed funds only to bets that had no Raw Payout from their eligible pool.
        # First, identify bets with zero raw payout.
        df["Extra Adj"] = df.apply(lambda r: (r["Bet Amount"] / total_pool) * total_unclaimed
                                   if r["Raw Payout"] == 0 else 0, axis=1)
    
        # Final Payout = Raw Payout + Extra Adjustment.
        df["Final Payout"] = df["Raw Payout"] + df["Extra Adj"]
    
        final_df = df[df["Final Payout"] > 0].copy()
    
        st.header("Individual Payouts (Final)")
        st.markdown("The table below shows for each wager: the Raw Payout, Extra Adj (pro rata extra), and Final Payout.")
        st.dataframe(final_df[[
            "Bettor Name", "Betting On", "Bet Type", "Bet Amount",
            "Win Contrib", "Place Contrib", "Show Contrib",
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