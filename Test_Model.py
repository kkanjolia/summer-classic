import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone

########################################
# SESSION STATE & PERSISTENCE SETUP
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

# Ensure required keys exist:
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
# TITLE & USER IDENTIFICATION
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
# HELPER FUNCTIONS: POOL ELIGIBILITY
########################################
def eligible_for_pool(row, pool, finishing_order):
    """
    Returns True if the wager qualifies for the specified pool:
      - For "win": Only wagers with Bet Type "Win" on the winning horse.
      - For "place": Wagers on the winning horse qualify if bet as "Win" or "Place";
                   wagers on the runner‑up qualify if bet as "Place".
      - For "show": Wagers on the winning horse qualify (all types);
                   wagers on the runner‑up qualify if bet as "Place" or "Show";
                   wagers on the third‑place horse qualify if bet as "Show".
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
# ADMIN LOGIN & CONTROLS (SIDEBAR)
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

if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock", key="toggle_lock"):
        st.session_state.wagering_closed = not st.session_state.wagering_closed

if st.session_state.wagering_closed:
    st.warning("Betting is closed; no new bets accepted.")
else:
    st.info("Wagering is OPEN.")

if st.session_state.admin_logged_in:
    st.subheader("All Wagers (Admin View)")
    st.dataframe(st.session_state.bets)

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
# PUBLIC BET FORM
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
# POOL CALCULATIONS & DETAILED SUMMARY
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
    
    # Use a pure pari-mutuel method.
    # For each pool, only wagers that are eligible contribute their full wager amount.
    # Payout ratio = (Pool Total) / (Sum of effective wagers among eligible bets)
    # A wager’s payout from that pool = (its full wager) * ratio, if it qualifies.
    df = st.session_state.bets.copy()
    
    # Admin sets finishing order.
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
    
        # Effective wager calculations:
        # Win Pool: Only bets with Bet Type "Win" on the winning horse.
        df["eff_win"] = df.apply(lambda r: r["Bet Amount"] if (r["Betting On"]==winner and r["Bet Type"]=="Win") else 0, axis=1)
        # Place Pool: For the winner, Win or Place bets qualify; for the runner-up, only Place bets.
        df["eff_place"] = df.apply(lambda r: r["Bet Amount"] if ((r["Betting On"]==winner and r["Bet Type"] in ["Win", "Place"]) or (r["Betting On"]==second and r["Bet Type"]=="Place")) else 0, axis=1)
        # Show Pool: For the winner, all bets qualify; for second if bet as Place/Show; for third if bet as Show.
        df["eff_show"] = df.apply(lambda r: r["Bet Amount"] if ((r["Betting On"]==winner) or 
                                                               (r["Betting On"]==second and r["Bet Type"] in ["Place", "Show"]) or 
                                                               (r["Betting On"]==third and r["Bet Type"]=="Show"))
                                   else 0, axis=1)
    
        total_eff_win = df["eff_win"].sum()
        total_eff_place = df["eff_place"].sum()
        total_eff_show = df["eff_show"].sum()
    
        # Compute payout ratios for each pool.
        win_ratio = total_win / total_eff_win if total_eff_win > 0 else 0
        place_ratio = total_place / total_eff_place if total_eff_place > 0 else 0
        show_ratio = total_show / total_eff_show if total_eff_show > 0 else 0
    
        # Calculate individual payouts per pool.
        df["win_payout"] = df["eff_win"] * win_ratio
        df["place_payout"] = df["eff_place"] * place_ratio
        df["show_payout"] = df["eff_show"] * show_ratio
        
        # Final payout is the sum across the pools.
        df["Final Payout"] = df["win_payout"] + df["place_payout"] + df["show_payout"]
        
        # Filter out wagers with no payout.
        final_df = df[df["Final Payout"] > 0].copy()
        
        st.header("Individual Payouts (Final)")
        st.markdown("Breakdown per wager (only displaying bets that receive a positive payout):")
        st.dataframe(final_df[[
            "Bettor Name", "Betting On", "Bet Type", "Bet Amount",
            "eff_win", "eff_place", "eff_show",
            "win_payout", "place_payout", "show_payout", "Final Payout"
        ]])
        
        st.write(f"**Total Wagered:** ${total_pool:.2f}")
        tot_paid = final_df["Final Payout"].sum()
        st.write(f"**Total Paid Out:** ${tot_paid:.2f}")
    else:
        st.write("No finishing order set by the admin.")
else:
    st.write("No bets placed yet.")