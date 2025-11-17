
(function() {
    const houseCode = window.HOUSE_CODE || "";
    const authUserId = window.AUTH_USER_ID || "";

    if (!houseCode) {
        console.warn("[SOCKET] no house code found — skipping connection");
        return;
    }

    const socket = io();
    
    socket.on("connect", () => {
        console.log("[SOCKET] connected", socket.id);
        socket.emit("join_house", { house_code: houseCode, auth_user_id: authUserId });
    });

    socket.on("joined", (data) => {
        console.log("[SOCKET] joined house", data);
        if (data.status === "in_progress") {
        window.location.href = data.redirect_url || "/game";
        }
    });

    socket.on("error", (err) => console.error("[SOCKET] error", err));

    socket.on("game_started", (payload) => {
        console.log("Game started", payload);
        const matchId = payload.match_id;

        // Store this globally so game.js can use it
        window.MATCH_ID = matchId;

        // redirect to /game page, where Flask template will have window.AUTH_USER_ID etc.
        window.location.href = `${payload.redirect_url}?match_id=${matchId}`;
        console.log("[SOCKET] game_started", payload);
    });

    socket.on("debug_game_ping", (d) => console.log("[SOCKET] debug ping", d));

    socket.on('game_cancelled', (payload) => {
        console.log('game_cancelled', payload);
        // If the client is on a "game in progress" screen and receives this,
        // redirect or show a modal to notify the player the game was canceled.
        // Example: redirect to create_house to show waiting UI
        setTimeout(() => { window.location.href = "{{ url_for('create_house') }}"; }, 300);
    });

    // Helper to show/hide start button based on numeric count
    function updateStartButton(count) {
        const wrapper = document.getElementById('start-game-wrapper');
        if (!wrapper) return;
        // show when count >= 2
        if (Number(count) >= 2) wrapper.style.display = '';
        else wrapper.style.display = 'none';
    }

    // initial sync from DOM value (in case the page was rendered with a value)
    const playersCountEl = document.getElementById('players-count');
    if (playersCountEl) {
        updateStartButton(parseInt(playersCountEl.textContent || '0', 10));
    }

    // When someone joins — update count and possibly show start button
    socket.on('player_joined', (payload) => {
        console.log('[SOCKET] player_joined', payload);
        if (payload.current_players !== undefined) {
        const el = document.getElementById('players-count');
        if (el) el.textContent = String(payload.current_players);
        updateStartButton(payload.current_players);
        }
        // optionally update players-list here
        if (payload.player_name) {
        const listEl = document.getElementById('players-list');
        if (listEl) {
            const li = document.createElement('li');
            li.textContent = payload.player_name;
            li.dataset.playerId = payload.player_id || '';
            listEl.appendChild(li);
        }
        }
    });

    // If you emit player_left on exits, handle it so the start button hides when count < 2
    socket.on('player_left', (payload) => {
        console.log('[SOCKET] player_left', payload);
        if (payload.current_players !== undefined) {
        const el = document.getElementById('players-count');
        if (el) el.textContent = String(payload.current_players);
        updateStartButton(payload.current_players);
        }
        // remove from players-list if present
        if (payload.player_id) {
        const listEl = document.getElementById('players-list');
        if (listEl) {
            const item = listEl.querySelector(`li[data-player-id="${payload.player_id}"]`);
            if (item) item.remove();
        }
        }
    });

    // In case server or other logic changes allow you to get an 'update_players' event,
    // handle that similarly (keeps DOM in sync)
    socket.on('update_players', (payload) => {
        if (!payload) return;
        if (payload.current_players !== undefined) {
        const el = document.getElementById('players-count');
        if (el) el.textContent = String(payload.current_players);
        updateStartButton(payload.current_players);
        }
        if (Array.isArray(payload.players_list)) {
        const listEl = document.getElementById('players-list');
        if (listEl) {
            listEl.innerHTML = '';
            payload.players_list.forEach(p => {
            const li = document.createElement('li');
            li.textContent = p.name || 'Player';
            li.dataset.playerId = p.id || '';
            listEl.appendChild(li);
            });
        }
        }
    });

})();
