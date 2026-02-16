let ws = null;
let currentUser = null;
let currentMatch = null;
let wsConnected = false;
let statsRefreshInterval = null;

async function loadComponent(id, url) {
    const response = await fetch(url);
    const text = await response.text();
    document.getElementById(id).innerHTML = text;
}


function applyDarkMode() {
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
    updateDarkModeButton();
}

function updateDarkModeButton() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const authDarkModeToggle = document.getElementById('authDarkModeToggle');

    const buttonText = document.body.classList.contains('dark-mode') ? '<i class="fas fa-sun"></i> Светлый режим' : '<i class="fas fa-moon"></i> Темный режим';

    if (darkModeToggle) {
        darkModeToggle.innerHTML = buttonText;
    }
    if (authDarkModeToggle) {
        authDarkModeToggle.innerHTML = buttonText;
    }
}


function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
    <span>${message}</span>
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}


function showPanel(panelId) {
    
    if (statsRefreshInterval) {
        clearInterval(statsRefreshInterval);
        statsRefreshInterval = null;
    }

    document.querySelectorAll('.content-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    document.getElementById(panelId + 'Panel').classList.add('active');

    
    const tabs = document.querySelectorAll('.nav-tab');
    const panelMap = {
        'problems': 0,
        'pvp': 1,
        'stats': 2,
        'leaderboard': 3,
        'profile': 4,
        'admin': 5
    };
    const tabIndex = panelMap[panelId];
    if (tabIndex !== undefined && tabs[tabIndex]) {
        tabs[tabIndex].classList.add('active');
    }

    
    switch(panelId) {
        case 'problems':
            loadProblems();
            break;
        case 'stats':
            loadStats();
            
            statsRefreshInterval = setInterval(loadStats, 5000);
            break;
        case 'leaderboard':
            loadLeaderboard();
            break;
        case 'pvp':
            loadActiveMatches();
            break;
        case 'profile':
            loadProfile();
            break;
        case 'admin':
            loadAdminData();
            break;
    }
}


function showAuthTab(tab) {
    const loginBtn = document.getElementById('loginTabBtn');
    const registerBtn = document.getElementById('registerTabBtn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (tab === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        loginBtn.classList.add('active');
        registerBtn.classList.remove('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        loginBtn.classList.remove('active');
        registerBtn.classList.add('active');
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    if (!username || !password) {
        showNotification('Заполните все поля', 'error');
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            showNotification(`Добро пожаловать, ${currentUser.username}!`, 'success');
            updateUIAfterLogin();
            loadProblems();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения с сервером', 'error');
        console.error('Login error:', error);
    }
}

async function register() {
    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value.trim();

    if (!username || !password) {
        showNotification('Заполните имя пользователя и пароль', 'error');
        return;
    }

    if (password.length < 6) {
        showNotification('Пароль должен содержать минимум 6 символов', 'error');
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, email, password})
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            showAuthTab('login');
            document.getElementById('loginUsername').value = username;
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения с сервером', 'error');
        console.error('Register error:', error);
    }
}

function logout() {
    currentUser = null;
    currentMatch = null;

    if (ws && wsConnected) {
        ws.close();
        wsConnected = false;
    }

    if (statsRefreshInterval) {
        clearInterval(statsRefreshInterval);
        statsRefreshInterval = null;
    }

    document.getElementById('authPanel').classList.add('active');
    document.getElementById('navTabs').style.display = 'none';
    document.getElementById('userPanel').style.display = 'none';

    document.querySelectorAll('.content-panel').forEach(panel => {
        if (panel.id !== 'authPanel') panel.classList.remove('active');
    });

        const authDarkModeToggle = document.getElementById('authDarkModeToggle');
        if (authDarkModeToggle) {
            authDarkModeToggle.style.display = 'block'; 
        }

        showNotification('Вы вышли из системы', 'info');
}

function updateUIAfterLogin() {
    document.getElementById('userName').textContent = currentUser.username;
    document.getElementById('userRating').textContent = currentUser.rating;
    document.getElementById('userAvatar').textContent = currentUser.username.charAt(0).toUpperCase();

    document.getElementById('userPanel').style.display = 'flex';
    document.getElementById('navTabs').style.display = 'flex';
    document.getElementById('authPanel').classList.remove('active');

    const adminTab = document.querySelector('.admin-tab');
    if (adminTab) {
        adminTab.style.display = currentUser.role === 'admin' ? 'flex' : 'none';
    }

    const authDarkModeToggle = document.getElementById('authDarkModeToggle');
    if (authDarkModeToggle) {
        authDarkModeToggle.style.display = 'none'; 
    }

    connectWebSocket();
    showPanel('problems');
}


async function loadProblems() {
    const category = document.getElementById('categoryFilter')?.value || '';
    const difficulty = document.getElementById('difficultyFilter')?.value || '';

    let url = '/api/problems';
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (difficulty) params.append('difficulty', difficulty);
    if (params.toString()) url += '?' + params.toString();

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderProblems(data.problems);
        } else {
            showNotification('Ошибка загрузки задач', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения с сервером', 'error');
        console.error('Load problems error:', error);
    }
}

function renderProblems(problems) {
    const grid = document.getElementById('problemsGrid');
    const loading = document.getElementById('problemsLoading');

    if (problems.length === 0) {
        grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 50px; color: var(--text-muted);">
        <i class="fas fa-search" style="font-size: 3em; margin-bottom: 20px;"></i>
        <p>Задачи не найдены</p>
        </div>
        `;
        loading.style.display = 'none';
        return;
    }

    grid.innerHTML = problems.map(problem => `
    <div class="problem-card">
    <div class="problem-header">
    <div class="problem-title">${problem.title}</div>
    <div class="problem-difficulty difficulty-${problem.difficulty === 1 ? 'easy' : problem.difficulty === 2 ? 'medium' : 'hard'}">
    ${problem.difficulty_text}
    </div>
    </div>
    <div class="problem-category">${problem.category}</div>
    <div class="problem-description">${problem.description}</div>
    <div class="problem-tags">
    ${problem.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
    </div>
    <div class="solve-form">
    <input type="text" class="solve-input" id="answer_${problem.id}" placeholder="Ваш ответ">
    <button class="solve-button" onclick="submitSolution(${problem.id})">
    <i class="fas fa-paper-plane"></i> Отправить
    </button>
    </div>
    </div>
    `).join('');

    loading.style.display = 'none';
}

async function submitSolution(problemId) {
    if (!currentUser) {
        showNotification('Войдите в систему', 'error');
        return;
    }

    const answerInput = document.getElementById(`answer_${problemId}`);
    const answer = answerInput.value.trim();

    if (!answer) {
        showNotification('Введите ответ', 'error');
        return;
    }

    try {
        const response = await fetch('/api/solve', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: currentUser.id,
                problem_id: problemId,
                answer: answer,
                time_spent: Math.floor(Math.random() * 300) + 30
            })
        });

        const data = await response.json();

        if (data.success) {
            if (data.correct) {
                showNotification(`Правильно! +${data.rating_change} к рейтингу`, 'success');
                currentUser.rating += data.rating_change;
                document.getElementById('userRating').textContent = currentUser.rating;
            } else {
                showNotification(`Неправильно. Правильный ответ: ${data.correct_answer}`, 'error');
            }
            answerInput.value = '';
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('Ошибка отправки решения', 'error');
        console.error('Submit solution error:', error);
    }
}


async function loadStats() {
    const userStatsContainer = document.getElementById('userStats');

    
    if (currentUser) {
        userStatsContainer.innerHTML = `
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        Загрузка статистики...
        </div>
        `;
    } else {
        userStatsContainer.innerHTML = `
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        Войдите в систему для просмотра личной статистики.
        </div>
        `;
    }

    try {
        const statsResponse = await fetch('/api/stats');
        const statsData = await statsResponse.json();

        if (statsData.success) {
            document.getElementById('totalUsers').textContent = statsData.stats.users_count;
            document.getElementById('totalProblems').textContent = statsData.stats.problems_count;
            document.getElementById('correctSolutions').textContent = statsData.stats.correct_solutions;
            document.getElementById('matchesPlayed').textContent = statsData.stats.matches_played;
        } else {
            showNotification('Ошибка загрузки общей статистики платформы', 'error');
            
        }
    } catch (error) {
        console.error('Load platform stats error:', error);
        showNotification('Ошибка соединения с сервером для общей статистики', 'error');
        
    }

    if (currentUser) {
        try {
            const userStatsResponse = await fetch(`/api/user/${currentUser.id}`);
            const userStatsData = await userStatsResponse.json();

            if (userStatsData.success) {
                const user = userStatsData.user;
                
                currentUser.rating = user.rating;
                document.getElementById('userRating').textContent = user.rating;

                userStatsContainer.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
                <div style="text-align: center;">
                <div style="font-size: 1.8em; color: var(--primary-color); font-weight: bold;">${user.stats.total_problems}</div>
                <div style="color: var(--text-muted);">Всего решено</div>
                </div>
                <div style="text-align: center;">
                <div style="font-size: 1.8em; color: var(--secondary-color); font-weight: bold;">${user.stats.correct_answers}</div>
                <div style="color: var(--text-muted);">Правильно</div>
                </div>
                <div style="text-align: center;">
                <div style="font-size: 1.8em; color: var(--accent-color); font-weight: bold;">${user.stats.accuracy}%</div>
                <div style="color: var(--text-muted);">Точность</div>
                </div>
                <div style="text-align: center;">
                <div style="font-size: 1.8em; color: var(--text-color); font-weight: bold;">${user.stats.avg_time}s</div>
                <div style="color: var(--text-muted);">Среднее время</div>
                </div>
                </div>
                ${user.categories.length > 0 ? `
                    <h4 style="color: var(--text-muted); margin: 25px 0 12px 0;">По категориям:</h4>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                    ${user.categories.map(cat => `
                        <div style="background: rgba(var(--primary-color-rgb), 0.1); padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--primary-color);">
                        <div style="display: flex; justify-content: space-between;">
                        <span>${cat.category}</span>
                        <span>${cat.correct}/${cat.total} (${cat.total > 0 ? Math.round(cat.correct/cat.total*100) : 0}%)</span>
                        </div>
                        </div>
                        `).join('')}
                        </div>
                        ` : ''}
                        `;
            } else {
                userStatsContainer.innerHTML = `
                <div style="text-align: center; padding: 30px; color: var(--text-muted);">
                Не удалось загрузить личную статистику. ${userStatsData.error || ''}
                </div>
                `;
                showNotification('Ошибка загрузки личной статистики', 'error');
            }
        } catch (error) {
            console.error('Load user stats error:', error);
            userStatsContainer.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">
            Ошибка соединения с сервером для личной статистики. Попробуйте позже.
            </div>
            `;
            showNotification('Ошибка соединения с сервером для личной статистики', 'error');
        }
    }
}


async function loadLeaderboard() {
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = `
    <tr>
    <td colspan="6" style="text-align: center; padding: 50px; color: var(--text-muted);">
    Загрузка таблицы лидеров...
    </td>
    </tr>
    `;

    try {
        const response = await fetch('/api/leaderboard');
        const data = await response.json();

        if (data.success) {
            renderLeaderboard(data.leaderboard);
        } else {
            tbody.innerHTML = `
            <tr>
            <td colspan="6" style="text-align: center; padding: 50px; color: var(--text-muted);">
            Не удалось загрузить таблицу лидеров. ${data.error || ''}
            </td>
            </tr>
            `;
            showNotification('Ошибка загрузки таблицы лидеров', 'error');
        }
    } catch (error) {
        console.error('Load leaderboard error:', error);
        tbody.innerHTML = `
        <tr>
        <td colspan="6" style="text-align: center; padding: 50px; color: var(--text-muted);">
        Ошибка соединения с сервером. Попробуйте позже.
        </td>
        </tr>
        `;
        showNotification('Ошибка загрузки таблицы лидеров', 'error');
    }
}

function renderLeaderboard(leaderboard) {
    const tbody = document.getElementById('leaderboardBody');

    if (leaderboard.length === 0) {
        tbody.innerHTML = `
        <tr>
        <td colspan="6" style="text-align: center; padding: 50px; color: var(--text-muted);">
        Нет данных для отображения
        </td>
        </tr>
        `;
        return;
    }

    tbody.innerHTML = leaderboard.map(player => `
    <tr>
    <td class="rank rank-${player.rank}">${player.rank}</td>
    <td>
    <div class="username-cell">
    <div class="user-rank-badge rank-${player.rank <= 3 ? player.rank : 'other'}-badge">${player.rank}</div>
    ${player.username}
    ${currentUser && player.id === currentUser.id ? '<span style="color: var(--primary-color); margin-left: 5px;">(Вы)</span>' : ''}
    </div>
    </td>
    <td style="color: var(--secondary-color); font-weight: bold;">${player.rating}</td>
    <td class="hide-on-mobile">${player.solved}</td>
    <td class="hide-on-mobile">${player.correct}</td>
    <td class="hide-on-mobile">${player.accuracy}%</td>
    </tr>
    `).join('');
}


async function loadActiveMatches() {
    try {
        const response = await fetch('/api/matches');
        const data = await response.json();

        if (data.success) {
            renderActiveMatches(data.matches);
        }
    } catch (error) {
        console.error('Load matches error:', error);
    }
}

function renderActiveMatches(matches) {
    const container = document.getElementById('activeMatches');

    if (matches.length === 0) {
        container.innerHTML = `
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        <i class="fas fa-search" style="font-size: 2em; margin-bottom: 15px;"></i>
        <p>Нет активных матчей</p>
        </div>
        `;
        return;
    }

    container.innerHTML = matches.map(match => `
    <div class="match-card">
    <div class="match-header">
    <div>
    <span class="match-status status-${match.status.toLowerCase()}">${match.status === 'waiting' ? 'Ожидание' : match.status === 'active' ? 'Идет' : 'Завершен'}</span>
    </div>
    <div style="color: var(--text-muted); font-size: 0.9em;">
    ${new Date(match.started_at).toLocaleTimeString()}
    </div>
    </div>
    <div class="match-players">
    <div>
    <div style="font-weight: bold;">${match.player1}</div>
    <div style="font-size: 0.9em; color: var(--text-muted);">vs</div>
    <div>${match.player2 || 'Ожидание...'}</div>
    </div>
    <div>
    <div style="color: var(--text-muted); font-size: 0.9em; margin-bottom: 5px;">Задача:</div>
    <div>${match.problem}</div>
    </div>
    <div>
    ${match.status === 'waiting' && (!currentUser || match.player1 !== currentUser.username) ? `
        <button class="neon-button" onclick="joinMatch(${match.id})" style="padding: 8px 15px; font-size: 0.9em;">
        Присоединиться
        </button>
        ` : ''}
        </div>
        </div>
        </div>
        `).join('');
}

async function createMatch() {
    if (!currentUser) {
        showNotification('Войдите в систему', 'error');
        return;
    }

    try {
        const response = await fetch('/api/match/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: currentUser.id})
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            currentMatch = {id: data.match_id};
            loadActiveMatches();
            
            await setupCurrentMatch(data.match_id);
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Create match error:', error);
        showNotification('Ошибка создания матча', 'error');
    }
}

async function joinMatch(matchId) {
    if (!currentUser) {
        showNotification('Войдите в систему', 'error');
        return;
    }

    try {
        const response = await fetch('/api/match/join', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: currentUser.id,
                match_id: matchId
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            currentMatch = {id: matchId};
            await setupCurrentMatch(matchId);
            loadActiveMatches();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Join match error:', error);
        showNotification('Ошибка входа в матч', 'error');
    }
}

async function setupCurrentMatch(matchId) {
    try {
        const response = await fetch(`/api/match/${matchId}`);
        const data = await response.json();

        if (data.success && data.match) {
            const match = data.match;
            const container = document.getElementById('currentMatch');

            
            const isParticipant = currentUser &&
            (match.player1_id === currentUser.id || match.player2_id === currentUser.id);

            let matchContent = '';

            
            if (!isParticipant) {
                matchContent = `
                <div style="text-align: center; padding: 50px; color: var(--text-muted);">
                <i class="fas fa-eye" style="font-size: 3em; margin-bottom: 20px;"></i>
                <p>Вы не являетесь участником этого матча.</p>
                <p>Текущий статус: ${match.status === 'waiting' ? 'Ожидание игроков' :
                    match.status === 'active' ? 'Идет игра' : 'Завершен'}</p>
                    <button class="neon-button purple" onclick="showPanel('pvp')" style="margin-top: 20px;">
                    <i class="fas fa-redo"></i> К списку матчей
                    </button>
                    </div>
                    `;
                    container.innerHTML = matchContent;
                    return;
            }

            
            const isPlayer1 = match.player1_id === currentUser.id;
            const playerName = isPlayer1 ? match.player1 : match.player2;
            const opponentName = isPlayer1 ? match.player2 : match.player1;

            if (match.status === 'waiting') {
                if (match.problem) {
                    const problem = match.problem;
                    matchContent = `
                    <div style="text-align: center;">
                    <div class="match-status status-waiting" style="margin: 0 auto 20px auto;">
                    Матч #${match.id} создан. Ожидание соперника...
                    </div>
                    <div style="margin-bottom: 30px;">
                    <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">Задача: ${problem.title}</div>
                    <div style="background: rgba(var(--primary-color-rgb), 0.1); padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(var(--primary-color-rgb), 0.3);">
                    <div class="problem-category">${problem.category}</div>
                    <p style="color: var(--text-color); line-height: 1.6;">${problem.description}</p>
                    </div>
                    </div>
                    <div style="text-align: center; color: var(--text-muted); padding: 20px 0;">
                    <i class="fas fa-hourglass-half" style="font-size: 2em; margin-bottom: 10px;"></i>
                    <p>Ожидание присоединения второго игрока...</p>
                    <p style="font-size: 0.9em;">Игрок 1: ${match.player1 || 'Неизвестный'}</p>
                    ${match.player2 ? `<p style="font-size: 0.9em;">Игрок 2: ${match.player2}</p>` : ''}
                    </div>
                    </div>
                    `;
                } else {
                    matchContent = `
                    <div style="text-align: center; padding: 50px; color: var(--text-muted);">
                    <i class="fas fa-hourglass-half" style="font-size: 3em; margin-bottom: 20px;"></i>
                    <p>Ожидание соперника для матча #${match.id}...</p>
                    <p style="font-size: 0.9em;">Игрок 1: ${match.player1 || 'Неизвестный'}</p>
                    ${match.player2 ? `<p style="font-size: 0.9em;">Игрок 2: ${match.player2}</p>` : ''}
                    </div>
                    `;
                }
            } else if (match.status === 'active' && match.problem) {
                const problem = match.problem;

                
                const playerAnswer = isPlayer1 ? match.player1_answer : match.player2_answer;
                const opponentAnswer = isPlayer1 ? match.player2_answer : match.player1_answer;
                const playerTime = isPlayer1 ? match.player1_time : match.player2_time;
                const opponentTime = isPlayer1 ? match.player2_time : match.player1_time;
                const playerSubmitted = playerAnswer !== null && playerAnswer !== undefined;
                const opponentSubmitted = opponentAnswer !== null && opponentAnswer !== undefined;
                const bothSubmitted = playerSubmitted && opponentSubmitted;

                
                if (bothSubmitted) {
                    
                    const problem_response = await fetch(`/api/problem/${match.problem_id}`);
                    const problem_data = await problem_response.json();
                    let correct_answer = '';
                    if (problem_data.success && problem_data.problem && problem_data.problem.answer) {
                        correct_answer = problem_data.problem.answer.trim().toLowerCase();
                    }
                    
                    const playerCorrect = playerAnswer && playerAnswer.trim().toLowerCase() === correct_answer;
                    const opponentCorrect = opponentAnswer && opponentAnswer.trim().toLowerCase() === correct_answer;
                    
                    matchContent = `
                    <div style="text-align: center;">
                    <div class="match-status status-active" style="margin: 0 auto 20px auto;">
                    Матч #${match.id} - Оба игрока ответили!
                    </div>
                    <div style="margin-bottom: 30px;">
                    <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">Задача: ${problem.title}</div>
                    <div style="background: rgba(var(--primary-color-rgb), 0.1); padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(var(--primary-color-rgb), 0.3);">
                    <div class="problem-category">${problem.category}</div>
                    <p style="color: var(--text-color); line-height: 1.6;">${problem.description}</p>
                    </div>
                    </div>
                    <div class="pvp-score-display" style="margin: 30px 0;">
                    <div class="player-score" style="border: 2px solid rgba(var(--border-color-rgb), 0.5); margin-bottom: 20px; padding: 20px; border-radius: 8px;">
                    <h4>${playerName} (Вы)</h4>
                    <div style="font-size: 1.1em; margin: 10px 0;">
                    <strong>Ваш ответ:</strong> ${playerAnswer}
                    ${playerCorrect ? '<span style="color: var(--success-color); margin-left: 10px;"><i class="fas fa-check-circle"></i> Правильно!</span>' : '<span style="color: var(--error-color); margin-left: 10px;"><i class="fas fa-times-circle"></i> Неправильно</span>'}
                    </div>
                    <div style="font-size: 0.9em; color: var(--text-muted);">Время: ${playerTime || 0}с</div>
                    </div>
                    <div class="player-score" style="border: 2px solid rgba(var(--border-color-rgb), 0.5); padding: 20px; border-radius: 8px;">
                    <h4>${opponentName}</h4>
                    <div style="font-size: 1.1em; margin: 10px 0;">
                    <strong>Ответ соперника:</strong> ${opponentAnswer}
                    ${opponentCorrect ? '<span style="color: var(--success-color); margin-left: 10px;"><i class="fas fa-check-circle"></i> Правильно!</span>' : '<span style="color: var(--error-color); margin-left: 10px;"><i class="fas fa-times-circle"></i> Неправильно</span>'}
                    </div>
                    <div style="font-size: 0.9em; color: var(--text-muted);">Время: ${opponentTime || 0}с</div>
                    </div>
                    </div>
                    <div style="color: var(--text-muted); padding: 20px 0;">
                    <p>Ожидаем завершения матча...</p>
                    </div>
                    </div>
                    `;
                } else if (playerSubmitted) {
                    
                    matchContent = `
                    <div style="text-align: center;">
                    <div class="match-status status-active" style="margin: 0 auto 20px auto;">
                    Матч #${match.id} идет!
                    </div>
                    <div style="margin-bottom: 30px;">
                    <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">Задача: ${problem.title}</div>
                    <div style="background: rgba(var(--primary-color-rgb), 0.1); padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(var(--primary-color-rgb), 0.3);">
                    <div class="problem-category">${problem.category}</div>
                    <p style="color: var(--text-color); line-height: 1.6;">${problem.description}</p>
                    </div>
                    </div>
                    <div style="text-align: center; color: var(--text-muted); padding: 20px 0;">
                    <i class="fas fa-check-circle" style="font-size: 2em; margin-bottom: 10px; color: var(--success-color);"></i>
                    <p>Вы уже отправили ответ: <strong>${playerAnswer}</strong></p>
                    <p>Ожидаем ответа от ${opponentName || 'соперника'}...</p>
                    </div>
                    </div>
                    `;
                } else {
                    
                    matchContent = `
                    <div style="text-align: center;">
                    <div class="match-status status-active" style="margin: 0 auto 20px auto;">
                    Матч #${match.id} идет!
                    </div>
                    <div style="margin-bottom: 30px;">
                    <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">Задача: ${problem.title}</div>
                    <div style="background: rgba(var(--primary-color-rgb), 0.1); padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(var(--primary-color-rgb), 0.3);">
                    <div class="problem-category">${problem.category}</div>
                    <p style="color: var(--text-color); line-height: 1.6;">${problem.description}</p>
                    </div>
                    </div>
                    <div class="solve-form" style="max-width: 400px; margin: 0 auto;">
                    <input type="text" id="matchAnswer" class="solve-input" placeholder="Ваш ответ" required>
                    <button class="solve-button" onclick="submitMatchAnswer()">
                    <i class="fas fa-paper-plane"></i> Отправить
                    </button>
                    </div>
                    ${opponentSubmitted ?
                        `<p style="color: var(--accent-color); margin-top: 15px;">Соперник уже отправил ответ!</p>` : ''}
                        </div>
                        `;
                }
            } else if (match.status === 'finished') {
                
                const problem_response = await fetch(`/api/problem/${match.problem_id}`);
                const problem_data = await problem_response.json();

                let correct_answer = '';
                if (problem_data.success && problem_data.problem && problem_data.problem.answer) {
                    correct_answer = problem_data.problem.answer.trim().toLowerCase();
                } else if (match.problem && match.problem.answer) {
                    correct_answer = match.problem.answer.trim().toLowerCase();
                }

                
                const player1Answer = match.player1_answer || '';
                const player2Answer = match.player2_answer || '';
                const player1Time = match.player1_time || 0;
                const player2Time = match.player2_time || 0;

                
                const player1Correct = player1Answer.trim().toLowerCase() === correct_answer;
                const player2Correct = player2Answer.trim().toLowerCase() === correct_answer;

                
                let winnerText = '';
                let playerStatus = '';
                let opponentStatus = '';

                if (match.winner_id === currentUser.id) {
                    winnerText = '<div class="winner-badge" style="color: var(--success-color); font-weight: bold; font-size: 1.2em; margin-bottom: 20px;">🏆 ВЫ ПОБЕДИЛИ!</div>';
                    playerStatus = 'ПОБЕДИТЕЛЬ';
                    opponentStatus = 'ПРОИГРАВШИЙ';
                } else if (match.winner_id) {
                    const winnerName = match.winner_id === match.player1_id ? match.player1 : match.player2;
                    winnerText = `<div style="color: var(--accent-color); font-weight: bold; font-size: 1.2em; margin-bottom: 20px;">🏆 Победитель: ${winnerName}</div>`;
                    if (match.winner_id === match.player1_id) {
                        playerStatus = isPlayer1 ? 'ПОБЕДИТЕЛЬ' : 'ПРОИГРАВШИЙ';
                        opponentStatus = isPlayer1 ? 'ПРОИГРАВШИЙ' : 'ПОБЕДИТЕЛЬ';
                    } else {
                        playerStatus = isPlayer1 ? 'ПРОИГРАВШИЙ' : 'ПОБЕДИТЕЛЬ';
                        opponentStatus = isPlayer1 ? 'ПОБЕДИТЕЛЬ' : 'ПРОИГРАВШИЙ';
                    }
                } else {
                    winnerText = '<div style="color: var(--text-muted); font-weight: bold; font-size: 1.2em; margin-bottom: 20px;">🤝 НИЧЬЯ</div>';
                    playerStatus = 'НИЧЬЯ';
                    opponentStatus = 'НИЧЬЯ';
                }

                
                const playerStatusColor = playerStatus === 'ПОБЕДИТЕЛЬ' ? 'var(--success-color)' :
                playerStatus === 'ПРОИГРАВШИЙ' ? 'var(--error-color)' : 'var(--text-muted)';
                const opponentStatusColor = opponentStatus === 'ПОБЕДИТЕЛЬ' ? 'var(--success-color)' :
                opponentStatus === 'ПРОИГРАВШИЙ' ? 'var(--error-color)' : 'var(--text-muted)';

                
                matchContent = `
                <div style="text-align: center;">
                <div class="match-status status-finished" style="margin: 0 auto 20px auto;">
                Матч #${match.id} завершен!
                </div>

                ${winnerText}

                <div class="pvp-score-display" style="margin: 30px 0;">
                <div class="player-score ${match.winner_id === match.player1_id ? 'winner' : ''}"
                style="border: 2px solid ${match.winner_id === match.player1_id ? 'var(--secondary-color)' : 'rgba(var(--border-color-rgb), 0.5)'};">
                <h4>${match.player1}</h4>
                <div style="font-size: 0.9em; color: ${player1Correct ? 'var(--success-color)' : 'var(--error-color)'};">
                Ответ: ${player1Answer || 'Не отправлен'}
                ${player1Correct ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-times-circle"></i>'}
                </div>
                <div style="font-size: 0.9em; color: var(--text-muted);">Время: ${player1Time}s</div>
                <div class="score" style="color: ${match.winner_id === match.player1_id ? 'var(--secondary-color)' : 'var(--text-muted)'};
                font-weight: bold; margin-top: 10px;">
                ${match.winner_id === match.player1_id ? '🏆 ПОБЕДИТЕЛЬ' : ''}
                </div>
                <div style="color: ${match.player1_id === currentUser.id ? playerStatusColor : opponentStatusColor};
                font-weight: bold; margin-top: 5px;">
                ${match.player1_id === currentUser.id ? playerStatus : opponentStatus}
                </div>
                </div>
                <div style="font-size: 2em; display: flex; align-items: center; justify-content: center; color: var(--text-muted);">VS</div>
                <div class="player-score ${match.winner_id === match.player2_id ? 'winner' : ''}"
                style="border: 2px solid ${match.winner_id === match.player2_id ? 'var(--secondary-color)' : 'rgba(var(--border-color-rgb), 0.5)'};">
                <h4>${match.player2}</h4>
                <div style="font-size: 0.9em; color: ${player2Correct ? 'var(--success-color)' : 'var(--error-color)'};">
                Ответ: ${player2Answer || 'Не отправлен'}
                ${player2Correct ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-times-circle"></i>'}
                </div>
                <div style="font-size: 0.9em; color: var(--text-muted);">Время: ${player2Time}s</div>
                <div class="score" style="color: ${match.winner_id === match.player2_id ? 'var(--secondary-color)' : 'var(--text-muted)'};
                font-weight: bold; margin-top: 10px;">
                ${match.winner_id === match.player2_id ? '🏆 ПОБЕДИТЕЛЬ' : ''}
                </div>
                <div style="color: ${match.player2_id === currentUser.id ? playerStatusColor : opponentStatusColor};
                font-weight: bold; margin-top: 5px;">
                ${match.player2_id === currentUser.id ? playerStatus : opponentStatus}
                </div>
                </div>
                </div>

                ${correct_answer ? `
                    <div style="margin: 20px 0; padding: 15px; background: rgba(var(--accent-color-rgb), 0.1); border-radius: 8px;">
                    <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 5px;">Правильный ответ:</div>
                    <div style="color: var(--accent-color); font-size: 1.2em; font-weight: bold;">${correct_answer}</div>
                    </div>
                    ` : ''}

                    <button class="neon-button purple" onclick="showPanel('pvp')" style="margin-top: 20px;">
                    <i class="fas fa-redo"></i> К списку матчей
                    </button>
                    </div>
                    `;
            } else {
                matchContent = `
                <div style="text-align: center; padding: 50px; color: var(--text-muted);">
                <i class="fas fa-gamepad" style="font-size: 3em; margin-bottom: 20px;"></i>
                <p>Матч #${match.id} в неизвестном состоянии или нет задачи.</p>
                </div>
                `;
            }
            container.innerHTML = matchContent;

            if (wsConnected) {
                ws.send(JSON.stringify({
                    type: 'auth',
                    user_id: currentUser.id,
                    match_id: matchId
                }));
            }
        } else {
            showNotification('Не удалось загрузить данные матча', 'error');
            document.getElementById('currentMatch').innerHTML = `
            <div style="text-align: center; padding: 50px; color: var(--text-muted);">
            <i class="fas fa-exclamation-circle" style="font-size: 3em; margin-bottom: 20px;"></i>
            <p>Не удалось загрузить данные матча. ${data.error || ''}</p>
            </div>
            `;
        }
    } catch (error) {
        console.error('Setup match error:', error);
        showNotification('Ошибка загрузки матча', 'error');
        document.getElementById('currentMatch').innerHTML = `
        <div style="text-align: center; padding: 50px; color: var(--text-muted);">
        <i class="fas fa-exclamation-triangle" style="font-size: 3em; margin-bottom: 20px;"></i>
        <p>Ошибка соединения с сервером при загрузке матча. Попробуйте позже.</p>
        </div>
        `;
    }
}

async function submitMatchAnswer() {
    if (!currentUser || !currentMatch) {
        showNotification('Нет активного матча', 'error');
        return;
    }

    const matchAnswerInput = document.getElementById('matchAnswer');
    const solveButton = document.querySelector('#currentMatch .solve-button');

    if (!matchAnswerInput || !solveButton) {
        console.error("Error: Match answer input or solve button not found.");
        showNotification('Ошибка: Элементы ввода ответа не найдены.', 'error');
        return;
    }

    const answer = matchAnswerInput.value.trim();
    if (!answer) {
        showNotification('Введите ответ', 'error');
        return;
    }

    
    matchAnswerInput.disabled = true;
    solveButton.disabled = true;
    solveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';

    try {
        
        const timeSpent = Math.floor(Math.random() * 180) + 30;

        const response = await fetch('/api/match/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: currentUser.id,
                match_id: currentMatch.id,
                answer: answer,
                time_spent: timeSpent
            })
        });

        const data = await response.json();

        if (data.success) {
            if (data.match_finished) {
                showNotification('Матч завершен!', 'success');
            } else {
                showNotification('Ответ отправлен! Ожидаем соперника...', 'success');
            }

            
            await setupCurrentMatch(currentMatch.id);

            if (wsConnected) {
                ws.send(JSON.stringify({
                    type: 'answer_submitted',
                    match_id: currentMatch.id,
                    user_id: currentUser.id
                }));
            }
        } else {
            showNotification(data.error, 'error');
            matchAnswerInput.disabled = false;
            solveButton.disabled = false;
            solveButton.innerHTML = '<i class="fas fa-paper-plane"></i> Отправить';
        }
    } catch (error) {
        console.error('Submit match answer error:', error);
        showNotification('Ошибка отправки ответа. Проверьте соединение с сервером.', 'error');
        matchAnswerInput.disabled = false;
        solveButton.disabled = false;
        solveButton.innerHTML = '<i class="fas fa-paper-plane"></i> Отправить';
    }
}


async function loadProfile() {
    const container = document.getElementById('profileContent');
    if (!currentUser) {
        container.innerHTML = `
        <div style="text-align: center; padding: 50px; color: var(--text-muted);">
        Войдите в систему для просмотра профиля.
        </div>
        `;
        return;
    }

    
    container.innerHTML = `
    <div style="text-align: center; padding: 50px; color: var(--text-muted);">
    Загрузка профиля...
    </div>
    `;

    try {
        const response = await fetch(`/api/user/${currentUser.id}`);
        const data = await response.json();

        if (data.success) {
            const user = data.user;
            renderProfile(user);
        } else {
            container.innerHTML = `
            <div style="text-align: center; padding: 50px; color: var(--text-muted);">
            Не удалось загрузить данные профиля. ${data.error || ''}
            </div>
            `;
            showNotification('Ошибка загрузки профиля', 'error');
        }
    }
    catch (error) {
        console.error('Load profile error:', error);
        container.innerHTML = `
        <div style="text-align: center; padding: 50px; color: var(--text-muted);">
        Ошибка соединения с сервером. Попробуйте позже.
        </div>
        `;
        showNotification('Ошибка загрузки профиля', 'error');
    }
}

function renderProfile(user) {
    const container = document.getElementById('profileContent');

    container.innerHTML = `
    <div class="profile-card">
    <div class="profile-header">
    <div class="profile-avatar">${user.username.charAt(0).toUpperCase()}</div>
    <div class="profile-info">
    <div class="profile-name">${user.username}</div>
    <div style="display: flex; gap: 15px; margin-top: 10px;">
    <div style="color: var(--secondary-color); font-weight: bold;">
    <i class="fas fa-trophy"></i> ${user.rating}
    </div>
    <div style="color: var(--accent-color); font-weight: bold;">
    <i class="fas fa-star"></i> Уровень ${user.level}
    </div>
    <div style="color: var(--primary-color); font-weight: bold;">
    <i class="fas fa-bolt"></i> ${user.xp} XP
    </div>
    </div>
    <div style="margin-top: 10px; color: var(--text-muted);">
    <span class="user-role role-${user.role}">${user.role === 'admin' ? 'Администратор' : 'Пользователь'}</span>
    </div>
    </div>
    </div>

    <h3 style="color: var(--primary-color); margin-bottom: 20px;">Статистика</h3>
    <div class="profile-stats">
    <div class="profile-stat">
    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">${user.stats.total_problems}</div>
    <div style="color: var(--text-muted);">Решено задач</div>
    </div>
    <div class="profile-stat">
    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">${user.stats.correct_answers}</div>
    <div style="color: var(--text-muted);">Правильных ответов</div>
    </div>
    <div class="profile-stat">
    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">${user.stats.accuracy}%</div>
    <div style="color: var(--text-muted);">Точность</div>
    </div>
    <div class="profile-stat">
    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">${user.stats.pvp_matches}</div>
    <div style="color: var(--text-muted);">PvP матчей</div>
    </div>
    <div class="profile-stat">
    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">${user.stats.pvp_wins}</div>
    <div style="color: var(--text-muted);">PvP побед</div>
    </div>
    <div class="profile-stat">
    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">${user.stats.pvp_winrate}%</div>
    <div style="color: var(--text-muted);">Винрейт</div>
    </div>
    </div>

    ${user.categories.length > 0 ? `
        <h3 style="color: var(--secondary-color); margin: 25px 0 15px 0;">Прогресс по категориям</h3>
        <div style="display: flex; flex-direction: column; gap: 10px;">
        ${user.categories.map(cat => `
            <div style="background: rgba(var(--primary-color-rgb), 0.1); padding: 12px 15px; border-radius: 6px; border: 1px solid rgba(var(--primary-color-rgb), 0.3);">
            <div style="display: flex; justify-content: space-between;">
            <span>${cat.category}</span>
            <span>${cat.correct}/${cat.total} (${cat.total > 0 ? Math.round(cat.correct/cat.total*100) : 0}%)</span>
            </div>
            <div style="background: rgba(var(--text-muted-rgb), 0.2); height: 8px; border-radius: 4px; overflow: hidden;">
            <div style="width: ${cat.total > 0 ? (cat.correct/cat.total*100) : 0}%; height: 100%; background: var(--secondary-color);"></div>
            </div>
            </div>
            `).join('')}
            </div>
            ` : ''}
            </div>
            `;
}

function showEditProfileModal() {
    if (!currentUser) return;

    document.getElementById('editProfileUsername').value = currentUser.username;
    
    showModal('editProfileModal');
}

async function updateProfile() {
    if (!currentUser) return;

    const email = document.getElementById('editProfileEmail').value.trim();
    const password = document.getElementById('editProfilePassword').value.trim();

    
    
    showNotification('Функция обновления профиля пока не реализована на сервере', 'info');
    closeModal();
}


function connectWebSocket() {
    if (wsConnected) return;

    try {
        ws = new WebSocket('ws://localhost:8765');

        ws.onopen = () => {
            wsConnected = true;
            console.log('WebSocket connected');

            if (currentUser) {
                ws.send(JSON.stringify({
                    type: 'auth',
                    user_id: currentUser.id,
                    match_id: currentMatch ? currentMatch.id : null 
                }));
            }
        };

        ws.onmessage = async (event) => {
            try {
                const data = JSON.parse(event.data);
                await handleWebSocketMessage(data);
            } catch (error) {
                console.error('WebSocket message error:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            wsConnected = false;
            console.log('WebSocket disconnected');
            setTimeout(connectWebSocket, 5000);
        };
    } catch (error) {
        console.error('WebSocket connection error:', error);
    }
}

async function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'match_started':
            showNotification(`Матч #${data.match_id} начался! ${data.player1_username} vs ${data.player2_username}`, 'success');

            
            if (currentUser && (data.player1_id === currentUser.id || data.player2_id === currentUser.id)) {
                currentMatch = { id: data.match_id };
                await setupCurrentMatch(data.match_id);
            }

            loadActiveMatches();
            break;

        case 'answer_submitted':
            
            if (currentMatch && data.match_id === currentMatch.id) {
                if (data.user_id !== currentUser.id) {
                    showNotification(`Соперник отправил ответ!`, 'info');
                }
                
                await setupCurrentMatch(currentMatch.id);
            }
            break;

        case 'match_finished':
            showNotification(`Матч #${data.match_id} завершен!`, 'success');

            
            if (currentMatch && data.match_id === currentMatch.id) {
                await setupCurrentMatch(currentMatch.id);
                loadStats(); 
            }

            loadActiveMatches();
            break;

        case 'player_left':
            showNotification(`Игрок ${data.username || ''} покинул матч #${data.match_id}`, 'info');

            if (currentMatch && data.match_id === currentMatch.id) {
                currentMatch = null; 
                document.getElementById('currentMatch').innerHTML = `
                <div style="text-align: center; padding: 50px; color: var(--text-muted);">
                <i class="fas fa-gamepad" style="font-size: 3em; margin-bottom: 20px;"></i>
                <p>Ваш соперник покинул матч. Создайте новый или присоединитесь к существующему.</p>
                </div>
                `;
            }

            loadActiveMatches(); 
            break;
    }
}


async function loadAdminData() {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        showPanel('problems');
        return;
    }

    const userListContainer = document.getElementById('userList');
    const adminStatsContainer = document.getElementById('adminStats');
    const problemsListContainer = document.getElementById('problemsList');

    userListContainer.innerHTML = `
    <div style="text-align: center; padding: 30px; color: var(--text-muted);">
    Загрузка пользователей...
    </div>
    `;
    adminStatsContainer.innerHTML = `
    <div style="text-align: center; padding: 30px; color: var(--text-muted);">
    Загрузка статистики платформы...
    </div>
    `;
    problemsListContainer.innerHTML = `
    <div style="text-align: center; padding: 30px; color: var(--text-muted);">
    Загрузка задач...
    </div>
    `;

    try {
        const usersResponse = await fetch('/api/users');
        const usersData = await usersResponse.json();

        if (usersData.success) {
            renderUserList(usersData.users);
        } else {
            userListContainer.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">
            Не удалось загрузить список пользователей. ${usersData.error || ''}
            </div>
            `;
            showNotification('Ошибка загрузки пользователей', 'error');
        }
    } catch (error) {
        console.error('Load admin users error:', error);
        userListContainer.innerHTML = `
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        Ошибка соединения с сервером для пользователей. Попробуйте позже.
        </div>
        `;
        showNotification('Ошибка загрузки пользователей', 'error');
    }

    try {
        const statsResponse = await fetch('/api/stats');
        const statsData = await statsResponse.json();

        if (statsData.success) {
            adminStatsContainer.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 20px;">
            <div style="text-align: center; background: rgba(var(--accent-color-rgb), 0.1); padding: 15px; border-radius: 8px; border: 1px solid var(--accent-color);">
            <div style="font-size: 1.5em; font-weight: bold; color: var(--accent-color);">${statsData.stats.users_count}</div>
            <div style="font-size: 0.9em; color: var(--text-muted);">Пользователей</div>
            </div>
            <div style="text-align: center; background: rgba(var(--primary-color-rgb), 0.1); padding: 15px; border-radius: 8px; border: 1px solid var(--primary-color);">
            <div style="font-size: 1.5em; font-weight: bold; color: var(--primary-color);">${statsData.stats.problems_count}</div>
            <div style="font-size: 0.9em; color: var(--text-muted);">Задач</div>
            </div>
            <div style="text-align: center; background: rgba(var(--secondary-color-rgb), 0.1); padding: 15px; border-radius: 8px; border: 1px solid var(--secondary-color);">
            <div style="font-size: 1.5em; font-weight: bold; color: var(--secondary-color);">${statsData.stats.correct_solutions}</div>
            <div style="font-size: 0.9em; color: var(--text-muted);">Решений</div>
            </div>
            </div>
            `;
        } else {
            adminStatsContainer.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">
            Не удалось загрузить статистику платформы. ${statsData.error || ''}
            </div>
            `;
            showNotification('Ошибка загрузки статистики платформы', 'error');
        }
    } catch (error) {
        console.error('Load admin stats error:', error);
        adminStatsContainer.innerHTML = `
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        Ошибка соединения с сервером для статистики платформы. Попробуйте позже.
        </div>
        `;
        showNotification('Ошибка загрузки статистики платформы', 'error');
    }

    
    loadAdminProblems();
}

async function loadAdminProblems() {
    const container = document.getElementById('problemsList');
    container.innerHTML = `
    <div style="text-align: center; padding: 30px; color: var(--text-muted);">
    Загрузка задач...
    </div>
    `;

    try {
        const response = await fetch('/api/problems');
        const data = await response.json();

        if (data.success) {
            if (data.problems.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">Нет задач</div>';
                return;
            }

            container.innerHTML = data.problems.map(problem => `
            <div style="background: rgba(var(--text-color-rgb), 0.05); padding: 10px 15px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(var(--border-color-rgb), 0.5);">
            <div style="flex: 1;">
            <div style="font-weight: bold; margin-bottom: 4px;">${problem.title}</div>
            <div style="font-size: 0.8em; color: var(--text-muted);">${problem.category} | ${problem.difficulty_text}</div>
            </div>
            <button class="action-button delete-button" onclick="deleteProblem(${problem.id}, '${problem.title.replace(/\'/g, "\\'")}')">
            <i class="fas fa-trash"></i> Удалить
            </button>
            </div>
            `).join('');
        } else {
            container.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">
            Не удалось загрузить список задач. ${data.error || ''}
            </div>
            `;
            showNotification('Ошибка загрузки задач администратора', 'error');
        }
    } catch (error) {
        console.error('Load admin problems error:', error);
        container.innerHTML = `
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        Ошибка соединения с сервером для задач администратора. Попробуйте позже.
        </div>
        `;
        showNotification('Ошибка загрузки задач администратора', 'error');
    }
}

function renderUserList(users) {
    const container = document.getElementById('userList');

    if (users.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 30px; color: var(--text-muted);">Нет пользователей</div>';
        return;
    }

    container.innerHTML = users.map(user => `
    <div class="user-item">
    <div class="user-details">
    <div style="font-weight: bold; margin-bottom: 5px;">${user.username}</div>
    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
    <span class="user-role role-${user.role}">${user.role === 'admin' ? 'Админ' : 'Пользователь'}</span>
    <span style="color: var(--secondary-color); font-weight: bold;">🏆 ${user.rating}</span>
    ${user.email ? `<span style="color: var(--text-muted); font-size: 0.9em;">${user.email}</span>` : ''}
    </div>
    </div>
    <div class="user-actions">
    <button class="action-button edit-button" onclick="showEditUserModal(${user.id}, '${user.username}', ${user.rating}, '${user.role}')">
    <i class="fas fa-edit"></i>
    </button>
    ${user.id !== currentUser.id ? `
        <button class="action-button delete-button" onclick="adminDeleteUser(${user.id})">
        <i class="fas fa-trash"></i>
        </button>
        ` : ''}
        </div>
        </div>
        `).join('');
}


function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        document.getElementById('modalOverlay').style.display = 'flex'; 
        modal.style.display = 'block';
    }
}

function closeModal() {
    document.getElementById('modalOverlay').style.display = 'none';
    document.querySelectorAll('#modalOverlay > div').forEach(modal => {
        modal.style.display = 'none';
    });
}

function showAddProblemModal() {
    showModal('addProblemModal');
}

async function addProblem() {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        return;
    }

    const title = document.getElementById('modalProblemTitle').value.trim();
    const description = document.getElementById('modalProblemDesc').value.trim();
    const answer = document.getElementById('modalProblemAnswer').value.trim();
    const difficulty = document.getElementById('modalProblemDifficulty').value;
    const category = document.getElementById('modalProblemCategory').value.trim();
    const tags = document.getElementById('modalProblemTags').value.trim();

    if (!title || !description || !answer) {
        showNotification('Заполните обязательные поля', 'error');
        return;
    }

    try {
        const response = await fetch('/api/admin/add_problem', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: currentUser.id,
                title,
                description,
                answer,
                difficulty,
                category,
                tags
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            closeModal();
            document.getElementById('modalProblemTitle').value = '';
            document.getElementById('modalProblemDesc').value = '';
            document.getElementById('modalProblemAnswer').value = '';
            document.getElementById('modalProblemCategory').value = '';
            document.getElementById('modalProblemTags').value = '';

            loadAdminProblems();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Add problem error:', error);
        showNotification('Ошибка добавления задачи', 'error');
    }
}

async function deleteProblem(problemId, problemTitle) {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        return;
    }

    if (!confirm(`Вы уверены, что хотите удалить задачу "${problemTitle}"?`)) {
        return;
    }

    try {
        const response = await fetch('/api/admin/delete_problem', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: currentUser.id,
                problem_id: problemId
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            loadAdminProblems();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Delete problem error:', error);
        showNotification('Ошибка удаления задачи', 'error');
    }
}

function showImportProblemsModal() {
    showModal('importProblemsModal');
}

async function importProblems() {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        return;
    }

    const data = document.getElementById('importProblemsData').value.trim();

    if (!data) {
        showNotification('Введите JSON данные', 'error');
        return;
    }

    try {
        const problems = JSON.parse(data);

        if (!Array.isArray(problems)) {
            showNotification('JSON должен содержать массив задач', 'error');
            return;
        }

        const response = await fetch('/api/admin/import_problems', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: currentUser.id,
                problems: problems
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            closeModal();
            document.getElementById('importProblemsData').value = '';
            loadAdminProblems();
        } else {
            showNotification(result.error, 'error');
        }
    } catch (error) {
        console.error('Import problems error:', error);
        showNotification('Ошибка импорта. Проверьте формат JSON', 'error');
    }
}

function exportProblems() {
    window.open('/api/export/problems', '_blank');
    showNotification('Экспорт начат', 'success');
}

function showAddUserModal() {
    showModal('addUserModal');
}

async function adminAddUser() {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        return;
    }

    const username = document.getElementById('modalUsername').value.trim();
    const email = document.getElementById('modalUserEmail').value.trim();
    const password = document.getElementById('modalUserPassword').value.trim();
    const role = document.getElementById('modalUserRole').value;

    if (!username || !password) {
        showNotification('Заполните имя пользователя и пароль', 'error');
        return;
    }

    if (password.length < 6) {
        showNotification('Пароль должен содержать минимум 6 символов', 'error');
        return;
    }

    try {
        const response = await fetch('/api/admin/add_user', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_id: currentUser.id,
                username,
                email,
                password,
                role
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            closeModal();
            document.getElementById('modalUsername').value = '';
            document.getElementById('modalUserEmail').value = '';
            document.getElementById('modalUserPassword').value = '';

            loadAdminData();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Add user error:', error);
        showNotification('Ошибка добавления пользователя', 'error');
    }
}

function showEditUserModal(userId, username, rating, role) {
    document.getElementById('editUserId').value = userId;
    document.getElementById('editUsername').value = username;
    document.getElementById('editUserRating').value = rating;
    document.getElementById('editUserRole').value = role;
    showModal('editUserModal');
}

async function adminUpdateUser() {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        return;
    }

    const userId = document.getElementById('editUserId').value;
    const rating = document.getElementById('editUserRating').value;
    const role = document.getElementById('editUserRole').value;

    try {
        const response = await fetch('/api/admin/update_user', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_id: currentUser.id,
                user_id: userId,
                rating: parseInt(rating),
                                 role
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            closeModal();
            loadAdminData();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Update user error:', error);
        showNotification('Ошибка обновления пользователя', 'error');
    }
}

async function adminDeleteUser(userId) {
    if (!currentUser || currentUser.role !== 'admin') {
        showNotification('Доступ запрещен', 'error');
        return;
    }

    if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
        return;
    }

    try {
        const response = await fetch('/api/admin/delete_user', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_id: currentUser.id,
                user_id: userId
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            loadAdminData();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        console.error('Delete user error:', error);
        showNotification('Ошибка удаления пользователя', 'error');
    }
}


document.addEventListener('DOMContentLoaded', async () => {
    
    await loadComponent('header-component', './components/header.html');
    await loadComponent('nav-tabs-component', './components/nav_tabs.html');
    await loadComponent('auth-panel-component', './components/auth.html');
    await loadComponent('problems-panel-component', './components/problems.html');
    await loadComponent('pvp-panel-component', './components/pvp.html');
    await loadComponent('stats-panel-component', './components/stats.html');
    await loadComponent('leaderboard-panel-component', './components/leaderboard.html');
    await loadComponent('profile-panel-component', './components/profile.html');
    await loadComponent('admin-panel-component', './components/admin.html');
    await loadComponent('modal-overlay-component', './components/modals.html');

    
    applyDarkMode();
    const headerDarkModeToggle = document.getElementById('darkModeToggle');
    if (headerDarkModeToggle) {
        headerDarkModeToggle.addEventListener('click', toggleDarkMode);
        updateDarkModeButton();
    }

    
    const authPanel = document.getElementById('authPanel');
    if (authPanel) {
        const authDarkModeToggle = document.createElement('button');
        authDarkModeToggle.id = 'authDarkModeToggle';
        authDarkModeToggle.className = 'neon-button';
        authDarkModeToggle.style.position = 'absolute';
        authDarkModeToggle.style.top = '20px';
        authDarkModeToggle.style.right = '20px';
        authDarkModeToggle.addEventListener('click', toggleDarkMode);
        authPanel.prepend(authDarkModeToggle);
        updateDarkModeButton(); 
    }

    
    if (document.getElementById('categoryFilter')) {
        document.getElementById('categoryFilter').addEventListener('change', loadProblems);
    }
    if (document.getElementById('difficultyFilter')) {
        document.getElementById('difficultyFilter').addEventListener('change', loadProblems);
    }

    
    document.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const currentActivePanel = document.querySelector('.content-panel.active');
            if (currentActivePanel && currentActivePanel.id === 'authPanel') {
                const loginForm = document.getElementById('loginForm');
                if (loginForm && loginForm.style.display !== 'none') {
                    login();
                } else {
                    register();
                }
            }
        }
    });

    
    document.getElementById('modalOverlay').addEventListener('click', (e) => {
        if (e.target.id === 'modalOverlay') {
            closeModal();
        }
    });
});


window.platform = {
    login,
    register,
    logout,
    loadProblems,
    submitSolution,
    loadStats,
    loadLeaderboard,
    createMatch,
    joinMatch,
    setupCurrentMatch,
    showPanel,
    showNotification,
    loadProfile,
    showEditProfileModal,
    updateProfile,
    showAddProblemModal,
    addProblem,
    deleteProblem,
    showImportProblemsModal,
    importProblems,
    exportProblems,
    showAddUserModal,
    adminAddUser,
    showEditUserModal,
    adminUpdateUser,
    adminDeleteUser,
    toggleDarkMode 
};
