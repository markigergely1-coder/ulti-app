import streamlit as st
from modules.db import get_games, delete_game


def _fmt_score(players, scores, forint_alap):
    parts = []
    for i, name in enumerate(players):
        pts = scores[i] if i < len(scores) else 0
        sign = "+" if pts > 0 else ""
        ft = pts * forint_alap
        ft_sign = "+" if ft > 0 else ""
        ft_str = f" ({ft_sign}{ft} Ft)" if forint_alap > 0 else ""
        parts.append(f"{name}: **{sign}{pts}**{ft_str}")
    return "  |  ".join(parts)


def render_history(db):
    st.subheader("Előzmények")

    if st.button("🔄 Frissítés", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    games = get_games(db)

    if not games:
        st.info("Még nincs mentett játék." if db else "⚠️ Nincs Firebase kapcsolat – ellenőrizd a secrets.toml fájlt.")
        return

    st.caption(f"{len(games)} mentett játék")

    for game in games:
        players = game.get("players", [])
        scores = game.get("final_scores", [])
        forint_alap = game.get("forint_alap", 0)
        mode = game.get("mode", "?")
        created = game.get("created_at", "")
        game_id = game.get("id", "")
        rounds = game.get("rounds", [])

        # Dátum formázás
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y.%m.%d %H:%M")
        except Exception:
            date_str = created[:16] if created else "?"

        mode_emoji = "🎮" if mode == "game" else "📝"
        header = f"{mode_emoji} {date_str}  —  {', '.join(players)}"

        with st.expander(header):
            # Végeredmény
            st.write("**Végeredmény:**")
            cols = st.columns(3)
            for i, col in enumerate(cols):
                if i < len(players) and i < len(scores):
                    pts = scores[i]
                    ft = pts * forint_alap
                    sign_p = "+" if pts > 0 else ""
                    sign_f = "+" if ft > 0 else ""
                    emoji = "🟢" if pts > 0 else "🔴" if pts < 0 else "⚪"
                    col.metric(
                        label=f"{emoji} {players[i]}",
                        value=f"{sign_p}{pts} pont",
                        delta=f"{sign_f}{ft} Ft" if forint_alap > 0 else None,
                    )

            # Körök (csak játék módnál)
            if mode == "game" and rounds:
                st.write(f"**Körök ({len(rounds)}):**")
                for j, r in enumerate(rounds, 1):
                    kontra_suffix = f" [{r.get('kontra_label', '')}]" if r.get("kontra", 1) > 1 else ""
                    pts = r.get("points", [])
                    if isinstance(pts, dict):
                        pts_list = [pts.get(i, pts.get(str(i), 0)) for i in range(3)]
                    else:
                        pts_list = pts

                    pts_str = "  ".join(
                        f"{players[i]}: {'+' if pts_list[i]>0 else ''}{pts_list[i]}"
                        for i in range(len(players))
                        if i < len(pts_list)
                    )
                    st.caption(f"{j}. {r.get('szolista_name','?')} – {r.get('bid','?')}{kontra_suffix} → {pts_str}")

            st.write(f"Alapét: {forint_alap} Ft/pont  |  Mód: {'Játék' if mode=='game' else 'Gyors'}")

            # Törlés
            if st.button(f"🗑️ Törlés", key=f"del_{game_id}"):
                ok, err = delete_game(db, game_id)
                if ok:
                    st.success("Törölve.")
                    st.rerun()
                else:
                    st.error(f"Törlési hiba: {err}")
