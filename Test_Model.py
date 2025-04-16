import streamlit as st
import pandas as pd
import pymysql
import os
from datetime import datetime, timezone

########################################
# MySQL Persistence Setup
########################################
MYSQL_HOST     = "sql5.freesqldatabase.com"
MYSQL_PORT     = 3306
MYSQL_DB       = "sql5773659"
MYSQL_USER     = "sql5773659"
MYSQL_PASSWORD = "3q2JtXGhXL"

def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        port=MYSQL_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    conn = get_connection()
    with conn.cursor() as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bettor_name VARCHAR(255),
                betting_on   VARCHAR(255),
                bet_type     VARCHAR(50),
                bet_amount   DECIMAL(10,2)
            )
        ''')
    conn.commit()
    conn.close()

def load_bets_from_db():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
          id,
          bettor_name AS `Bettor Name`,
          betting_on   AS `Betting On`,
          bet_type     AS `Bet Type`,
          bet_amount   AS `Bet Amount`
        FROM bets
        """,
        conn
    )
    conn.close()
    # ───── FIX #1 ──────────────────────────────────────────────────────────────
    # ensure that "Bet Amount" is actually a float, never a str
    df["Bet Amount"] = pd.to_numeric(df["Bet Amount"], errors="coerce").fillna(0.0)
    # ────────────────────────────────────────────────────────────────────────────
        # ───── FIX #1.5 ────────────────────────────────────────────────
    # Drop any rows where all cell values match the column names (erroneous header rows)
    header_mask = df.eq(df.columns, axis=1).all(axis=1)
    if header_mask.any():
        df = df.loc[~header_mask]
    # ────────────────────────────────────────────────────────────────
    return df

def insert_bet(bettor_name, betting_on, bet_type, bet_amount):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute('''
            INSERT INTO bets (bettor_name, betting_on, bet_type, bet_amount)
            VALUES (%s, %s, %s, %s)
        ''', (bettor_name, betting_on, bet_type, bet_amount))
    conn.commit()
    conn.close()

def delete_bets(ids):
    conn = get_connection()
    with conn.cursor() as c:
        c.executemany('DELETE FROM bets WHERE id=%s', [(i,) for i in ids])
    conn.commit()
    conn.close()

def delete_all_bets():
    conn = get_connection()
    with conn.cursor() as c:
        c.execute('DELETE FROM bets')
    conn.commit()
    conn.close()

# Initialize DB once
init_db()

########################################
# Session State Setup: single load
########################################
st.session_state["bets"] = load_bets_from_db()

# Initialize other keys
for key in ["current_user", "admin_logged_in", "wagering_closed", "finishing_order"]:
    if key not in st.session_state:
        st.session_state[key] = None if key in ["current_user", "finishing_order"] else False

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
st.session_state.current_user = user_choice if user_choice != "Select a name..." else None

if st.session_state.current_user:
    st.write(f"**Current user:** {st.session_state.current_user}")
else:
    st.warning("Please select your name to place bets.")

########################################
# Helper Functions: Each‑Way Processing
########################################
def effective_contribution(bet_type, amount, pool_category):
    if bet_type == "Win":
        return amount / 3.0
    elif bet_type == "Place":
        return amount / 2.0 if pool_category in ["Place", "Show"] else 0
    elif bet_type == "Show":
        return amount if pool_category == "Show" else 0
    return 0

def eligible_for_pool(row, pool, finishing_order):
    if not finishing_order:
        return False
    win_horse, second_horse, third_horse = (
        finishing_order["winner"],
        finishing_order["second"],
        finishing_order["third"],
    )
    bt, outcome = row["Bet Type"], row["Betting On"]
    if pool == "win":
        return outcome == win_horse and bt == "Win"
    elif pool == "place":
        if outcome == win_horse:
            return bt in ["Win", "Place"]
        if outcome == second_horse:
            return bt == "Place"
        return False
    else:  # show
        if outcome == win_horse:
            return True
        if outcome == second_horse:
            return bt in ["Win", "Place", "Show"]
        if outcome == third_horse:
            return bt == "Show"
        return False

########################################
# Admin Login (Sidebar)
########################################
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")
def admin_login():
    with st.sidebar:
        st.header("Admin Login")
        pw = st.text_input("Enter admin password", type="password")
        if st.button("Login as Admin"):
            if pw == ADMIN_PASSWORD:
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
# Wagering Lock Toggle (Admin Only)
########################################
if st.session_state.admin_logged_in and st.button("Toggle Wagering Lock"):
    st.session_state.wagering_closed = not st.session_state.wagering_closed

# ─── replaced one‑liner with normal if/else ─────────────────────────────────
if st.session_state.wagering_closed:
    st.warning("Betting is closed; no new bets accepted.")
else:
    st.info("Wagering is OPEN.")
# ────────────────────────────────────────────────────────────────────────────

########################################
# Admin View: All Wagers
########################################
if st.session_state.admin_logged_in:
    st.subheader("All Wagers (Admin View)")
    st.dataframe(st.session_state.bets)

    if st.button("Refresh Bets"):
        st.session_state.bets = load_bets_from_db()
        st.success("Refreshed.")

    st.subheader("Admin: Delete Bets")
    if not st.session_state.bets.empty:
        bet_ids = st.session_state.bets["id"].tolist()
        to_del  = st.multiselect("Select wager IDs to delete", bet_ids)
        if st.button("Delete Selected Bets"):
            delete_bets(to_del)
            st.session_state.bets = load_bets_from_db()
            st.success("Deleted.")
    else:
        st.info("No wagers to delete.")

    st.markdown("---")
    st.subheader("Admin: Delete All Bets")
    if st.button("Delete ALL Bets"):
        delete_all_bets()
        st.session_state.bets = load_bets_from_db()
        st.success("All wiped.")

########################################
# Public Bet Form
########################################
if not st.session_state.wagering_closed and st.session_state.current_user:
    with st.form("bet_form", clear_on_submit=True):
        st.write(f"**Bettor Name:** {st.session_state.current_user}")
        horse = st.selectbox("Betting On", all_names[1:])
        btype = st.selectbox("Bet Type", ["Win", "Place", "Show"])
        amt   = st.number_input("Bet Amount ($)", min_value=1.0, step=1.0)
        if st.form_submit_button("Submit Bet"):
            insert_bet(st.session_state.current_user, horse, btype, amt)
            st.session_state.bets = load_bets_from_db()
            st.success(f"{st.session_state.current_user} bet ${amt} on {horse} ({btype})")
else:
    if not st.session_state.current_user:
        st.error("Select your name first.")
    else:
        st.error("Wagering is currently locked.")

########################################
# Pool Calculations & Detailed Summary
########################################
if not st.session_state.bets.empty:
    st.header("Total Pool Size")
    total_pool  = st.session_state.bets["Bet Amount"].sum()
    total_win   = st.session_state.bets.query("`Bet Type`=='Win'")["Bet Amount"].sum()
    total_place = st.session_state.bets.query("`Bet Type`=='Place'")["Bet Amount"].sum()
    total_show  = st.session_state.bets.query("`Bet Type`=='Show'")["Bet Amount"].sum()

    st.write(f"**Total Pool:** ${total_pool:.2f}")
    st.write(f"**Win Pool:** ${total_win:.2f}")
    st.write(f"**Place Pool:** ${total_place:.2f}")
    st.write(f"**Show Pool:** ${total_show:.2f}")

    # Compute effective contributions for each bet.
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
    
        # Eligibility masks for each pool.
        win_mask = (df["Betting On"] == winner) & (df["Bet Type"] == "Win")
        place_mask = df.apply(lambda r: (r["Betting On"] == winner and r["Bet Type"] in ["Win", "Place"]) or 
                                        (r["Betting On"] == second and r["Bet Type"] == "Place"), axis=1)
        show_mask = df.apply(lambda r: (r["Betting On"] == winner) or 
                                       (r["Betting On"] == second and r["Bet Type"] in ["Win", "Place", "Show"]) or 
                                       (r["Betting On"] == third and r["Bet Type"] == "Show"), axis=1)
    
        eligible_win_total = df.loc[win_mask, "Win Contrib"].sum()
        eligible_place_total = df.loc[place_mask, "Place Contrib"].sum()
        eligible_show_total = df.loc[show_mask, "Show Contrib"].sum()
    
        raw_win_ratio = (total_win / eligible_win_total) if eligible_win_total > 0 else 0
        raw_place_ratio = (total_place / eligible_place_total) if eligible_place_total > 0 else 0
        raw_show_ratio = (total_show / eligible_show_total) if eligible_show_total > 0 else 0
    
        # Compute pool payouts ensuring 100% distribution.
        def compute_pool_payout(df, pool, pool_total, eligible_mask, contrib_col):
            if df.loc[eligible_mask].empty:
                # Fallback: use all bets for this pool type.
                eligible_mask = df["Bet Type"] == pool.capitalize()
            total_eff = df.loc[eligible_mask, contrib_col].sum()
            if total_eff > 0:
                ratio = pool_total / total_eff
                df.loc[eligible_mask, pool + "_payout_raw"] = df.loc[eligible_mask, contrib_col] * ratio
            else:
                total_fb = df.loc[df["Bet Type"] == pool.capitalize(), "Bet Amount"].sum()
                ratio = pool_total / total_fb if total_fb > 0 else 0
                df.loc[df["Bet Type"] == pool.capitalize(), pool + "_payout_raw"] = df.loc[df["Bet Type"] == pool.capitalize(), "Bet Amount"] * ratio
            
            # Calculate remainder.
            raw_total = df[pool + "_payout_raw"].sum()
            remainder = pool_total - raw_total
            if total_eff > 0:
                df.loc[eligible_mask, pool + "_payout_extra"] = (df.loc[eligible_mask, contrib_col] / total_eff) * remainder
            else:
                df[pool + "_payout_extra"] = 0
            df[pool + "_payout_final"] = df[pool + "_payout_raw"].fillna(0) + df[pool + "_payout_extra"].fillna(0)
            # Final scaling to ensure total equals pool_total.
            final_sum = df[pool + "_payout_final"].sum()
            if final_sum != 0:
                scale = pool_total / final_sum
            else:
                scale = 1
            df[pool + "_payout_final"] = df[pool + "_payout_final"] * scale
            return df
        
        df = compute_pool_payout(df, "win", total_win, win_mask, "Win Contrib")
        df = compute_pool_payout(df, "place", total_place, place_mask, "Place Contrib")
        df = compute_pool_payout(df, "show", total_show, show_mask, "Show Contrib")
    
        df["Final Payout"] = df["win_payout_final"] + df["place_payout_final"] + df["show_payout_final"]
    
        final_df = df[df["Final Payout"] > 0].copy()
    
        st.header("Individual Payouts (Final)")
        st.markdown("Breakdown per wager (only showing wagers with a positive final payout):")
        st.dataframe(final_df[[
            "Bettor Name", "Betting On", "Bet Type", "Bet Amount",
            "Win Contrib", "Place Contrib", "Show Contrib",
            "win_payout_raw", "place_payout_raw", "show_payout_raw",
            "win_payout_extra", "place_payout_extra", "show_payout_extra",
            "Final Payout"
        ]])
    
        st.write(f"**Total Wagered:** ${total_pool:.2f}")
        tot_paid = final_df["Final Payout"].sum()
        st.write(f"**Total Paid Out:** ${tot_paid:.2f}")
    else:
        st.write("No finishing order set by the admin.")
else:
    st.write("No bets placed yet.")