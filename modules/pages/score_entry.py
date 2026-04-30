import streamlit as st
from datetime import datetime, timezone
from modules.db import save_game


def render_score_entry(db):
    st.subheader("Gyors eredményrögzítés")
    st.caption("Játék után add meg a végső pontokat és mentsd el.")

    with st.form("quick_entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        p1 = c1.text_input("1. játékos")
        p2 = c2.text_input("2. játékos")
        p3 = c3.text_input("3. játékos")

        st.write("**Végső pontok:**")
        sc1, sc2, sc3 = st.columns(3)
        s1 = sc1.number_input("1. játékos pontja", step=1, value=0, key="qe_s1")
        s2 = sc2.number_input("2. játékos pontja", step=1, value=0, key="qe_s2")
        s3 = sc3.number_input("3. játékos pontja", step=1, value=0, key="qe_s3")

        forint_alap = st.number_input(
            "Alapét (Ft/pont)", min_value=0, value=10, step=5,
            help="0 = csak pontozás"
        )

        submitted = st.form_submit_button("💾 Mentés", type="primary", use_container_width=True)

    if submitted:
        names = [p1.strip(), p2.strip(), p3.strip()]
        if not all(names):
            st.error("Add meg mindhárom játékos nevét!")
            return
        if len(set(n.lower() for n in names)) < 3:
            st.error("A három név nem egyezhet meg!")
            return

        scores = [int(s1), int(s2), int(s3)]

        game_data = {
            "mode": "quick",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "players": names,
            "forint_alap": forint_alap,
            "final_scores": scores,
        }

        doc_id, err = save_game(db, game_data)
        if err:
            st.error(f"Mentési hiba: {err}")
        else:
            st.success("Elmentve!")
            # Elszámolás előnézete
            st.write("**Eredmény:**")
            cols = st.columns(3)
            for i, col in enumerate(cols):
                pts = scores[i]
                ft = pts * forint_alap
                sign_p = "+" if pts > 0 else ""
                sign_f = "+" if ft > 0 else ""
                emoji = "🟢" if pts > 0 else "🔴" if pts < 0 else "⚪"
                col.metric(
                    label=f"{emoji} {names[i]}",
                    value=f"{sign_p}{pts} pont",
                    delta=f"{sign_f}{ft} Ft" if forint_alap > 0 else None,
                )
