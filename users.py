from consulta import add_user as add_user_to_db
import sqlite3
# users = {}

def get_user(email):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None




def add_user(email, name, hashed_password):
    # Primeiro adiciona ao banco de dados
    success, message = add_user_to_db(email, name, hashed_password)
    
    # if success:
    #     # Se deu certo, salva também em memória (opcional)
    #     users[email] = {
    #         'name': name,
    #         'password': hashed_password,
    #         'email': email,
    #         'avatar': f'https://i.pravatar.cc/150?u={email}'
    #     }
    
    return success, message
