import streamlit as st
import pandas as pd
import pymysql
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine
engine = create_engine("mysql+pymysql://sql5773659:3q2JtXGhXL@sql5.freesqldatabase.com:3306/sql5773659")

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
    df = pd.read_sql_query(
        """
        SELECT
          id,
          bettor_name   AS `Bettor Name`,
          betting_on     AS `Betting On`,
          bet_type       AS `Bet Type`,
          bet_amount     AS `Bet Amount`
        FROM bets
        """,
        engine
    )

    # Drop any row where the DB just echoed your CSV header back as data:
    df = df[df["Bettor Name"]   != "Bettor Name"]
    df = df[df["Betting On"]     != "Betting On"]
    df = df[df["Bet Type"]       != "Bet Type"]
    df = df[df["Bet Amount"].astype(str) != "Bet Amount"]

    # make sure Bet Amount really is numeric
    df["Bet Amount"] = pd.to_numeric(df["Bet Amount"], errors="coerce").fillna(0)

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
# Only load from the DB if we haven't already in this session
if "bets" not in st.session_state:
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
        horse = st.selectbox("Betting On", all_names[1:], key="betting_on")
        btype = st.selectbox("Bet Type", ["Win", "Place", "Show"], key="bet_type")
        amt   = st.number_input("Bet Amount ($)", min_value=1.0, step=1.0, key="bet_amount")
        submitted = st.form_submit_button("Submit Bet")
        if submitted:
            insert_bet(st.session_state.current_user, horse, btype, amt)
            st.session_state.bets = load_bets_from_db()
            st.success(f"{st.session_state.current_user} bet ${amt:.2f} on {horse} ({btype})")
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
    
    def create_summary(df):
        summary = df.pivot_table(
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
        
    summary_df = create_summary(df)
    st.dataframe(summary_df)
    
    ########################################
    # Finishing Order & Final Payout Calculation
    ########################################
    finishing_opts = [
        "Anthony Sousa", "Connor Donovan", "Chris Brown", "Jared Joaquin",
        "Jim Alexander", "Joe Canavan", "Mark Leonard", "Pete Koskores",
        "Pete Sullivan", "Kunal Kanjolia", "Mike Leonard", "Ryan Barcome"
    ]
    if st.session_state.admin_logged_in:
        st.header("Enter Finishing Order (Admin Only)")
        finish_order = {
            "winner": st.selectbox("Winner (1st)", finishing_opts, key="winner_select"),
            "second": st.selectbox("2nd Place", finishing_opts, key="second_select"),
            "third": st.selectbox("3rd Place", finishing_opts, key="third_select"),
        }
        st.session_state.finishing_order = finish_order
    else:
        st.info("Only admins can adjust finishing order.")
        finish_order = st.session_state.finishing_order

    if finish_order:
        winner = finish_order["winner"]
        second = finish_order["second"]
        third = finish_order["third"]

        # Eligibility masks
        win_mask = (df["Betting On"] == winner) & (df["Bet Type"] == "Win")
        place_mask = df.apply(
            lambda r: (r["Betting On"] == winner and r["Bet Type"] in ["Win", "Place"]) or
                      (r["Betting On"] == second and r["Bet Type"] == "Place"),
            axis=1
        )
        show_mask = df.apply(
            lambda r: (r["Betting On"] == winner) or
                      (r["Betting On"] == second and r["Bet Type"] in ["Win", "Place", "Show"]) or
                      (r["Betting On"] == third and r["Bet Type"] == "Show"),
            axis=1
        )

        # Totals & raw ratios
        eligible_win = df.loc[win_mask,   "Win Contrib"].sum()
        eligible_place = df.loc[place_mask, "Place Contrib"].sum()
        eligible_show = df.loc[show_mask,  "Show Contrib"].sum()
        raw_win_ratio   = (total_win   / eligible_win)   if eligible_win   > 0 else 0
        raw_place_ratio = (total_place / eligible_place) if eligible_place > 0 else 0
        raw_show_ratio  = (total_show  / eligible_show)  if eligible_show  > 0 else 0

        # Compute each pool’s payouts (raw, extra, final)
        def pool_payout(df, pool, pool_total, mask, contrib):
            df[f"{pool}_raw"] = df.apply(
                lambda r: r[contrib] * {"win": raw_win_ratio, "place": raw_place_ratio, "show": raw_show_ratio}[pool]
                if mask.loc[r.name] else 0,
                axis=1
            )
            claimed = df[f"{pool}_raw"].sum()
            unclaimed = pool_total - claimed

            # extra: split unclaimed among eligible who got zero raw
            extra_mask = mask & df[f"{pool}_raw"].eq(0)
            total_amt = df.loc[extra_mask, "Bet Amount"].sum()
            df[f"{pool}_extra"] = df.apply(
                lambda r: (r["Bet Amount"] / total_amt * unclaimed) if extra_mask.loc[r.name] and total_amt>0 else 0,
                axis=1
            )

            df[f"{pool}_final"] = df[f"{pool}_raw"] + df[f"{pool}_extra"]
            # scale to exactly pool_total
            s = df[f"{pool}_final"].sum()
            if s>0:
                df[f"{pool}_final"] *= (pool_total / s)
            return df

        df = pool_payout(df, "win",   tw_eff,   win_mask,   "Win Contrib")
        df = pool_payout(df, "place", tp_eff, place_mask, "Place Contrib")
        df = pool_payout(df, "show",  ts_eff,  show_mask,  "Show Contrib")

        # Final aggregation & display
        df["Final Payout"] = df["win_final"] + df["place_final"] + df["show_final"]
        final_df = df[df["Final Payout"]>0].copy()

        st.header("Individual Payouts (Final)")
        st.dataframe(final_df[[
            "Bettor Name","Betting On","Bet Type","Bet Amount",
            "win_raw","place_raw","show_raw",
            "win_extra","place_extra","show_extra",
            "Final Payout"
        ]])
        st.write(f"**Total Wagered:** ${total_pool:.2f}")
        st.write(f"**Total Paid Out:** ${final_df['Final Payout'].sum():.2f}")

    else:
        st.write("No finishing order set by the admin.")
else:
    st.write("No bets placed yet.")
