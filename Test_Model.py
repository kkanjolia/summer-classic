import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone
from math import isclose

########################################
#   Load or Initialize Session State
########################################
BETS_FILE = "bets_data.csv"

def load_bets():
    """Load bets from the CSV file, or return an empty DataFrame if none found."""
    if os.path.exists(BETS_FILE):
        return pd.read_csv(BETS_FILE)
    else:
        return pd.DataFrame(columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])

if "bets" not in st.session_state:
    st.session_state["bets"] = load_bets()
else:
    # Refresh from CSV on each run
    st.session_state["bets"] = load_bets()

# Ensure the main keys exist
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "wagering_closed" not in st.session_state:
    st.session_state["wagering_closed"] = False

########################################
#   User Identification
########################################
def user_identification():
    """Handle the user name selection or editing in a single click each."""
    if st.session_state.current_user is None:
        st.subheader("Select Your Name")
        selected_name = st.selectbox(
            "Bettor Name",
            [
                "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
                "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
                "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
            ]
        )
        if st.button("Confirm Name"):
            # Store the selected name in session state
            st.session_state.current_user = selected_name
            st.success(f"Name confirmed: {selected_name}")
    else:
        st.write(f"**Current user**: {st.session_state.current_user}")
        if st.button("Back / Change Name"):
            # Clear the user selection
            st.session_state.current_user = None

user_identification()

########################################
#   Helper: Effective Contribution
########################################
def effective_contribution(bet_type, amount, category):
    """
    Returns how much of 'amount' goes to the Win / Place / Show pools based on bet_type.
    """
    if bet_type == "Win":
        return amount / 3.0 if category in ["Win","Place","Show"] else 0
    elif bet_type == "Place":
        # Place bets split 50/50 between Place and Show
        return amount / 2.0 if category in ["Place","Show"] else 0
    elif bet_type == "Show":
        return amount if category=="Show" else 0
    return 0

########################################
#   Admin Login (Sidebar)
########################################
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")
def admin_login():
    with st.sidebar:
        st.header("Admin Login")
        admin_pw = st.text_input("Enter admin password", type="password")
        if st.button("Login as Admin"):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Logged in as admin.")
            else:
                st.error("Incorrect password.")

admin_login()

if st.session_state.admin_logged_in:
    if st.sidebar.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.success("Logged out.")

########################################
#   Title and Wagering Lock Toggle
########################################
st.title("2025 Summer Classic")

if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock"):
        st.session_state.wagering_closed = not st.session_state.wagering_closed
        if st.session_state.wagering_closed:
            st.success("Wagering locked.")
        else:
            st.info("Wagering unlocked.")

if st.session_state.wagering_closed:
    st.warning("Wagering is LOCKED. No new bets accepted.")
else:
    st.info("Wagering is OPEN. Place bets below if you have selected your name.")

########################################
#   Admin Wager Management (Delete Bets)
########################################
if st.session_state.admin_logged_in:
    st.subheader("Admin: Manage Bets (Delete)")
    if not st.session_state.bets.empty:
        to_delete = st.multiselect("Select wagers to delete", st.session_state.bets.index)
        if st.button("Delete Selected Bets"):
            if to_delete:
                st.session_state.bets.drop(to_delete, inplace=True)
                st.session_state.bets.reset_index(drop=True, inplace=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
                st.success("Wagers deleted.")
            else:
                st.error("No wagers selected.")
    else:
        st.info("No wagers to delete.")

########################################
#   Public Bet Form
########################################
if not st.session_state.wagering_closed and st.session_state.current_user is not None:
    st.subheader("Place a Bet")
    with st.form("bet_form", clear_on_submit=True):
        st.write(f"Bettor Name: {st.session_state.current_user}")
        horse = st.selectbox("Betting On", [
            "Anthony Sousa","Connor Donovan","Chris Brown","Jared Joaquin",
            "Jim Alexander","Joe Canavan","Mark Leonard","Pete Koskores",
            "Pete Sullivan","Kunal Kanjolia","Mike Leonard","Ryan Barcome"
        ])
        btype = st.selectbox("Bet Type", ["Win","Place","Show"])
        amt = st.number_input("Bet Amount ($)", min_value=1, step=1)
        submitted = st.form_submit_button("Submit Bet")

        if submitted:
            new_row = pd.DataFrame(
                [[st.session_state.current_user, horse, btype, amt]],
                columns=["Bettor Name","Betting On","Bet Type","Bet Amount"]
            )
            st.session_state.bets = pd.concat([st.session_state.bets, new_row], ignore_index=True)
            st.session_state.bets.to_csv(BETS_FILE, index=False)
            st.success(f"Bet placed: {st.session_state.current_user} bet ${amt} on {horse} ({btype})")

########################################
#   If we have bets, show pools etc.
########################################
if len(st.session_state.bets)>0:
    st.header("Total Pool Size")

    # Raw totals
    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Win","Bet Amount"].sum()
    total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Place","Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Show","Bet Amount"].sum()

    st.write(f"**Total Pool:** ${total_pool}")
    st.write(f"**Win Pool:** ${total_win}")
    st.write(f"**Place Pool:** ${total_place}")
    st.write(f"**Show Pool:** ${total_show}")

    # Effective splitted totals
    bets_df = st.session_state.bets.copy()
    bets_df["Win Contrib"]   = bets_df.apply(lambda r: effective_contribution(r["Bet Type"],r["Bet Amount"],"Win"), axis=1)
    bets_df["Place Contrib"] = bets_df.apply(lambda r: effective_contribution(r["Bet Type"],r["Bet Amount"],"Place"), axis=1)
    bets_df["Show Contrib"]  = bets_df.apply(lambda r: effective_contribution(r["Bet Type"],r["Bet Amount"],"Show"), axis=1)

    total_win_eff   = bets_df["Win Contrib"].sum()
    total_place_eff = bets_df["Place Contrib"].sum()
    total_show_eff  = bets_df["Show Contrib"].sum()

    st.write("**Effective Win Pool:** $", total_win_eff)
    st.write("**Effective Place Pool:** $", total_place_eff)
    st.write("**Effective Show Pool:** $", total_show_eff)

    # Detailed Wager Summary
    st.header("Detailed Wager Summary")

    def create_summary():
        summary = st.session_state.bets.pivot_table(
            index="Betting On",
            columns="Bet Type",
            values="Bet Amount",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        # Rename or create columns for Win/Place/Show
        for btype in ["Win","Place","Show"]:
            if btype not in summary.columns:
                summary[btype]=0
            else:
                summary.rename(columns={btype: f"Total Bet {btype}"}, inplace=True)

        # Raw ratio
        summary["Payout Ratio Win"]   = summary["Total Bet Win"].apply(
            lambda x: (total_win / x) if x>0 else 0
        )
        summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(
            lambda x: (total_place / x) if x>0 else 0
        )
        summary["Payout Ratio Show"]  = summary["Total Bet Show"].apply(
            lambda x: (total_show / x) if x>0 else 0
        )
        return summary

    summary_df = create_summary()
    st.dataframe(summary_df)

    # Admin sets finishing order
    if st.session_state.admin_logged_in:
        st.header("Enter Finishing Order (Admin Only)")
        finishing_options = [
            "Anthony Sousa","Connor Donovan","Chris Brown","Jared Joaquin",
            "Jim Alexander","Joe Canavan","Mark Leonard","Pete Koskores",
            "Pete Sullivan","Ryan Barcome","Kunal Kanjolia","Mike Leonard"
        ]
        winner = st.selectbox("Winner (1st)", finishing_options, key="winner_select")
        second = st.selectbox("2nd Place", finishing_options, key="second_select")
        third  = st.selectbox("3rd Place", finishing_options, key="third_select")
        st.session_state.finishing_order = {
            "winner":winner,"second":second,"third":third
        }
    else:
        st.info("Finishing order can only be adjusted by the admin.")
        if "finishing_order" in st.session_state:
            order = st.session_state.finishing_order
            winner = order["winner"]
            second = order["second"]
            third  = order["third"]
        else:
            winner = second = third = None

    # If finishing order is set, compute final payouts
    if winner:
        weff = bets_df.loc[bets_df["Betting On"]==winner, "Win Contrib"].sum()
        peff = bets_df.loc[bets_df["Betting On"].isin([winner,second]), "Place Contrib"].sum()
        seff = bets_df.loc[bets_df["Betting On"].isin([winner,second,third]), "Show Contrib"].sum()

        wpool_eff   = total_win_eff
        ppool_eff   = total_place_eff
        spool_eff   = total_show_eff

        data_pools = [
            {"name":"Win","pool":wpool_eff,"eligible":weff},
            {"name":"Place","pool":ppool_eff,"eligible":peff},
            {"name":"Show","pool":spool_eff,"eligible":seff},
        ]
        no_winners  = [p for p in data_pools if p["eligible"]==0 and p["pool"]>0]
        yes_winners = [p for p in data_pools if p["eligible"]>0]
        extra_funds = sum([p["pool"] for p in no_winners])
        sum_winner_pools = sum([p["pool"] for p in yes_winners])

        if extra_funds>0 and sum_winner_pools>0:
            for p in yes_winners:
                ratio  = p["pool"] / sum_winner_pools
                additn = extra_funds*ratio
                if p["name"]=="Win":
                    wpool_eff += additn
                elif p["name"]=="Place":
                    ppool_eff += additn
                elif p["name"]=="Show":
                    spool_eff += additn
            # zero out pools that had no winners
            for p in no_winners:
                if p["name"]=="Win":
                    wpool_eff=0
                elif p["name"]=="Place":
                    ppool_eff=0
                elif p["name"]=="Show":
                    spool_eff=0

        st.write(f"**Effective Win Pool (post-redistribution):** ${wpool_eff:.2f}")
        st.write(f"**Effective Place Pool (post-redistribution):** ${ppool_eff:.2f}")
        st.write(f"**Effective Show Pool (post-redistribution):** ${spool_eff:.2f}")

        wratio = (wpool_eff/weff) if weff>0 else 0
        pratio = (ppool_eff/peff) if peff>0 else 0
        sratio = (spool_eff/seff) if seff>0 else 0

        st.write("**Final Win Ratio:**", wratio)
        st.write("**Final Place Ratio:**", pratio)
        st.write("**Final Show Ratio:**", sratio)

        def calc_payout(row):
            pay=0
            if row["Betting On"]==winner and row["Win Contrib"]>0:
                pay += row["Win Contrib"]*wratio
            if row["Betting On"] in [winner,second] and row["Place Contrib"]>0:
                pay += row["Place Contrib"]*pratio
            if row["Betting On"] in [winner,second,third] and row["Show Contrib"]>0:
                pay += row["Show Contrib"]*sratio
            return pay

        bets_df["Raw Payout"] = bets_df.apply(calc_payout, axis=1)
        total_raw = bets_df["Raw Payout"].sum()
        sfactor   = (total_pool / total_raw) if total_raw>0 else 0
        bets_df["Payout"] = bets_df["Raw Payout"]*sfactor
        bets_df.loc[bets_df["Payout"].isna(),"Payout"]=0

        final_df = bets_df[bets_df["Payout"]>0].copy()
        st.header("Individual Payouts")
        st.markdown("Only bets with nonzero payouts:")
        st.dataframe(
            final_df[["Bettor Name","Betting On","Bet Type","Bet Amount","Win Contrib","Place Contrib","Show Contrib","Payout"]]
        )
        tot_pool_amt = st.session_state.bets["Bet Amount"].sum()
        tot_payout   = final_df["Payout"].sum()
        st.write(f"**Total Wagered:** ${tot_pool_amt:.2f}")
        st.write(f"**Total Paid Out:** ${tot_payout:.2f}")
    else:
        st.write("Finishing order is not yet set by the admin.")