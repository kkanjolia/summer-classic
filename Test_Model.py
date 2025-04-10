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
#   Title
########################################
st.title("2025 Summer Classic")

########################################
#   User Identification (Single Drop-Down)
########################################
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
#   Helper Functions: Each-Way Processing
########################################
def effective_contribution(bet_type, amount, category):
    """
    - Win bets: amount/3 each to Win, Place, Show
    - Place bets: amount/2 each to Place, Show
    - Show bets: full amount to Show
    """
    if bet_type == "Win":
        return amount / 3.0
    elif bet_type == "Place":
        return amount / 2.0 if category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if category == "Show" else 0
    else:
        return 0

########################################
#   Admin Login (Sidebar)
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
#   Wagering Lock Toggle (Admin Only)
########################################
if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock"):
        st.session_state.wagering_closed = not st.session_state.wagering_closed

########################################
#   Show Only One Banner
########################################
if st.session_state.wagering_closed:
    st.warning("Betting is closed; no new bets accepted.")
else:
    st.info("Wagering is OPEN.")

########################################
#   Admin: Delete Bets
########################################
if st.session_state.admin_logged_in:
    st.subheader("Admin: Manage Bets (Delete)")
    if not st.session_state.bets.empty:
        indices_to_delete = st.multiselect("Select wager row indices to delete", list(st.session_state.bets.index))
        if st.button("Delete Selected Bets"):
            if indices_to_delete:
                st.session_state.bets.drop(indices_to_delete, inplace=True)
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
if (not st.session_state.wagering_closed) and st.session_state.current_user:
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
else:
    st.error("No name selected or wagering is locked; no new bets accepted.")

########################################
#   Pool Calculations & Detailed Summary
########################################
if len(st.session_state.bets)>0:
    st.header("Total Pool Size")

    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win  = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Win","Bet Amount"].sum()
    total_place= st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Place","Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"]=="Show","Bet Amount"].sum()

    st.write(f"**Total Pool:** ${total_pool}")
    st.write(f"**Win Pool:**   ${total_win}")
    st.write(f"**Place Pool:** ${total_place}")
    st.write(f"**Show Pool:**  ${total_show}")

    # Effective splitted totals
    df = st.session_state.bets.copy()
    df["Win Contrib"]   = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Win"), axis=1)
    df["Place Contrib"] = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Place"), axis=1)
    df["Show Contrib"]  = df.apply(lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Show"), axis=1)

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
        # rename or create columns for Win/Place/Show
        if "Win" in summary.columns:
            summary.rename(columns={"Win":"Total Bet Win"}, inplace=True)
        else:
            summary["Total Bet Win"]=0
        if "Place" in summary.columns:
            summary.rename(columns={"Place":"Total Bet Place"}, inplace=True)
        else:
            summary["Total Bet Place"]=0
        if "Show" in summary.columns:
            summary.rename(columns={"Show":"Total Bet Show"}, inplace=True)
        else:
            summary["Total Bet Show"]=0

        summary["Payout Ratio Win"]   = summary["Total Bet Win"].apply(  lambda x: total_win/x if x>0 else 0)
        summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(lambda x: total_place/x if x>0 else 0)
        summary["Payout Ratio Show"]  = summary["Total Bet Show"].apply( lambda x: total_show/x if x>0 else 0)
        return summary

    summary_df = create_summary()
    st.dataframe(summary_df)

    # Finishing order
    st.subheader("Finishing Order (Admin Only)")
    finishing_opts = [
        "Anthony Sousa","Connor Donovan","Chris Brown","Jared Joaquin",
        "Jim Alexander","Joe Canavan","Mark Leonard","Pete Koskores",
        "Pete Sullivan","Ryan Barcome","Kunal Kanjolia","Mike Leonard"
    ]
    if st.session_state.admin_logged_in:
        winner = st.selectbox("Winner (1st)", finishing_opts, key="winner_select")
        second = st.selectbox("2nd Place", finishing_opts, key="second_select")
        third  = st.selectbox("3rd Place", finishing_opts, key="third_select")
        st.session_state.finishing_order = {"winner":winner, "second":second, "third":third}
    else:
        if "finishing_order" in st.session_state:
            order = st.session_state.finishing_order
            winner = order["winner"]
            second = order["second"]
            third  = order["third"]
        else:
            winner = second = third = None
        st.info("Only admins can adjust finishing order.")

    if winner:
        weff = df.loc[df["Betting On"]==winner, "Win Contrib"].sum()
        peff = df.loc[df["Betting On"].isin([winner, second]), "Place Contrib"].sum()
        seff = df.loc[df["Betting On"].isin([winner, second, third]), "Show Contrib"].sum()

        wpool_eff = tw_eff
        ppool_eff = tp_eff
        spool_eff = ts_eff

        data_pools = [
            {"name":"Win","pool":tw_eff,"eligible":weff},
            {"name":"Place","pool":tp_eff,"eligible":peff},
            {"name":"Show","pool":ts_eff,"eligible":seff}
        ]
        no_winners = [p for p in data_pools if p["eligible"]==0 and p["pool"]>0]
        yes_winners= [p for p in data_pools if p["eligible"]>0]
        extra_funds = sum([p["pool"] for p in no_winners])
        sum_winners = sum([p["pool"] for p in yes_winners])

        if extra_funds>0 and sum_winners>0:
            for p in yes_winners:
                ratio  = p["pool"]/sum_winners
                additn = extra_funds*ratio
                if p["name"]=="Win":   wpool_eff += additn
                elif p["name"]=="Place": ppool_eff += additn
                elif p["name"]=="Show":  spool_eff += additn
            for p in no_winners:
                if p["name"]=="Win":   wpool_eff=0
                elif p["name"]=="Place": ppool_eff=0
                elif p["name"]=="Show": spool_eff=0

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
            if row["Betting On"] in [winner, second] and row["Place Contrib"]>0:
                pay += row["Place Contrib"]*pratio
            if row["Betting On"] in [winner, second, third] and row["Show Contrib"]>0:
                pay += row["Show Contrib"]*sratio
            return pay

        df["Raw Payout"] = df.apply(calc_payout, axis=1)
        total_raw = df["Raw Payout"].sum()
        sfactor = (total_pool / total_raw) if total_raw>0 else 0
        df["Payout"] = df["Raw Payout"]*sfactor
        df.loc[df["Payout"].isna(),"Payout"]=0

        final_df = df[df["Payout"]>0].copy()
        st.header("Individual Payouts")
        st.markdown("Only bets with nonzero payouts:")
        st.dataframe(final_df[[
            "Bettor Name","Betting On","Bet Type","Bet Amount",
            "Win Contrib","Place Contrib","Show Contrib","Payout"
        ]])
        tot_pool = st.session_state.bets["Bet Amount"].sum()
        tot_paid = final_df["Payout"].sum()
        st.write(f"**Total Wagered:** ${tot_pool:.2f}")
        st.write(f"**Total Paid Out:** ${tot_paid:.2f}")
    else:
        st.write("No finishing order set by the admin.")
else:
    st.write("No bets placed yet.")