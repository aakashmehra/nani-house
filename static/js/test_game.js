document.addEventListener('DOMContentLoaded', () => {
    // ===== Countdown logic (unchanged) =====
    const overlay = document.getElementById('countdownOverlay');
    const countEl = document.getElementById('countNumber');
    const board = document.getElementById('board');
    const authUserId = window.AUTH_USER_ID || "";    // injected by Flask template
    const matchId = window.HOUSE_ID || window.MATCH_ID || null; // whichever you use
    const playerId = String(authUserId || "");
    const socket = io();

    // small safety: if no match/player id, warn (socket still connects)
    if (!matchId || !playerId) {
        console.warn("No matchId or playerId present on window. Make sure your template provides AUTH_USER_ID and HOUSE_ID/MATCH_ID.");
    }

    let count = 3;
    const timer = setInterval(() => {
        count--;
        if (count > 0) {
            countEl.textContent = count;
        } else if (count === 0) {
            countEl.textContent = 'Game started!';
            setTimeout(() => {
                overlay.classList.add('fade-out');
                board.removeAttribute('aria-hidden');
                board.classList.add('active');
                setTimeout(() => overlay.style.display = 'none', 500);
            }, 700);
        }
    }, 1000);

    // ===== Settings Modal logic =====
    const modal = document.getElementById('settingsModal');
    const openBtn = document.getElementById('openSettings');
    const closeBtn = document.getElementById('closeSettings');
    const exitBtn = document.getElementById('exitGameBtn');

    openBtn.addEventListener('click', () => modal.classList.remove('hidden'));
    closeBtn.addEventListener('click', () => modal.classList.add('hidden'));

    // Redirect back to the house page
    exitBtn.addEventListener('click', async () => {
        try {
            exitBtn.disabled = true;
            const buttonText = exitBtn.querySelector('.button-text');
            if (buttonText) buttonText.textContent = "Exiting...";
            const exitUrl = window.EXIT_GAME_URL || "/exit_game";
            const resp = await fetch(exitUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await resp.json();
            if (resp.ok && data.ok) {
                window.location.href = data.redirect || (window.CREATE_HOUSE_URL || "/create_house");
            } else {
                console.error("Exit failed", data);
                alert("Could not exit game. Try again.");
                exitBtn.disabled = false;
                if (buttonText) buttonText.textContent = "Exit Game";
            }
        } catch (err) {
            console.error("Exit error", err);
            alert("Network error while exiting. Try again.");
            exitBtn.disabled = false;
            const buttonText = exitBtn.querySelector('.button-text');
            if (buttonText) buttonText.textContent = "Exit Game";
        }
    });

    // Close modal if user clicks outside of it
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.add('hidden');
    });


    // --------------------------
    // Socket: connect / join match
    // --------------------------
    socket.on('connect', () => {
        console.log('[SOCKET] connected', socket.id);
        console.log('[SOCKET] matchId:', matchId, 'playerId:', playerId, 'types:', typeof matchId, typeof playerId);
        if (matchId && playerId) {
            const joinData = { match_id: matchId, player_id: String(playerId) };
            console.log('[SOCKET] Emitting join_game with data:', joinData);
            socket.emit('join_game', joinData);
        } else if (window.HOUSE_CODE && playerId) {
            socket.emit('join_house', { house_code: window.HOUSE_CODE, auth_user_id: playerId });
        }
    });

    socket.on('disconnect', (reason) => {
        console.error('[SOCKET] disconnected, reason:', reason);
        console.trace('[SOCKET] Disconnect stack trace');
    });

    socket.on('error', (err) => console.error('[SOCKET] error', err));

    socket.on('match_snapshot', (snap) => {
        // render players on the grid (function defined below)
        console.log('[SNAPSHOT] Received match_snapshot', snap);
        
        // Check if our move was successful by comparing positions
        if (pendingMove && snap.players && snap.players[playerId]) {
            const newPos = snap.players[playerId].pos;
            console.log('[MOVE] Checking move success', { pendingMove, newPos });
            if (newPos && newPos[0] === pendingMove[0] && newPos[1] === pendingMove[1]) {
                // Move succeeded, consume the roll
                console.log('[MOVE] Move succeeded, consuming roll');
                lastRoll = null;
                pendingMove = null;
            } else {
                console.log('[MOVE] Move not yet confirmed or failed');
            }
        }
        
        renderSnapshot(snap);
    });

    // --------------------------
    // Roll + Move UI wiring
    // --------------------------
    const rollBtn = document.getElementById('rollBtn');

    let lastRoll = null; // server-provided roll until used
    let currentTurn = null; // current turn player id
    let pendingMove = null; 

    // Handle turn updates
    socket.on('turn_update', (data) => {
        console.log('[TURN] Turn update received', data);
        currentTurn = data.current_turn;
        updateRollButtonState();
    });

    function updateRollButtonState() {
        if (!rollBtn) return;
        const isMyTurn = currentTurn && String(currentTurn) === String(playerId);
        console.log('[TURN] Updating roll button state', { currentTurn, playerId, isMyTurn });
        rollBtn.disabled = !isMyTurn;
    }

    if (rollBtn) {
        rollBtn.addEventListener('click', () => {
            console.log('[ROLL] Roll button clicked');
            if (rollBtn.disabled) {
                console.log('[ROLL] Button is disabled, ignoring click');
                return;
            }
            rollBtn.disabled = true;
            console.log('[ROLL] Sending roll_request', { match_id: matchId, player_id: playerId });
            
            // Show full-screen dice popup
            if (diceRollPopup) {
                console.log('[ROLL] Showing dice popup');
                diceRollPopup.classList.remove('hidden');
                // Reset dice image animation
                if (diceRollImage) {
                    diceRollImage.style.animation = 'none';
                    setTimeout(() => {
                        diceRollImage.style.animation = 'diceSpin 0.5s ease-in-out';
                    }, 10);
                }
                // Hide number initially
                if (diceRollNumber) {
                    diceRollNumber.textContent = '';
                    diceRollNumber.classList.remove('show');
                }
            }
            
            if (!matchId || !playerId) {
                console.error('[ROLL] Missing match or player ID', { matchId, playerId });
                alert('Missing match or player ID. Cannot roll.');
                rollBtn.disabled = false;
                if (diceRollPopup) diceRollPopup.classList.add('hidden');
                return;
            }
            const rollData = { match_id: matchId, player_id: String(playerId) };
            console.log('[ROLL] Emitting roll_request with data:', rollData);
            console.log('[ROLL] Socket connected?', socket.connected);
            console.log('[ROLL] Socket id:', socket.id);
            
            socket.emit('roll_request', rollData, (response) => {
                console.log('[ROLL] Roll request acknowledgment:', response);
            });
            
            // Also listen for any errors
            socket.on('error', (error) => {
                console.error('[ROLL] Socket error after roll_request:', error);
            });
        });
    }

    socket.on('roll_result', (d) => {
        console.log('[ROLL] Received roll_result event', d);
        if (!d) {
            console.warn('[ROLL] No data in roll_result');
            return;
        }
        
        // Compare player IDs (handle both string and number)
        const receivedPlayerId = String(d.player_id || '');
        const currentPlayerId = String(playerId || '');
        console.log('[ROLL] Comparing player IDs', { 
            receivedPlayerId, 
            currentPlayerId, 
            receivedType: typeof d.player_id,
            currentType: typeof playerId,
            match: receivedPlayerId === currentPlayerId 
        });
        
        if (!d.player_id) {
            console.warn('[ROLL] No player_id in roll_result data');
            return;
        }
        
        if (receivedPlayerId !== currentPlayerId) {
            console.log('[ROLL] Roll result is not for this player, ignoring', {
                received: receivedPlayerId,
                current: currentPlayerId
            });
            return; // ensure it's our roll result
        }
        
        console.log('[ROLL] Player IDs match! Processing roll result...');
        
        console.log('[ROLL] This is our roll result, value:', d.value);
        
        // Clear any pending move when new roll happens
        pendingMove = null;
        
        // Set the roll value immediately (but don't show it yet)
        const rollValue = Number(d.value);
        console.log('[ROLL] Roll value parsed:', rollValue);
        
        // Wait 2 seconds, then reveal the number
        setTimeout(() => {
            console.log('[ROLL] Revealing number after 2 seconds:', rollValue);
            lastRoll = rollValue;
            console.log('[ROLL] lastRoll set to:', lastRoll);
            
            if (diceRollNumber) {
                diceRollNumber.textContent = rollValue;
                diceRollNumber.classList.add('show');
                console.log('[ROLL] Number displayed in popup');
            } else {
                console.error('[ROLL] diceRollNumber element not found!');
            }
            
            // Close popup after showing number for 1 second, then allow movement
            setTimeout(() => {
                console.log('[ROLL] Closing popup, user can now move');
                if (diceRollPopup) diceRollPopup.classList.add('hidden');
                console.log('[ROLL] lastRoll available for movement:', lastRoll);
                // User can now move on the board
            }, 1000);
        }, 2000);
    });

    socket.on('roll_failed', (d) => {
        console.warn('[ROLL] Roll failed event received', d);
        if (diceRollPopup) diceRollPopup.classList.add('hidden');
        updateRollButtonState();
        if (d && d.reason === 'not_your_turn') {
            console.log('[ROLL] Not your turn');
            alert('It is not your turn!');
        } else {
            const reason = d ? d.reason : 'unknown error';
            console.error('[ROLL] Roll failed with reason:', reason);
            alert('Roll failed: ' + reason);
        }
    });

    socket.on('player_rolled', (d) => {
        // broadcast of someone rolling — you can animate this
        console.log('player_rolled', d);
    });

    socket.on('move_failed', (d) => {
        console.warn('[MOVE] Move failed', d);
        console.log('[MOVE] Roll still available:', lastRoll);
        alert('Move failed: ' + (d.reason || 'invalid move'));
        // Clear pending move - roll is still available
        pendingMove = null;
    });

    // --------------------------
    // Board click => move_request
    // --------------------------
    // Use 'board' variable declared earlier as the board element
    board.addEventListener('click', (ev) => {
        const cell = ev.target.closest('.cell');
        if (!cell) {
            console.log('[MOVE] Click was not on a cell');
            return;
        }
        const domRow = Number(cell.dataset.row);
        const col = Number(cell.dataset.col);
        // flip Y because template rows start at top (r=0) while logic uses bottom-left (0,0)
        const logicalY = 9 - domRow;
        const logicalX = col;

        console.log('[MOVE] Cell clicked', { domRow, col, logicalX, logicalY, lastRoll });

        // require a roll before moving
        if (lastRoll === null) {
            console.warn('[MOVE] No roll available, cannot move');
            alert("You must roll first!");
            return;
        }

        if (!matchId || !playerId) {
            console.error('[MOVE] Missing match or player id', { matchId, playerId });
            alert("Missing match or player id; cannot send move.");
            return;
        }

        console.log('[MOVE] Sending move_request', {
            match_id: matchId,
            player_id: playerId,
            target: [logicalX, logicalY],
            steps_allowed: lastRoll
        });

        // Store pending move to check if it succeeds
        pendingMove = [logicalX, logicalY];
        
        socket.emit('move_request', {
            match_id: matchId,
            player_id: playerId,
            target: [logicalX, logicalY],
            steps_allowed: lastRoll
        });
        
        // Don't consume roll yet - wait for confirmation via snapshot
    });


    // --------------------------
    // Render helpers
    // --------------------------
    function renderSnapshot(snapshot) {
        if (!snapshot) return;
        // clear previous marks
        const cells = board.querySelectorAll('.cell');
        cells.forEach(c => {
            c.innerHTML = '';
            c.classList.remove('occupied');
        });

        const players = snapshot.players || {};
        for (const pid in players) {
            const info = players[pid];
            if (!info.pos) continue;
            const x = info.pos[0];
            const y = info.pos[1];
            // convert logical y -> DOM row index
            const domRow = 9 - y;
            const selector = `.cell[data-row="${domRow}"][data-col="${x}"]`;
            const cell = board.querySelector(selector);
            if (!cell) continue;
            
            // Create player marker with character image if available
            const playerMarker = document.createElement('div');
            playerMarker.className = 'player-marker';
            
            // Add character image if available
            if (info.image_path) {
                const charImg = document.createElement('img');
                // Convert database path to Flask static URL
                // Database has "img/characters/ditte.webp", Flask serves from /static/
                let imgPath = info.image_path;
                if (!imgPath.startsWith('/static/') && !imgPath.startsWith('http')) {
                    if (imgPath.startsWith('/')) {
                        imgPath = '/static' + imgPath;
                    } else {
                        imgPath = '/static/' + imgPath;
                    }
                }
                charImg.src = imgPath;
                charImg.alt = info.name || 'Player';
                charImg.className = 'player-character-img';
                playerMarker.appendChild(charImg);
            }
            
            // Add player label
            const label = document.createElement('div');
            label.className = 'player-label';
            label.textContent = pid === playerId ? 'You' : (info.name || 'P');
            playerMarker.appendChild(label);
            
            cell.appendChild(playerMarker);
            cell.classList.add('occupied');
        }
    }

    // minimal styling for player marker if not present in CSS
    const style = document.createElement('style');
    style.textContent = `
    .player-marker{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px}
    .player-character-img{width:40px;height:40px;object-fit:contain;border-radius:4px}
    .player-label{background:rgba(255,255,255,0.9);padding:2px 6px;border-radius:8px;font-size:10px;font-weight:600;color:#000}
    .cell.occupied{background:rgba(0,0,0,0.06)}
    `;
    document.head.appendChild(style);

});
