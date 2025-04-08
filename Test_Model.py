import streamlit as st
import pandas as pd
import os

# ======= Persistence Setup: Load bets from file =======
BETS_FILE = "bets_data.csv"

def load_bets():
    if os.path.exists(BETS_FILE):
        return pd.read_csv(BETS_FILE)
    else:
        return pd.DataFrame(columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])

st.session_state.bets = load_bets()

# Admin Login Section in the Sidebar
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")  # Use environment variable for admin password

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

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

admin_login()

if st.session_state.admin_logged_in:
    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.success("Logged out.")

st.title("2025 Summer Classic")

# Public Bet Form
def bet_form():
    with st.form("bet_form", clear_on_submit=True):
        Bettor_Name = st.selectbox("Bettor Name", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"])
        Who_You_Bet_On = st.selectbox("Betting On", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"])
        bet_type = st.selectbox("Bet Type", ["Win", "Place", "Show"])
        bet_amount = st.number_input("**Bet Amount:** $", min_value=0, step=1)
        submitted = st.form_submit_button("Submit Bet")

        if submitted:
            new_bet = pd.DataFrame([[Bettor_Name, Who_You_Bet_On, bet_type, bet_amount]],
                                   columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])
            st.session_state.bets = pd.concat([st.session_state.bets, new_bet], ignore_index=True)
            st.session_state.bets.to_csv(BETS_FILE, index=False)

bet_form()

st.header("Current Bets")
st.markdown("Below are all the bets placed so far.")
st.dataframe(st.session_state.bets[["Bettor Name", "Betting On", "Bet Type", "Bet Amount"]])

# Display total pool size
def calculate_pools():
    total_pool = st.session_state.bets["Bet Amount"].sum()
    total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Win", "Bet Amount"].sum()
    total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Place", "Bet Amount"].sum()
    total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Show", "Bet Amount"].sum()
    return total_pool, total_win, total_place, total_show

total_pool, total_win, total_place, total_show = calculate_pools()

st.header("Total Pool Size")
st.markdown("These are the total wagered amounts for each category:")
st.write("**Total Pool Size:** $", total_pool)
st.write("**Win Pool:** $", total_win)
st.write("**Place Pool:** $", total_place)
st.write("**Show Pool:** $", total_show)

# Hypothetical Payout Ratios Section
st.header("Bet Summary and Hypothetical Payout Ratios")
st.markdown("""
This table summarizes the bets by Outcome and Bet Type.
It shows the total bet amount per outcome in each category and the hypothetical payout ratio 
(calculated as Total Pool for the category divided by the total bets on that outcome).
""")

# Create a pivot table that aggregates total bets by Outcome and Bet Type
def create_summary():
    summary = st.session_state.bets.pivot_table(
        index="Betting On", 
        columns="Bet Type", 
        values="Bet Amount", 
        aggfunc="sum", 
        fill_value=0
    ).reset_index()

    for bet_type in ["Win", "Place", "Show"]:
        if bet_type in summary.columns:
            summary = summary.rename(columns={bet_type: f"Total Bet {bet_type}"})
        else:
            summary[f"Total Bet {bet_type}"] = 0

    summary["Payout Ratio Win"] = summary["Total Bet Win"].apply(lambda x: total_win / x if x > 0 else None)
    summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(lambda x: total_place / x if x > 0 else None)
    summary["Payout Ratio Show"] = summary["Total Bet Show"].apply(lambda x: total_show / x if x > 0 else None)
    
    return summary

summary = create_summary()
st.dataframe(summary)

# Finishing Order Section (Admin Only - but values are stored for everyone)
options = ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", 
           "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", 
           "Kunal Kanjolia", "Mike Leonard"]

if st.session_state.admin_logged_in:
    st.header("Enter Finishing Order (Admin Only)")
    winner = st.selectbox("Winner (1st)", options, key="winner")
    second = st.selectbox("2nd Place", options, key="second")
    third = st.selectbox("3rd Place", options, key="third")
    # Save finishing order to session state so everyone can see the payouts
    st.session_state.finishing_order = {"winner": winner, "second": second, "third": third}
else:
    st.info("Finishing order can only be adjusted by the admin.")
    # Use finishing order stored in session state, if available
    if "finishing_order" in st.session_state:
        order = st.session_state.finishing_order
        winner = order["winner"]
        second = order["second"]
        third = order["third"]
    else:
        winner = second = third = None

# Calculate Eligible Bets & Payout Ratios
def eligible_sum(bet_type, eligible_outcomes):
    df = st.session_state.bets
    return df.loc[(df["Bet Type"] == bet_type) & (df["Betting On"].isin(eligible_outcomes)), "Bet Amount"].sum()

eligible_win = [winner]
eligible_place = [winner, second]
eligible_show = [winner, second, third]

eligible_win_total = eligible_sum("Win", eligible_win)
eligible_place_total = eligible_sum("Place", eligible_place)
eligible_show_total = eligible_sum("Show", eligible_show)

win_ratio = total_win / eligible_win_total if eligible_win_total > 0 else 0
place_ratio = total_place / eligible_place_total if eligible_place_total > 0 else 0
show_ratio = total_show / eligible_show_total if eligible_show_total > 0 else 0

st.header("Bet Summary")

# Group bets by Outcome and Bet Type and calculate the total bet amount for each group.
summary_df = st.session_state.bets.groupby(["Betting On", "Bet Type"])["Bet Amount"].sum().reset_index()
st.dataframe(summary_df)

# Calculate and Display Individual Payouts
def calculate_payout(row):
    """
    Calculates the payout for each bet based on:
      - If a bet is on the winning horse:
            * A "Win" bet gets paid from the win, place, and show pools.
            * A "Place" bet gets paid from the place and show pools.
            * A "Show" bet gets paid from the show pool.
      - Otherwise, no payout.
    """
    payout = 0
    # Only proceed if a finishing order has been set (i.e. winner is not None)
    if winner is not None:
        # Check if the bet's chosen horse is the winner.
        if row["Betting On"] == winner:
            if row["Bet Type"] == "Win":
                # Win bet gets the combined payout of all three pools.
                payout = row["Bet Amount"] * (win_ratio + place_ratio + show_ratio)
            elif row["Bet Type"] == "Place":
                # Place bet gets the combined payout of place and show pools.
                payout = row["Bet Amount"] * (place_ratio + show_ratio)
            elif row["Bet Type"] == "Show":
                # Show bet gets the payout from the show pool.
                payout = row["Bet Amount"] * show_ratio
        # If you also want to allow Place bets on horses that finish second to be eligible:
        elif row["Bet Type"] == "Place" and row["Betting On"] == second:
            payout = row["Bet Amount"] * (place_ratio + show_ratio)
        # And similarly if you want Show bets on third-place horses to be eligible:
        elif row["Bet Type"] == "Show" and row["Betting On"] == third:
            payout = row["Bet Amount"] * show_ratio
    return payout

bets_df = st.session_state.bets.copy()
bets_df["Payout"] = bets_df.apply(calculate_payout, axis=1)

st.header("Individual Payouts")
st.markdown("""
Final Payouts once tournament is over (Payout null until tournament is over) 
""")
st.dataframe(bets_df[["Bettor Name", "Betting On", "Bet Type", "Bet Amount", "Payout"]])