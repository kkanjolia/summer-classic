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

# Load or initialize bets in session_state
st.session_state.bets = load_bets()

# --- Helper Functions for Each-Way Processing ---

def effective_contribution(bet_type, amount, category):
    """
    Returns the effective contribution of a bet to a given pool category.
    - For Win bets: split equally among Win, Place, and Show (amount/3 each).
    - For Place bets: split equally between Place and Show (amount/2 each).
    - For Show bets: full amount goes to Show pool.
    """
    if bet_type == "Win":
        return amount / 3
    elif bet_type == "Place":
        return amount / 2 if category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if category == "Show" else 0
    else:
        return 0

def total_effective_pool(category):
    total = 0
    for _, row in st.session_state.bets.iterrows():
        total += effective_contribution(row["Bet Type"], row["Bet Amount"], category)
    return total

def effective_eligible_sum(bet_type, outcome, category):
    total = 0
    for _, row in st.session_state.bets.iterrows():
        if row["Betting On"] == outcome and row["Bet Type"] == bet_type:
            total += effective_contribution(row["Bet Type"], row["Bet Amount"], category)
    return total

# ========= Admin Login Section in the Sidebar =========
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")  # Set via env var

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

# ========= Public Bet Form =========
def bet_form():
    with st.form("bet_form", clear_on_submit=True):
        Bettor_Name = st.selectbox("Bettor Name", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
                                                  "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
                                                  "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"])
        Who_You_Bet_On = st.selectbox("Betting On", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
                                                    "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
                                                    "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"])
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

# ========= Raw Total Pools =========
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

# ========= Effective Pool Totals (Each-Way Splitting) =========
total_win_eff = total_effective_pool("Win")
total_place_eff = total_effective_pool("Place")
total_show_eff = total_effective_pool("Show")

st.write("**Effective Win Pool:** $", total_win_eff)
st.write("**Effective Place Pool:** $", total_place_eff)
st.write("**Effective Show Pool:** $", total_show_eff)

# ========= Hypothetical Payout Ratios Section (Using Raw Totals) =========
st.header("Bet Summary and Hypothetical Payout Ratios")
st.markdown("""
This table summarizes the bets by Outcome and Bet Type.
It shows the total bet amount per outcome in each category and the hypothetical payout ratio 
(calculated as Total Pool for the category divided by the total bets on that outcome).
""")
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

# ========= Finishing Order Section (Admin Only, but stored for everyone) =========
options = ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", 
           "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", 
           "Kunal Kanjolia", "Mike Leonard"]

if st.session_state.admin_logged_in:
    st.header("Enter Finishing Order (Admin Only)")
    winner = st.selectbox("Winner (1st)", options, key="winner")
    second = st.selectbox("2nd Place", options, key="second")
    third = st.selectbox("3rd Place", options, key="third")
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

# ========= Compute Eligible Effective Sums for Payout Ratio Calculation =========
eligible_win_eff = effective_eligible_sum("Win", winner, "Win")
eligible_place_eff = (effective_eligible_sum("Place", winner, "Place") +
                      effective_eligible_sum("Place", second, "Place"))
eligible_show_eff = (effective_eligible_sum("Show", winner, "Show") +
                     effective_eligible_sum("Show", second, "Show") +
                     effective_eligible_sum("Show", third, "Show"))

# ========= Compute Payout Ratios Based on Effective Values =========
win_ratio = total_win_eff / eligible_win_eff if eligible_win_eff > 0 else 0
place_ratio = total_place_eff / eligible_place_eff if eligible_place_eff > 0 else 0
show_ratio = total_show_eff / eligible_show_eff if eligible_show_eff > 0 else 0

st.write("**Win Payout Ratio:**", win_ratio)
st.write("**Place Payout Ratio:**", place_ratio)
st.write("**Show Payout Ratio:**", show_ratio)

# ========= Raw Bet Summary =========
st.header("Bet Summary")
summary_df = st.session_state.bets.groupby(["Betting On", "Bet Type"])["Bet Amount"].sum().reset_index()
st.dataframe(summary_df)

# ========= Each-Way Payout Calculation =========
WIN_FRACTION = 1/3          # For Win bets: 1/3 to win, 1/3 to place, 1/3 to show
PLACE_FRACTION = 1/2        # For Place bets: 1/2 to place, 1/2 to show

def calculate_payout(row):
    payout = 0
    if winner is not None:
        if row["Betting On"] == winner:
            if row["Bet Type"] == "Win":
                win_eff = row["Bet Amount"] * WIN_FRACTION
                place_eff = row["Bet Amount"] * WIN_FRACTION
                show_eff = row["Bet Amount"] * WIN_FRACTION
                payout = (win_eff / eligible_win_eff * total_win_eff) + \
                         (place_eff / eligible_place_eff * total_place_eff) + \
                         (show_eff / eligible_show_eff * total_show_eff)
            elif row["Bet Type"] == "Place":
                if row["Betting On"] in [winner, second]:
                    place_eff = row["Bet Amount"] * PLACE_FRACTION
                    show_eff = row["Bet Amount"] * PLACE_FRACTION
                    payout = (place_eff / eligible_place_eff * total_place_eff) + \
                             (show_eff / eligible_show_eff * total_show_eff)
            elif row["Bet Type"] == "Show":
                if row["Betting On"] in [winner, second, third]:
                    payout = row["Bet Amount"] / eligible_show_eff * total_show_eff
        elif row["Bet Type"] == "Place" and row["Betting On"] == second:
            place_eff = row["Bet Amount"] * PLACE_FRACTION
            show_eff = row["Bet Amount"] * PLACE_FRACTION
            payout = (place_eff / eligible_place_eff * total_place_eff) + \
                     (show_eff / eligible_show_eff * total_show_eff)
        elif row["Bet Type"] == "Show" and row["Betting On"] == third:
            payout = row["Bet Amount"] / eligible_show_eff * total_show_eff
    return payout

bets_df = st.session_state.bets.copy()
bets_df["Payout"] = bets_df.apply(calculate_payout, axis=1)

st.header("Individual Payouts")
st.markdown("Final Payouts once tournament is over")
st.dataframe(bets_df[["Bettor Name", "Betting On", "Bet Type", "Bet Amount", "Payout"]])