import streamlit as st
import pandas as pd
import os

# ======= Persistence Setup =======
BETS_FILE = "bets_data.csv"

def load_bets():
    if os.path.exists(BETS_FILE):
        return pd.read_csv(BETS_FILE)
    else:
        return pd.DataFrame(columns=["Bettor Name","Betting On","Bet Type","Bet Amount"])

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()
else:
    # Refresh from CSV in case of external changes
    st.session_state.bets = load_bets()

# ============ HELPER FUNCTIONS ============
def split_contribution(bet_type, amount):
    """
    Returns a tuple (win_amt, place_amt, show_amt)
    indicating how much of 'amount' goes to each pool.
    """
    if bet_type == "Win":
        # 1/3 each to Win, Place, Show
        return (amount/3.0, amount/3.0, amount/3.0)
    elif bet_type == "Place":
        # 1/2 to Place, 1/2 to Show
        return (0.0, amount/2.0, amount/2.0)
    elif bet_type == "Show":
        # All to Show
        return (0.0, 0.0, amount)
    else:
        return (0.0, 0.0, 0.0)

st.title("2025 Summer Classic (Simplified Each-Way)")

# ============ Admin Login ============
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

def admin_login():
    with st.sidebar:
        st.header("Admin Login")
        pw = st.text_input("Enter admin password", type="password")
        if st.button("Login as Admin"):
            if pw == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Admin access granted.")
            else:
                st.error("Incorrect password.")

admin_login()

if st.session_state.admin_logged_in:
    if st.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.success("Admin logged out.")

# ============ Wagering Lock Toggle ============
if "wagering_locked" not in st.session_state:
    st.session_state.wagering_locked = False

if st.session_state.admin_logged_in:
    if st.button("Toggle Wagering Lock"):
        st.session_state.wagering_locked = not st.session_state.wagering_locked
        if st.session_state.wagering_locked:
            st.success("Wagering is now locked.")
        else:
            st.info("Wagering unlocked.")

if st.session_state.wagering_locked:
    st.warning("Wagering is LOCKED.")
else:
    st.info("Wagering is OPEN.")

# ============ Admin can delete bets ============
if st.session_state.admin_logged_in:
    st.subheader("Admin: Manage Bets")
    if len(st.session_state.bets) > 0:
        to_delete = st.multiselect("Select rows to delete", st.session_state.bets.index)
        if st.button("Delete Selected Bets"):
            if to_delete:
                st.session_state.bets.drop(to_delete, inplace=True)
                st.session_state.bets.reset_index(drop=True, inplace=True)
                st.session_state.bets.to_csv(BETS_FILE, index=False)
                st.success("Bets deleted.")
            else:
                st.error("No bets selected.")
    else:
        st.info("No bets to delete.")

# ============ Bet Form ============
if not st.session_state.wagering_locked:
    with st.form("bet_form", clear_on_submit=True):
        st.subheader("Place a Bet")
        bettor = st.selectbox("Bettor Name", 
            ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
             "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
             "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"])
        horse = st.selectbox("Betting On", 
            ["Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
             "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
             "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"])
        btype = st.selectbox("Bet Type", ["Win","Place","Show"])
        amt = st.number_input("Bet Amount ($)", min_value=1, step=1)
        submit_bet = st.form_submit_button("Submit Bet")
        if submit_bet:
            new_row = pd.DataFrame([[bettor, horse, btype, amt]],
                                   columns=["Bettor Name","Betting On","Bet Type","Bet Amount"])
            st.session_state.bets = pd.concat([st.session_state.bets, new_row], ignore_index=True)
            st.session_state.bets.to_csv(BETS_FILE, index=False)
            st.success(f"Bet placed: {bettor} bets ${amt} on {horse} ({btype})")

# ============ Finishing Order ============
if "finishing_order" not in st.session_state:
    st.session_state.finishing_order = {"winner": None, "second": None, "third": None}

if st.session_state.admin_logged_in:
    st.subheader("Enter Finishing Order")
    horses = ["(None)"] + [
        "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin", 
        "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores", 
        "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
    ]
    w = st.selectbox("1st Place", horses, index=0)
    s = st.selectbox("2nd Place", horses, index=0)
    t = st.selectbox("3rd Place", horses, index=0)
    if st.button("Save Finishing Order"):
        st.session_state.finishing_order = {"winner": None if w=="(None)" else w,
                                            "second": None if s=="(None)" else s,
                                            "third": None if t=="(None)" else t}
        st.success("Finishing order saved.")

winner = st.session_state.finishing_order.get("winner")
second = st.session_state.finishing_order.get("second")
third = st.session_state.finishing_order.get("third")

# ============ Calculate Pools ============
# 1) Build the splitted contributions
bets_df = st.session_state.bets.copy()
bets_df["Win Contrib"] = 0.0
bets_df["Place Contrib"] = 0.0
bets_df["Show Contrib"] = 0.0

for idx, row in bets_df.iterrows():
    w, p, sh = split_contribution(row["Bet Type"], row["Bet Amount"])
    bets_df.at[idx, "Win Contrib"]   = w
    bets_df.at[idx, "Place Contrib"] = p
    bets_df.at[idx, "Show Contrib"]  = sh

win_pool   = bets_df["Win Contrib"].sum()
place_pool = bets_df["Place Contrib"].sum()
show_pool  = bets_df["Show Contrib"].sum()

st.header("Pool Totals")
st.write(f"**Win Pool:** ${win_pool}")
st.write(f"**Place Pool:** ${place_pool}")
st.write(f"**Show Pool:** ${show_pool}")

# 2) Identify which splitted bets are eligible for each pool
#    - Win pool: only bets that had "Win Contrib" on the actual 1st place
#    - Place pool: splitted place from bets on the 1st or 2nd place
#    - Show pool: splitted show from bets on the 1st, 2nd or 3rd place

def is_eligible_for_win(row):
    return (winner is not None 
            and row["Win Contrib"] > 0 
            and row["Betting On"] == winner)

def is_eligible_for_place(row):
    return (row["Place Contrib"] > 0 
            and ( (winner is not None and row["Betting On"]==winner)
                  or (second is not None and row["Betting On"]==second) ))

def is_eligible_for_show(row):
    return (row["Show Contrib"] > 0 
            and ( (winner is not None and row["Betting On"]==winner)
                  or (second is not None and row["Betting On"]==second)
                  or (third is not None  and row["Betting On"]==third) ))

win_eligible_contrib   = bets_df.loc[bets_df.apply(is_eligible_for_win, axis=1),   "Win Contrib"].sum()
place_eligible_contrib = bets_df.loc[bets_df.apply(is_eligible_for_place, axis=1), "Place Contrib"].sum()
show_eligible_contrib  = bets_df.loc[bets_df.apply(is_eligible_for_show, axis=1),  "Show Contrib"].sum()

# 3) If a pool has zero eligible contributions, we redistribute that pool's entire funds
#    to the other pool(s) that do have winners, proportionally to their original pool sizes.
extra = 0.0
win_pool_eff   = win_pool
place_pool_eff = place_pool
show_pool_eff  = show_pool

pools_data = [
    {"name": "Win",   "pool": win_pool,   "eligible": win_eligible_contrib},
    {"name": "Place", "pool": place_pool, "eligible": place_eligible_contrib},
    {"name": "Show",  "pool": show_pool,  "eligible": show_eligible_contrib},
]

no_winners = [p for p in pools_data if p["eligible"]==0 and p["pool"]>0]
yes_winners= [p for p in pools_data if p["eligible"]>0]

extra_funds = sum([p["pool"] for p in no_winners])
sum_winner_pools = sum([p["pool"] for p in yes_winners])

def find_pool_struct(name):
    if name=="Win":
        return win_pool_eff
    elif name=="Place":
        return place_pool_eff
    else:
        return show_pool_eff

if extra_funds>0 and sum_winner_pools>0:
    # Redistribute proportionally
    for p in yes_winners:
        share = p["pool"]/sum_winner_pools
        addition = extra_funds*share
        if p["name"]=="Win":
            win_pool_eff += addition
        elif p["name"]=="Place":
            place_pool_eff += addition
        elif p["name"]=="Show":
            show_pool_eff += addition
    # Zero out the pools that had no winners
    for p in no_winners:
        if p["name"]=="Win":
            win_pool_eff=0
        elif p["name"]=="Place":
            place_pool_eff=0
        elif p["name"]=="Show":
            show_pool_eff=0

st.write(f"**Effective Win Pool (post-redistribution):** ${win_pool_eff:.2f}")
st.write(f"**Effective Place Pool (post-redistribution):** ${place_pool_eff:.2f}")
st.write(f"**Effective Show Pool (post-redistribution):** ${show_pool_eff:.2f}")

# 4) Calculate each splitted portion's share
#   - For each splitted bet that is eligible for the Win pool, the ratio is (win_pool_eff / sum_of_eligible_win_contrib).
#   - Similarly for place and show.
win_ratio   =  (win_pool_eff / win_eligible_contrib)   if win_eligible_contrib>0   else 0.0
place_ratio =  (place_pool_eff / place_eligible_contrib) if place_eligible_contrib>0 else 0.0
show_ratio  =  (show_pool_eff / show_eligible_contrib)  if show_eligible_contrib>0  else 0.0

st.write("**Final Win Ratio:**", win_ratio)
st.write("**Final Place Ratio:**", place_ratio)
st.write("**Final Show Ratio:**", show_ratio)

# 5) Final Payout calculation for each splitted portion
def splitted_payout(row):
    # By default, 0
    payout = 0.0
    # Win portion
    if is_eligible_for_win(row):
        payout += row["Win Contrib"]*win_ratio
    # Place portion
    if is_eligible_for_place(row):
        payout += row["Place Contrib"]*place_ratio
    # Show portion
    if is_eligible_for_show(row):
        payout += row["Show Contrib"]*show_ratio
    return payout

bets_df["Payout"] = bets_df.apply(splitted_payout, axis=1)

# Filter out those with 0 payout if you prefer
final_df = bets_df[bets_df["Payout"]>0].copy()
st.header("Individual Payouts")
st.markdown("Below are only the bets that paid out (nonzero).")
st.dataframe(final_df[["Bettor Name","Betting On","Bet Type","Bet Amount","Win Contrib","Place Contrib","Show Contrib","Payout"]])

total_pool_amt = st.session_state.bets["Bet Amount"].sum()
total_payouts = final_df["Payout"].sum()
st.write(f"**Total Wagered:** ${total_pool_amt:.2f}")
st.write(f"**Total Paid Out:** ${total_payouts:.2f}")