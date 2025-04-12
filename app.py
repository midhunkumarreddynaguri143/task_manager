
# 🔐 Firebase setup
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)
app.secret_key = 'supersecretkey'


# 📌 Homepage
@app.route('/')
def index():
    return redirect('/dashboard')


# 🔑 Login Page
@app.route('/login')
def login():
    return render_template('login.html')


# ✅ Set user after Firebase login
@app.route('/set_user', methods=['POST'])
def set_user():
    uid = request.form['uid']
    session['user_id'] = uid
    return '', 204


# 🚪 Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# 🏠 Dashboard showing boards
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    boards = db.collection('taskboards').stream()
    user_boards = []
    for board in boards:
        data = board.to_dict()
        if data.get('owner') == user_id or user_id in data.get('members', []):
            data['id'] = board.id
            user_boards.append(data)

    return render_template('dashboard.html', boards=user_boards)


# ➕ Create task board
@app.route('/create_board', methods=['POST'])
def create_board():
    title = request.form['title']
    user_id = session['user_id']

    board_ref = db.collection('taskboards').document()
    board_ref.set({
        'title': title,
        'owner': user_id,
        'members': []
    })
    return redirect('/dashboard')


# 📋 View task board
@app.route('/board/<board_id>')
def view_board(board_id):
    board_ref = db.collection('taskboards').document(board_id)
    board = board_ref.get()
    if not board.exists:
        return "Board not found", 404

    board_data = board.to_dict()
    board_data['id'] = board.id

    if session['user_id'] != board_data['owner'] and session['user_id'] not in board_data.get('members', []):
        return "Unauthorized", 403

    tasks_ref = db.collection('tasks').where('board_id', '==', board_id)
    tasks = []
    completed_count = 0
    for task in tasks_ref.stream():
        data = task.to_dict()
        data['id'] = task.id
        if data.get('complete'):
            completed_count += 1
        tasks.append(data)

    total_count = len(tasks)
    active_count = total_count - completed_count

    stats = {
        'total': total_count,
        'completed': completed_count,
        'active': active_count
    }

    return render_template('board.html', board=board_data, board_id=board_id, tasks=tasks, stats=stats)


# 🧩 Add task to board
@app.route('/add_task/<board_id>', methods=['POST'])
def add_task(board_id):
    title = request.form['title']
    due_date = request.form['due_date']
    description = request.form.get('description', '')
    assigned_to = request.form.get('assigned_to') or None

    db.collection('tasks').add({
        'board_id': board_id,
        'title': title,
        'due_date': due_date,
        'description': description,
        'complete': False,
        'completed_at': None,
        'assigned_to': assigned_to,
        'highlight_red': False
    })
    return redirect(f'/board/{board_id}')


# ✅ Toggle task completion
@app.route('/toggle_task/<board_id>/<task_id>', methods=['POST'])
def toggle_task(board_id, task_id):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get()
    if task.exists:
        data = task.to_dict()
        complete = not data.get('complete', False)
        update_data = {'complete': complete}
        update_data['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if complete else None
        task_ref.update(update_data)
    return redirect(f'/board/{board_id}')


# 👥 Add member to board (owner only)
@app.route('/add_member/<board_id>', methods=['POST'])
def add_member(board_id):
    user_to_add = request.form['user_id']
    board_ref = db.collection('taskboards').document(board_id)
    board = board_ref.get()

    if board.exists and board.to_dict().get('owner') == session['user_id']:
        current_members = board.to_dict().get('members', [])
        if user_to_add not in current_members:
            current_members.append(user_to_add)
            board_ref.update({'members': current_members})
    return redirect(f'/board/{board_id}')


# ✏️ Edit Task
@app.route('/edit_task/<board_id>/<task_id>', methods=['GET', 'POST'])
def edit_task(board_id, task_id):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get()
    if not task.exists:
        return "Task not found", 404

    if request.method == 'POST':
        updated_task = {
            'title': request.form['title'],
            'due_date': request.form['due_date'],
            'description': request.form.get('description', '')
        }
        task_ref.update(updated_task)
        return redirect(f'/board/{board_id}')

    task_data = task.to_dict()
    return render_template('edit_task.html', task=task_data, board_id=board_id, task_id=task_id)


# 🗑️ Delete Task
@app.route('/delete_task/<board_id>/<task_id>', methods=['POST'])
def delete_task(board_id, task_id):
    db.collection('tasks').document(task_id).delete()
    return redirect(f'/board/{board_id}')


# 🏷️ Rename Board (Owner Only)
@app.route('/rename_board/<board_id>', methods=['POST'])
def rename_board(board_id):
    new_title = request.form['title']
    board_ref = db.collection('taskboards').document(board_id)
    board = board_ref.get()

    if not board.exists:
        return "Board not found", 404

    if board.to_dict().get('owner') != session['user_id']:
        return "Unauthorized", 403

    board_ref.update({'title': new_title})
    return redirect(f'/board/{board_id}')


# ❌ Remove Member (Owner Only)
@app.route('/remove_member/<board_id>', methods=['POST'])
def remove_member(board_id):
    user_to_remove = request.form['user_id']
    board_ref = db.collection('taskboards').document(board_id)
    board = board_ref.get()

    if not board.exists:
        return "Board not found", 404

    board_data = board.to_dict()
    if board_data.get('owner') != session['user_id']:
        return "Unauthorized", 403

    members = board_data.get('members', [])
    if user_to_remove in members:
        members.remove(user_to_remove)
        board_ref.update({'members': members})

        # 🚨 Unassign and highlight tasks
        tasks = db.collection('tasks').where('board_id', '==', board_id).stream()
        for task in tasks:
            task_data = task.to_dict()
            if task_data.get('assigned_to') == user_to_remove:
                db.collection('tasks').document(task.id).update({
                    'assigned_to': None,
                    'highlight_red': True
                })

    return redirect(f'/board/{board_id}')


# ✅ Run Flask server
if __name__ == '__main__':
    app.run(debug=True)
