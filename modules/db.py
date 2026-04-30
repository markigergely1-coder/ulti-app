import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import os
import json

CREDENTIALS_FILE = "firebase_credentials.json"
COLLECTION = "ulti_games"


def _parse_private_key(creds_dict):
    if "private_key" in creds_dict:
        pk = creds_dict["private_key"].strip().strip('"').strip("'")
        if "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        creds_dict["private_key"] = pk
    return creds_dict


@st.cache_resource(ttl=3600)
def get_firestore_db():
    try:
        if hasattr(st, "secrets") and "google_creds" in st.secrets:
            creds_dict = _parse_private_key(dict(st.secrets["google_creds"]))
            creds = service_account.Credentials.from_service_account_info(creds_dict)
            return firestore.Client(credentials=creds, project=creds_dict.get("project_id"))
        elif os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, "r") as f:
                creds_dict = json.load(f)
            return firestore.Client.from_service_account_json(CREDENTIALS_FILE)
    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
    return None


def save_game(db, game_data):
    if db is None:
        return None, "Nincs Firestore kapcsolat – ellenőrizd a secrets.toml fájlt."
    try:
        doc_ref = db.collection(COLLECTION).document()
        doc_ref.set(game_data)
        return doc_ref.id, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=60)
def get_games(_db, limit=100):
    if _db is None:
        return []
    try:
        docs = (
            _db.collection(COLLECTION)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        games = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            games.append(d)
        return games
    except Exception as e:
        st.error(f"Hiba az adatok betöltésekor: {e}")
        return []


def delete_game(db, game_id):
    if db is None:
        return False, "Nincs Firestore kapcsolat."
    try:
        db.collection(COLLECTION).document(game_id).delete()
        st.cache_data.clear()
        return True, None
    except Exception as e:
        return False, str(e)
