import firebase_admin
from firebase_admin import credentials, initialize_app, firestore, storage, db, auth

if not firebase_admin._apps:
    cred = credentials.Certificate("./workspace.json")
    app = initialize_app(cred, {
        'databaseURL': 'https://admin-con-3a498-default-rtdb.firebaseio.com/',
        'storageBucket': 'admin-con-3a498.appspot.com'
    })
    fs_db = firestore.client()