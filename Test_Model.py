import streamlit as st
import pandas as pd

# Initialize session state for bets if not already set.
if "bets" not in st.session_state:
    st.session_state.bets = pd.DataFrame(columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])

# 1. Admin Login Section in the Sidebar
ADMIN_PASSWORD = "Southboston15!"  # Replace with your admin password

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

    # If already logged in, show a logout button
if st.session_state.admin_logged_in:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.success("Logged out.")

st.title("2025 Summer Classic")

#1 Public Bet Form (this section is visible to everyone)
with st.form("bet_form", clear_on_submit=True):
    Bettor_Name = st.selectbox("Bettor Name", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia",  "Mike Leonard"])
    Who_You_Bet_On = st.selectbox("Betting On", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia",  "Mike Leonard"])
    bet_type = st.selectbox("Bet Type", ["Win","Place","Show"])
    bet_amount = st.number_input("**Bet Amount:** $", min_value=0, step=1)
    submitted = st.form_submit_button("Submit Bet")

    if submitted:
        new_bet = pd.DataFrame([[Bettor_Name, Who_You_Bet_On, bet_type, bet_amount]],
                                columns=["Bettor Name", "Betting On", "Bet Type", "Bet Amount"])
        st.session_state.bets = pd.concat([st.session_state.bets, new_bet], ignore_index=True)

st.header("Current Bets")
st.markdown("Below are all the bets placed so far.")
st.dataframe(st.session_state.bets[["Bettor Name", "Betting On", "Bet Type", "Bet Amount"]])


#2 Display total pool size (total bet amount across all bets)
total_pool = st.session_state.bets["Bet Amount"].sum()
total_win = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Win", "Bet Amount"].sum()
total_place = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Place", "Bet Amount"].sum()
total_show = st.session_state.bets.loc[st.session_state.bets["Bet Type"] == "Show", "Bet Amount"].sum()

st.header("Total Pool Size")
st.markdown("These are the total wagered amounts for each category:")
st.write("**Total Pool Size:** $", total_pool)
st.write("**Win Pool:** $", total_win)
st.write("**Place Pool:** $", total_place)
st.write("**Show Pool:** $", total_show)


# --- Hypothetical Payout Ratios Section ---
st.header("Bet Summary and Hypothetical Payout Ratios")
st.markdown("""
This table summarizes the bets by Outcome and Bet Type.
It shows the total bet amount per outcome in each category and the hypothetical payout ratio 
(calculated as Total Pool for the category divided by the total bets on that outcome).
""")

# Create a pivot table that aggregates total bets by Outcome and Bet Type
# Create the pivot table
summary = st.session_state.bets.pivot_table(
    index="Betting On", 
    columns="Bet Type", 
    values="Bet Amount", 
    aggfunc="sum", 
    fill_value=0
).reset_index()

# Check for each bet type column and rename or add if missing:
if "Win" in summary.columns:
    summary = summary.rename(columns={"Win": "Total Bet Win"})
else:
    summary["Total Bet Win"] = 0

if "Place" in summary.columns:
    summary = summary.rename(columns={"Place": "Total Bet Place"})
else:
    summary["Total Bet Place"] = 0

if "Show" in summary.columns:
    summary = summary.rename(columns={"Show": "Total Bet Show"})
else:
    summary["Total Bet Show"] = 0

# Now calculate the payout ratios
summary["Payout Ratio Win"] = summary["Total Bet Win"].apply(lambda x: total_win / x if x > 0 else None)
summary["Payout Ratio Place"] = summary["Total Bet Place"].apply(lambda x: total_place / x if x > 0 else None)
summary["Payout Ratio Show"] = summary["Total Bet Show"].apply(lambda x: total_show / x if x > 0 else None)


st.dataframe(summary)

# 2. Finishing Order Section (Admin Only)
if st.session_state.admin_logged_in:
    st.header("Enter Finishing Order (Admin Only)")
    winner = st.selectbox("Winner (1st)", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia",  "Mike Leonard"], key="winner")
    second = st.selectbox("2nd Place", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia",  "Mike Leonard"], key="second")
    third = st.selectbox("3rd Place", ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", "Pete Sullivan", "Ryan Barcome", "Kunal Kanjolia",  "Mike Leonard"], key="third")
else:
    st.info("Finishing order can only be adjusted by the admin.")
    # Optionally, set default finishing order or leave them unset
    winner = None
    second = None
    third = None



# Section 4: Calculate Eligible Bets & Payout Ratios
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



# Display the summary DataFrame.
st.dataframe(summary_df)

# Section 5: Calculate and Display Individual Payouts
def calculate_payout(row):
    if row["Bet Type"] == "Win" and row["Betting On"] in eligible_win:
        return row["Bet Amount"] * win_ratio
    elif row["Bet Type"] == "Place" and row["Betting On"] in eligible_place:
        return row["Bet Amount"] * place_ratio
    elif row["Bet Type"] == "Show" and row["Betting On"] in eligible_show:
        return row["Bet Amount"] * show_ratio
    else:
        return 0.0

bets_df = st.session_state.bets.copy()
bets_df["Payout"] = bets_df.apply(calculate_payout, axis=1)

st.header("Individual Payouts")
st.markdown("""
Final Payouts once tournament is over (Payout null until tournament is over) 
""")
st.dataframe(bets_df[["Bettor Name", "Betting On", "Bet Type", "Bet Amount", "Payout"]])