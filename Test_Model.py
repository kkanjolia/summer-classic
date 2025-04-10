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

# Make sure we have the session state keys:
if "bets" not in st.session_state:
    st.session_state["bets"] = load_bets()
else:
    # Refresh from CSV
    st.session_state["bets"] = load_bets()

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "wagering_closed" not in st.session_state:
    st.session_state["wagering_closed"] = False

########################################
#   USER IDENTIFICATION SECTION
########################################
def user_identification():
    # Use a single container to manage both selection and "Back/Change" in one place.
    user_container = st.container()
    with user_container:
        if st.session_state.current_user is None:
            # Show name selection
            st.subheader("Select Your Name")
            selected_name = st.selectbox(
                "Bettor Name",
                [
                    "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
                    "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
                    "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
                ],
                key="user_select"
            )
            if st.button("Confirm Name"):
                st.session_state.current_user = selected_name
                st.experimental_rerun()
        else:
            # Show the confirmed name and a "Back/Change Name" button
            st.write(f"**Current user**: {st.session_state.current_user}")
            if st.button("Back / Change Name"):
                st.session_state.current_user = None
                st.experimental_rerun()

# Call user identification
user_identification()

########################################
#   HELPER FUNCTIONS FOR POOL LOGIC
########################################
def effective_contribution(bet_type, amount, category):
    """ Returns the fraction of a bet that goes to a given pool (Win, Place, Show). """
    if bet_type == "Win":
        return amount / 3 if category in ["Win", "Place", "Show"] else 0
    elif bet_type == "Place":
        if category == "Place" or category == "Show":
            return amount / 2
        else:
            return 0
    elif bet_type == "Show":
        return amount if category == "Show" else 0
    else:
        return 0

def total_effective_pool(category):
    return sum(
        effective_contribution(row["Bet Type"], row["Bet Amount"], category)
        for _, row in st.session_state.bets.iterrows()
    )

########################################
#   ADMIN LOGIN IN SIDEBAR
########################################
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")

def admin_login():
    with st.sidebar:
        st.header("Admin Login")
        admin_pw = st.text_input("Enter admin password", type="password", key="admin_pw")
        if st.button("Login as Admin"):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Logged in as admin.")
            else:
                st.error("Incorrect password.")

admin_login()

if st.session_state.admin_logged_in:
    if st.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.success("Logged out.")

########################################
#   TITLE AND LOCK TOGGLE
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
    st.info("Wagering is OPEN. You can place bets below.")

########################################
#   ADMIN WAGER DELETION
########################################
if st.session_state.admin_logged_in:
    st.subheader("Admin: Manage Bets (Delete Erroneous Bets)")
    if not st.session_state.bets.empty:
        indices_to_delete = st.multiselect("Select wagers to delete", options=list(st.session_state.bets.index))
        if st.button("Delete Selected Bets"):
            if indices_to_delete:
                st.session_state.bets = st.session_state.bets.drop(indices_to_delete).reset_index(drop=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
                st.success("Wagers deleted.")
            else:
                st.error("No wagers selected to delete.")
    else:
        st.info("No wagers found.")

########################################
#   PUBLIC BET FORM
########################################
if not st.session_state.wagering_closed and st.session_state.current_user is not None:
    st.subheader("Place a Bet")
    with st.form("bet_form"):
        st.write(f"Bettor Name: {st.session_state.current_user}")
        horse = st.selectbox("Betting On", [
            "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
            "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
            "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
        ])
        bet_type = st.selectbox("Bet Type", ["Win", "Place", "Show"])
        amt = st.number_input("Bet Amount ($)", min_value=1, step=1)
        submit_bet = st.form_submit_button("Submit Bet")

        if submit_bet:
            new_row = pd.DataFrame(
                [[st.session_state.current_user, horse, bet_type, amt]],
                columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"]
            )
            st.session_state.bets = pd.concat([st.session_state.bets, new_row], ignore_index=True)
            st.session_state.bets.to_csv(BETS_FILE, index=False)
            st.success(f"Bet placed: {st.session_state.current_user} bet ${amt} on {horse} ({bet_type})")

########################################
#   POOL CALCULATIONS
########################################
def calculate_pools():
    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Win", "Bet Amount"].sum()
    total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Place", "Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Show", "Bet Amount"].sum()
    return total_pool, total_win, total_place, total_show

if len(st.session_state.bets) > 0:
    st.header("Total Pool Size")
    total_pool, total_win, total_place, total_show = calculate_pools()
    st.write(f"**Total Pool:** ${total_pool}")
    st.write(f"**Win Pool:** ${total_win}")
    st.write(f"**Place Pool:** ${total_place}")
    st.write(f"**Show Pool:** ${total_show}")

    # Effective pools (each-way splitting)
    bets_df = st.session_state.bets.copy()
    bets_df["Win Contrib"] = bets_df.apply(
        lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Win"), axis=1
    )
    bets_df["Place Contrib"] = bets_df.apply(
        lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Place"), axis=1
    )
    bets_df["Show Contrib"] = bets_df.apply(
        lambda r: effective_contribution(r["Bet Type"], r["Bet Amount"], "Show"), axis=1
    )

    total_win_eff = bets_df["Win Contrib"].sum()
    total_place_eff = bets_df["Place Contrib"].sum()
    total_show_eff = bets_df["Show Contrib"].sum()

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
        for bt in ["Win", "Place", "Show"]:
            if bt in summary.columns:
                summary = summary.rename(columns={bt: f"Total Bet {bt}"})
            else:
                summary[f"Total Bet {bt}"] = 0
        # Calculate raw payout ratios (not necessarily final)
        summary["Payout Ratio Win"] = summary["Total Bet Win"].apply(
            lambda x: (total_win / x) if x > 0 else 0
        )
        summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(
            lambda x: (total_place / x) if x > 0 else 0
        )
        summary["Payout Ratio Show"] = summary["Total Bet Show"].apply(
            lambda x: (total_show / x) if x > 0 else 0
        )
        return summary

    summary_df = create_summary()
    st.dataframe(summary_df)

    # Finishing order
    if st.session_state.admin_logged_in:
        st.header("Enter Finishing Order (Admin Only)")
        finishing_options = [
            "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
            "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
            "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia", "Mike Leonard"
        ]
        winner = st.selectbox("Winner (1st)", finishing_options, key="winner_select")
        second = st.selectbox("2nd Place", finishing_options, key="second_select")
        third = st.selectbox("3rd Place", finishing_options, key="third_select")
        st.session_state.finishing_order = {
            "winner": winner,
            "second": second,
            "third": third
        }
    else:
        st.info("Finishing order can only be adjusted by the admin.")
        if "finishing_order" in st.session_state:
            order = st.session_state.finishing_order
            winner = order["winner"]
            second = order["second"]
            third = order["third"]
        else:
            winner = second = third = None

    # Compute eligibility
    win_eligible_total = bets_df.loc[bets_df["Betting On"] == winner, "Win Contrib"].sum()
    place_eligible_total = bets_df.loc[bets_df["Betting On"].isin([winner, second]), "Place Contrib"].sum()
    show_eligible_total = bets_df.loc[bets_df["Betting On"].isin([winner, second, third]), "Show Contrib"].sum()

    # Redistribute if any pool has zero eligible bets
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
        # zero out the pools that had no winners
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

    # Final Payout Ratios
    win_ratio   = (win_pool_eff / win_eligible_total)   if win_eligible_total>0 else 0
    place_ratio = (place_pool_eff / place_eligible_total) if place_eligible_total>0 else 0
    show_ratio  = (show_pool_eff / show_eligible_total)   if show_eligible_total>0 else 0

    st.write("**Final Win Ratio:**", win_ratio)
    st.write("**Final Place Ratio:**", place_ratio)
    st.write("**Final Show Ratio:**", show_ratio)

    def calculate_payout(row):
        payout = 0.0
        # If a bet is on the winning horse with "Win Contrib"
        if row["Betting On"] == winner and row["Win Contrib"]>0:
            payout += row["Win Contrib"]*win_ratio
        # Place-eligible means bet on winner or second
        if row["Betting On"] in [winner, second] and row["Place Contrib"]>0:
            payout += row["Place Contrib"]*place_ratio
        # Show-eligible means bet on winner or second or third
        if row["Betting On"] in [winner, second, third] and row["Show Contrib"]>0:
            payout += row["Show Contrib"]*show_ratio
        return payout

    bets_df["Raw Payout"] = bets_df.apply(calculate_payout, axis=1)

    # Scale so total payout = total pool
    total_raw = bets_df["Raw Payout"].sum()
    scale_factor = (total_pool / total_raw) if total_raw>0 else 0
    bets_df["Payout"] = bets_df["Raw Payout"]*scale_factor
    bets_df.loc[bets_df["Payout"].isna(), "Payout"] = 0

    final_df = bets_df[bets_df["Payout"]>0].copy()
    st.header("Individual Payouts")
    st.markdown("Only bets with nonzero payouts:")
    st.dataframe(final_df[["Bettor Name","Betting On","Bet Type","Bet Amount",
                           "Win Contrib","Place Contrib","Show Contrib","Payout"]])
    total_pool_amt = st.session_state.bets["Bet Amount"].sum()
    total_payouts = final_df["Payout"].sum()
    st.write(f"**Total Wagered:** ${total_pool_amt:.2f}")
    st.write(f"**Total Paid Out:** ${total_payouts:.2f}")