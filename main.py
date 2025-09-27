import os
import sqlite3
import threading
import asyncio
import secrets
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
from discord import Intents
from discord.ext import commands

# ---------------- Configurações ----------------
DISCORD_BOT_TOKEN = "MTI3MjM3OTY1NjkyNTg3MjI3MA.G_dqeA.GiG5c7dudhAdE00GEQVuFyUcpojPkiC-0Kv_OE"
GUILD_ID = 1397337439407964360  # ID do seu servidor
FLASK_SECRET = secrets.token_urlsafe(16)
MASTER_USER = 'mestre'
MASTER_PASS = 'goncalves@445'
DB_FILE = 'app.db'

# ---------------- Flask ----------------
app = Flask(__name__)
app.secret_key = FLASK_SECRET

# ---------------- CSS ----------------
CSS = """
<style>
body { background-color: black; color: #00ff99; font-family: 'Courier New', monospace; text-align: center; }
h1, h2 { color: #00ff99; text-shadow: 0 0 10px #00ff99; }
a, button { background: black; color: #00ff99; border: 1px solid #00ff99; padding: 6px 12px; margin: 2px; text-decoration: none; display: inline-block; transition: 0.3s; cursor: pointer; }
a:hover, button:hover { background: #00ff99; color: black; }
table { margin: auto; border-collapse: collapse; width: 90%; }
th, td { border: 1px solid #00ff99; padding: 8px; }
tr:hover { background: #002b22; }
input { padding: 6px; margin: 4px; border: 1px solid #00ff99; background: black; color: #00ff99; }
.flash { color: #ffcc00; }
.modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; overflow:auto; background-color: rgba(0,0,0,0.8); }
.modal-content { background-color: black; margin: 15% auto; padding: 20px; border: 1px solid #00ff99; width: 50%; color: #00ff99; }
.modal-content button { margin-top:10px; }
</style>
"""

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        token TEXT UNIQUE,
        discord_id TEXT,
        count INTEGER DEFAULT 0
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS recruited (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT UNIQUE,
        username TEXT,
        avatar_url TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Discord Bot ----------------
intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot_ready = threading.Event()
member_cache = {}

@bot.event
async def on_ready():
    print(f"Discord bot conectado como {bot.user}")
    if GUILD_ID:
        guild = bot.get_guild(GUILD_ID)
        if guild:
            async for m in guild.fetch_members(limit=None):
                member_cache[str(m.id)] = {'id': str(m.id), 'name': m.display_name, 'avatar_url': str(m.display_avatar.url) if m.display_avatar else ''}
    bot_ready.set()

async def send_dm_async(discord_id: str, message: str):
    try:
        user = await bot.fetch_user(int(discord_id))
        await user.send(message)
        return True
    except Exception as e:
        print(f"Erro ao enviar DM para {discord_id}: {e}")
        return False

def start_bot():
    if not DISCORD_BOT_TOKEN or 'COLE_SEU_TOKEN' in DISCORD_BOT_TOKEN:
        print('Token não configurado corretamente.')
        return
    bot.run(DISCORD_BOT_TOKEN)

threading.Thread(target=start_bot, daemon=True).start()

# ---------------- Templates ----------------
login_template = CSS + '''
<h2>Login Mestre</h2>
<form method="post">
<label>Usuário: <input name="username"></label><br>
<label>Senha: <input type="password" name="password"></label><br>
<input type="submit" value="Entrar">
</form>
<p>{{ message }}</p>
'''

master_dashboard_template = CSS + '''
<h2>Bem-vindo, Mestre</h2>
<p><a href="{{ url_for('create_admin') }}">Criar administrador (gera token e envia DM)</a></p>
<p><a href="{{ url_for('view_admins') }}">Ver administradores</a></p>
<p><a href="{{ url_for('recruitment') }}">Ir para Recrutamento</a></p>
<p><a href="{{ url_for('master_logout') }}">Logout</a></p>
'''

create_admin_template = CSS + '''
<h2>Criar administrador</h2>
<form method="post">
<label>Nome do admin: <input name="username" required></label><br>
<label>Discord ID do admin: <input name="discord_id" required></label><br>
<input type="submit" value="Gerar e Enviar Token">
</form>
<p>{{ message }}</p>
<p><a href="{{ url_for('master_dashboard') }}">Voltar</a></p>
'''

view_admins_template = CSS + '''
<h2>Administradores</h2>
<ul>
{% for a in admins %}
<li>{{ a[1] }} — Discord: {{ a[3] }} — Token: {{ a[2] }} — Recrutamentos: {{ a[4] }}</li>
{% endfor %}
</ul>
<p><a href="{{ url_for('master_dashboard') }}">Voltar</a></p>
'''

admin_dashboard_template = CSS + '''
<div id="modal" class="modal">
  <div class="modal-content">
    <p>Você é responsável por organizar a lista corretamente e colocar a quantidade certa de pessoas. Não faça recrutamentos indevidos.</p>
    <button onclick="document.getElementById('modal').style.display='none'">OK</button>
  </div>
</div>

<h2>Bem-vindo, Admin {{ username }}</h2>
<p>Recrutamentos até agora: <strong>{{ count }}</strong></p>
<p><a href="{{ url_for('recruitment') }}">Ir para Recrutamento</a></p>
<p><a href="{{ url_for('admin_logout') }}">Logout</a></p>
<script>document.getElementById('modal').style.display='block';</script>
'''

recruitment_template = CSS + '''
<h2>Recrutamento</h2>
<table border="1">
<tr><th>Avatar</th><th>Nome</th><th>Ações</th></tr>
{% for m in members %}
<tr>
<td>{% if m.avatar_url %}<img src="{{ m.avatar_url }}" width=50 height=50>{% endif %}</td>
<td>{{ m.name }}<br>ID: {{ m.id }}</td>
<td>
<form method="post" action="{{ url_for('add_recruited') }}" style="display:inline">
<input type="hidden" name="discord_id" value="{{ m.id }}">
<input type="hidden" name="username" value="{{ m.name }}">
<input type="hidden" name="avatar_url" value="{{ m.avatar_url }}">
<input type="submit" value="Adicionar">
</form>
<form method="post" action="{{ url_for('remove_recruited') }}" style="display:inline">
<input type="hidden" name="discord_id" value="{{ m.id }}">
<input type="submit" value="Remover">
</form>
<form method="post" action="{{ url_for('send_result') }}" style="display:inline">
<input type="hidden" name="discord_id" value="{{ m.id }}">
<input type="text" name="message" placeholder="Mensagem ao usuário (opcional)" required>
<input type="submit" value="Enviar Resultado">
</form>
</td>
</tr>
{% endfor %}
</table>
<ul>
{% for r in recruited %}<li>{{ r[2] }} ({{ r[1] }})</li>{% endfor %}
</ul>
{% with messages = get_flashed_messages() %}{% if messages %}<ul class="flash">{% for m in messages %}<li>{{ m }}</li>{% endfor %}</ul>{% endif %}{% endwith %}
<p><a href="{{ url_for('index') }}">Início</a></p>
'''

# ---------------- Routes ----------------
@app.route('/')
def index():
    return CSS + '<h2>Site de Recrutamento</h2><p><a href="/master/login">Login Mestre</a> | <a href="/admin/login">Login Admin</a> | <a href="/recruitment">Recrutamento</a></p>'

# Mestre login
@app.route('/master/login', methods=['GET','POST'])
def master_login():
    message=''
    if request.method=='POST':
        if request.form['username']==MASTER_USER and request.form['password']==MASTER_PASS:
            session['master']=True
            return redirect(url_for('master_dashboard'))
        else:
            message='Credenciais inválidas.'
    return render_template_string(login_template, message=message)

@app.route('/master/dashboard')
def master_dashboard():
    if not session.get('master'): return redirect(url_for('master_login'))
    return render_template_string(master_dashboard_template)

@app.route('/master/logout')
def master_logout():
    session.pop('master',None)
    return redirect(url_for('index'))

@app.route('/master/create_admin', methods=['GET','POST'])
def create_admin():
    if not session.get('master'): return redirect(url_for('master_login'))
    message=''
    if request.method=='POST':
        username = request.form['username']
        discord_id = request.form['discord_id']
        token = secrets.token_urlsafe(12)
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO admins (username, token, discord_id) VALUES (?, ?, ?)', (username, token, discord_id))
            conn.commit()
            message=f'Token gerado: {token} (tentando enviar por DM)'
            if bot_ready.is_set():
                asyncio.run_coroutine_threadsafe(send_dm_async(discord_id, f'Você foi adicionado como admin. Token: {token}'), bot.loop)
        except Exception as e:
            message=f'Erro ao criar admin: {e}'
        finally:
            conn.close()
    return render_template_string(create_admin_template, message=message)

@app.route('/master/admins')
def view_admins():
    if not session.get('master'): return redirect(url_for('master_login'))
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT * FROM admins')
    admins = cur.fetchall()
    conn.close()
    return render_template_string(view_admins_template, admins=admins)

# Admin login/logout
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    message=''
    if request.method=='POST':
        token = request.form['token']
        conn=sqlite3.connect(DB_FILE)
        cur=conn.cursor()
        cur.execute('SELECT username, discord_id, count FROM admins WHERE token=?',(token,))
        row=cur.fetchone()
        conn.close()
        if row:
            session['admin']=True
            session['admin_user']=row[0]
            session['admin_discord_id']=row[1]
            session['admin_count']=row[2]
            return redirect(url_for('admin_dashboard'))
        else:
            message='Token inválido.'
    return render_template_string(login_template.replace('Login Mestre','Login Admin'), message=message)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    conn=sqlite3.connect(DB_FILE)
    cur=conn.cursor()
    cur.execute('SELECT count FROM admins WHERE username=?',(session.get('admin_user'),))
    row=cur.fetchone()
    count=row[0] if row else 0
    conn.close()
    return render_template_string(admin_dashboard_template, username=session.get('admin_user'), count=count)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

# Recruitment actions
@app.route('/recruitment')
def recruitment():
    members=list(member_cache.values())
    conn=sqlite3.connect(DB_FILE)
    cur=conn.cursor()
    cur.execute('SELECT * FROM recruited')
    recruited=cur.fetchall()
    conn.close()
    return render_template_string(recruitment_template, members=members, recruited=recruited)

@app.route('/add_recruited', methods=['POST'])
def add_recruited():
    discord_id=request.form['discord_id']
    username=request.form['username']
    avatar_url=request.form['avatar_url']
    conn=sqlite3.connect(DB_FILE)
    cur=conn.cursor()
    cur.execute('INSERT OR IGNORE INTO recruited (discord_id, username, avatar_url) VALUES (?,?,?)',(discord_id,username,avatar_url))
    if session.get('admin'):
        cur.execute('UPDATE admins SET count=count+1 WHERE username=?',(session.get('admin_user'),))
    conn.commit(); conn.close()
    return redirect(url_for('recruitment'))

@app.route('/remove_recruited', methods=['POST'])
def remove_recruited():
    discord_id=request.form['discord_id']
    conn=sqlite3.connect(DB_FILE)
    cur=conn.cursor()
    cur.execute('DELETE FROM recruited WHERE discord_id=?',(discord_id,))
    if session.get('admin'):
        cur.execute('SELECT count FROM admins WHERE username=?',(session.get('admin_user'),))
        row=cur.fetchone()
        if row and row[0]>0:
            cur.execute('UPDATE admins SET count=count-1 WHERE username=?',(session.get('admin_user'),))
    conn.commit(); conn.close()
    return redirect(url_for('recruitment'))

@app.route('/send_result', methods=['POST'])
def send_result():
    target_discord_id=request.form['discord_id']
    message=request.form.get('message')
    if message and bot_ready.is_set():
        asyncio.run_coroutine_threadsafe(send_dm_async(target_discord_id,message),bot.loop)
    if session.get('admin'):
        conn=sqlite3.connect(DB_FILE)
        cur=conn.cursor()
        cur.execute('SELECT count, discord_id FROM admins WHERE username=?',(session.get('admin_user'),))
        row=cur.fetchone(); conn.close()
        total=row[0] if row else 0
        summary=f'Você fez um total de {total} recrutamentos. Parabéns!'
        if bot_ready.is_set():
            asyncio.run_coroutine_threadsafe(send_dm_async(row[1],summary),bot.loop)
        flash(summary)
    return redirect(url_for('recruitment'))

if __name__=='__main__':
    print('Aguardando bot conectar...')
    app.run(host='0.0.0.0', port=5000, debug=True)