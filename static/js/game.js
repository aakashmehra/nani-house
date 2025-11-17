document.addEventListener('DOMContentLoaded', () => {
    // ===== Countdown logic (unchanged) =====
    const board = document.getElementById('board');
    const authUserId = window.AUTH_USER_ID || "";    // injected by Flask template
    const matchId = window.HOUSE_ID || window.MATCH_ID || null; // whichever you use
    const playerId = String(authUserId || "");
    const socket = io();
    let currentSnapshot = null; // latest snapshot from server
    let highlightedSet = new Set(); // set of 'x,y' strings for valid move targets

    // ===== Flash Message System =====
    const flashMessageEl = document.getElementById('flashMessage');
    const flashMessageText = document.getElementById('flashMessageText');
    let flashTimeout = null;

    function showFlashMessage(message, duration = 3000) {
        if (!flashMessageEl || !flashMessageText) return;
        
        // Clear any existing timeout
        if (flashTimeout) {
            clearTimeout(flashTimeout);
            flashTimeout = null;
        }

        // Set message text
        flashMessageText.textContent = message;
        
        // Show message
        flashMessageEl.classList.remove('hidden');
        
        // Auto-hide after duration
        flashTimeout = setTimeout(() => {
            flashMessageEl.classList.add('hidden');
            flashTimeout = null;
        }, duration);
    }


    // small safety: if no match/player id, warn (socket still connects)
    if (!matchId || !playerId) {
        console.warn("No matchId or playerId present on window. Make sure your template provides AUTH_USER_ID and HOUSE_ID/MATCH_ID.");
    }
    
    // Activate board immediately (countdown removed)
    if (board) {
        board.removeAttribute('aria-hidden');
        board.classList.add('active');
    }

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
            const exitText = exitBtn.querySelector('.exit-button-text');
            if (exitText) exitText.textContent = "Exiting...";
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
                showFlashMessage("Could not exit game. Try again.");
                exitBtn.disabled = false;
                if (exitText) exitText.textContent = "Exit Game";
            }
        } catch (err) {
            console.error("Exit error", err);
            showFlashMessage("Network error while exiting. Try again.");
            exitBtn.disabled = false;
            const exitText = exitBtn.querySelector('.exit-button-text');
            if (exitText) exitText.textContent = "Exit Game";
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
        if (matchId && playerId) {
            socket.emit('join_game', { match_id: matchId, player_id: playerId });
        } else if (window.HOUSE_CODE && playerId) {
            // fallback: if you used HOUSE_CODE instead of match id
            socket.emit('join_house', { house_code: window.HOUSE_CODE, auth_user_id: playerId });
        }
    });

    socket.on('disconnect', () => console.log('[SOCKET] disconnected'));

    socket.on('error', (err) => console.error('[SOCKET] error', err));

    socket.on('match_snapshot', (snap) => {
        // render players on the grid (function defined below)
        console.log('match_snapshot', snap);
        currentSnapshot = snap;
        renderSnapshot(snap);
    });

    // --------------------------
    // Roll + Move UI wiring
    // --------------------------
    const rollBtn = document.getElementById('rollBtn');
    const turnIndicator = document.getElementById('turnIndicator');
    const attackBtn = document.getElementById('attackBtn');
    const itemsBtn = document.getElementById('itemsBtn'); // renamed from inventoryBtn
    const abilityBtn = document.getElementById('abilityBtn');
    const gameActionButtons = document.getElementById('gameActionButtons');
    const rollPlayerName = document.getElementById('rollPlayerName');
    const rollPlayerValue = document.getElementById('rollPlayerValue');
    const healthFill = document.getElementById("health-fill")

    let lastRoll = null; // server-provided roll until used
    let rollDisplayTimeout = null; // timeout for hiding roll display
    let attackMode = false;
    let isZoomedOut = false; // track zoom state
    const boardWrap = document.querySelector('.board-wrap');

    if (rollBtn) {
        rollBtn.addEventListener('click', () => {
            rollBtn.disabled = true;
            if (!matchId || !playerId) {
                showFlashMessage('Missing match or player ID. Cannot roll.');
                return;
            }
            // Zoom out will be handled by roll_result socket event
            socket.emit('roll_request', { match_id: matchId, player_id: playerId });
        });
    }

    if (attackBtn){
        attackBtn.addEventListener('click', () => {
            attackBtn.disabled = true;
            attackMode = true;
            board.style.pointerEvents = 'pointer';
            if (!matchId || !playerId) {
                showFlashMessage('Missing match or player ID. Cannot roll.');
                attackMode = false;
                if (gameActionButtons) {
                    gameActionButtons.classList.remove('hidden');
                }
                return;
            }
            // Zoom out when clicking attack to see the board
            zoomOut();
            showFlashMessage("Choose a player to Attack!")
            socket.emit('attackable_players', { match_id: matchId, player_id: playerId })
        });
    }


    // Items button (renamed from Inventory)
    if (itemsBtn) {
        itemsBtn.addEventListener('click', () => {
            // TODO: Implement items functionality
            console.log('Items button clicked');
        });
    }

    // Ability button (new, do nothing for now)
    if (abilityBtn) {
        abilityBtn.addEventListener('click', () => {
            // TODO: Implement ability functionality
            console.log('Ability button clicked');
        });
    }

    socket.on('turn_update', (d) => {
        // Clear any pending timeout when turn changes
        if (rollDisplayTimeout) {
            clearTimeout(rollDisplayTimeout);
            rollDisplayTimeout = null;
        }
        
        // Zoom in on the player whose turn it is
        const turnPlayerId = d.turn;
        zoomInOnPlayer(turnPlayerId);
        
        if(d.turn === playerId){
            rollBtn.disabled = false;
            attackBtn.disabled = false;
            itemsBtn.disabled = false;
            abilityBtn.disabled = false;
            // Show action buttons when it's user's turn
            if (gameActionButtons) {
                gameActionButtons.classList.remove('hidden');
            }
            turnIndicator.textContent = "Your Turn";
        } else {
            rollBtn.disabled = true;
            attackBtn.disabled = true;
            itemsBtn.disabled = true;
            abilityBtn.disabled = true;
            // Hide action buttons when it's not user's turn
            if (gameActionButtons) {
                gameActionButtons.classList.add('hidden');
            }
            turnIndicator.textContent = `${d.user}'s Turn`;
        }
    });

    socket.on('health_update', (d) => {
        console.log(d)
        // Zoom out whenever ANY player attacks (health update indicates an attack happened)
        if (d.attacker && d.target) {
            zoomOut();
        }
        
        if(attackMode){
            showFlashMessage(`${d.attacker} attacked ${d.target}!`)
            attackMode = false;
        }
        if (d.user_id === playerId){
            if (d.current_health <= 0){
                d.current_health = 0;
            }
            let percent = (d.current_health/d.max_health) * 100;
            healthFill.style.width = percent + "%";
        }
    });

    socket.on('attackable_players_result', (d) => {
        if (d.player_id === playerId){
            if (d.success === false){
                showFlashMessage("No Players in range")
                attackMode = false;
            }
            highlightPositions(d.attacks)
        }
    });

    socket.on('roll_result', (d) => {
        if (!d) return;
        // Determine who rolled (support multiple possible property names)
        const rollerId = d.player_id || d.playerId || d.player || d.user_id;

        // Zoom out whenever ANY player rolls
        zoomOut();

        // Clear any existing timeout
        if (rollDisplayTimeout) {
            clearTimeout(rollDisplayTimeout);
            rollDisplayTimeout = null;
        }

        // Show ALL players' rolls in bottom right (including our own)
        if (rollPlayerName && rollPlayerValue) {
            rollPlayerName.textContent = d.user || 'Player';
            rollPlayerValue.textContent = d.value;
            rollPlayerName.classList.remove('hidden');
            rollPlayerValue.classList.remove('hidden');
            
            // Hide after 2.5 seconds
            rollDisplayTimeout = setTimeout(() => {
                if (rollPlayerName) rollPlayerName.classList.add('hidden');
                if (rollPlayerValue) rollPlayerValue.classList.add('hidden');
            }, 2500);
        }

        // If this roll is not for us, do not enable movement
        if (!rollerId || String(rollerId) !== playerId) {
            // Prevent local click actions for non-rollers
            board.style.pointerEvents = 'none';
            return;
        }

        // It's our roll — hide action buttons immediately and allow moves
        board.style.pointerEvents = 'auto';
        lastRoll = Number(d.value);
        
        // Hide action buttons immediately after roll
        if (gameActionButtons) {
            gameActionButtons.classList.add('hidden');
        }
        
        if (rollBtn) rollBtn.disabled = true;

        try {
            const playerPos = getPlayerPosition(playerId);
            if (playerPos && lastRoll > 0) {
                const reachable = computeReachablePositions(playerPos, lastRoll);
                highlightPositions(reachable);
            }
        } catch (e) {
            console.error('Error computing reachable positions', e);
        }
    });
    // Use 'board' variable declared earlier as the board element
    board.addEventListener('click', (ev) => {
        const cell = ev.target.closest('.cell');
        if (!cell) return;
        const domRow = Number(cell.dataset.row);
        const col = Number(cell.dataset.col);
        // flip Y because template rows start at top (r=0) while logic uses bottom-left (0,0)
        const logicalY = 9 - domRow;
        const logicalX = col;


        if (attackMode){
            const key = `${logicalX},${logicalY}`;
            if (!highlightedSet.has(key)) {
                showFlashMessage('Not in Range');
                return;
            }
            console.log(key)
            socket.emit("attack_request", {
                match_id: matchId,
                player_id: playerId,
                target: [logicalX, logicalY],
            });
            // Zoom will be handled by turn_update when next turn starts
        }
        // require a roll before moving
        if (lastRoll === null) {
            showFlashMessage("You must roll first!");
            return;
        }

        if (!matchId || !playerId) {
            showFlashMessage("Missing match or player id; cannot send move.");
            return;
        }

        // Only allow moving to highlighted/allowed cells
        const key = `${logicalX},${logicalY}`;
        if (!highlightedSet.has(key)) {
            showFlashMessage('Move out of bounds');
            return;
        }

        socket.emit('move_request', {
            match_id: matchId,
            player_id: playerId,
            target: [logicalX, logicalY],
            steps_allowed: lastRoll
        });

        // consume the roll locally and clear highlights
        lastRoll = null;
        clearHighlights();
        // Clear any pending timeout
        if (rollDisplayTimeout) {
            clearTimeout(rollDisplayTimeout);
            rollDisplayTimeout = null;
        }
        // Hide action buttons when move is made (if still visible)
        if (gameActionButtons) {
            gameActionButtons.classList.add('hidden');
        }
        
        // Zoom will be handled by turn_update when next turn starts
    });


    // --------------------------
    // Camera/Zoom functions
    // --------------------------
    function zoomInOnPlayer(playerIdToZoom) {
        if (!boardWrap || !currentSnapshot || !board) return;
        
        const playerPos = getPlayerPosition(playerIdToZoom);
        if (!playerPos) {
            // If position not found, just reset zoom
            resetZoom();
            return;
        }
        
        isZoomedOut = false;
        
        // Convert logical position to DOM cell position
        const x = playerPos[0];
        const y = playerPos[1];
        const domRow = 9 - y;
        
        // Get the cell element
        const cell = board.querySelector(`.cell[data-row="${domRow}"][data-col="${x}"]`);
        if (!cell) {
            resetZoom();
            return;
        }

        // Calculate cell position as percentage of board (0-1)
        // Board is 10x10, so each cell is 10% of board
        const cellXPercent = (x + 0.5) / 10; // center of cell
        const cellYPercent = (domRow + 0.5) / 10; // center of cell


        // Scale up 3x
        const scale = 3;
        
        // Calculate translation to center the cell
        // We need to move the cell to the center (50%) of the viewport
        // After scaling, the board is 3x larger, so we need to account for that
        const translateXPercent = (0.5 - cellXPercent) * 100;
        const translateYPercent = (0.5 - cellYPercent) * 100;

        boardWrap.style.transform = `scale(${scale}) translate(${translateXPercent}%, ${translateYPercent}%)`;
    }
    
    function zoomOut() {
        if (!boardWrap) return;
        isZoomedOut = true;
        // Reset zoom to show full board
        boardWrap.style.transform = 'scale(1) translate(0, 0)';
    }
    
    function resetZoom() {
        if (!boardWrap) return;
        isZoomedOut = false;
        boardWrap.style.transform = 'scale(1) translate(0, 0)';
    }

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

            const pos = info.position;
            if (!pos) continue;

            const x = pos[0];
            const y = pos[1];

            // convert logical y -> DOM row index (same as your original)
            const domRow = 9 - y;
            const selector = `.cell[data-row="${domRow}"][data-col="${x}"]`;
            const cell = board.querySelector(selector);
            if (!cell) continue;

            // Create player container
            const playerContainer = document.createElement('div');
            playerContainer.className = 'player-container';

            // Create username bubble (speech bubble with arrow pointing down)
            const usernameBubble = document.createElement('div');
            usernameBubble.className = 'username-bubble';
            const usernameText = document.createElement('span');
            usernameText.className = 'username-text';
            usernameText.textContent = info.user || 'Player';
            usernameBubble.appendChild(usernameText);
            playerContainer.appendChild(usernameBubble);

            // Create character image container
            const characterContainer = document.createElement('div');
            characterContainer.className = 'character-container';
            
            // Create character image
            const characterImg = document.createElement('img');
            characterImg.className = 'character-image';
            // Construct image path from character name
            // Character images are stored as: img/characters/{name_lowercase}.webp
            const characterName = (info.name || 'default').toLowerCase();
            // Handle special case for "Ishada" which might be capitalized differently
            const imageName = characterName === 'ishada' ? 'Ishada' : characterName;
            characterImg.src = `/static/img/characters/${imageName}.webp`;
            characterImg.alt = info.name || 'Character';
            characterImg.onerror = function() {
                // Fallback if image doesn't exist - show first letter of character name
                this.style.display = 'none';
                const fallback = document.createElement('div');
                fallback.className = 'character-fallback';
                fallback.textContent = (info.name || 'C').charAt(0).toUpperCase();
                if (!characterContainer.querySelector('.character-fallback')) {
                    characterContainer.appendChild(fallback);
                }
            };
            
            characterContainer.appendChild(characterImg);
            playerContainer.appendChild(characterContainer);

            cell.appendChild(playerContainer);
            cell.classList.add('occupied');

        }

        // After re-rendering board, re-apply highlights if we still have a pending roll
        if (lastRoll !== null) {
            const playerPos = getPlayerPosition(playerId);
            if (playerPos) {
                const reachable = computeReachablePositions(playerPos, lastRoll);
                highlightPositions(reachable);
            }
        }
    }


    // Styling for player container, username bubble, and character image
    const style = document.createElement('style');
    style.textContent = `
    .player-container {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%;
        height: 100%;
        pointer-events: none;
    }
    
    .username-bubble {
        position: absolute;
        top: -25px;
        background: rgba(255, 255, 255, 0.95);
        color: #333;
        padding: 4px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 600;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        z-index: 10;
        font-family: 'Sansation', sans-serif;
    }
    
    .username-bubble::after {
        content: '';
        position: absolute;
        bottom: -6px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-top: 6px solid rgba(255, 255, 255, 0.95);
    }
    
    .username-text {
        display: block;
    }
    
    .character-container {
        position: relative;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .character-image {
        width: 100%;
        height: 100%;
        object-fit: contain;
        max-width: 80%;
        max-height: 80%;
    }
    
    .character-fallback {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 50%;
        font-size: 20px;
        font-weight: bold;
        color: #333;
    }
    
    .cell.occupied {
        background: rgba(0, 0, 0, 0.06);
    }
    `;
    document.head.appendChild(style);

    // --------------------------
    // Highlighting & movement helpers
    // --------------------------
    function positionKey(x, y) {
        return `${x},${y}`;
    }

    function getPlayerPosition(pid) {
        if (!currentSnapshot || !currentSnapshot.players) return null;
        const info = currentSnapshot.players[pid] || currentSnapshot.players[String(pid)];
        if (!info) return null;
        return info.position || null;
    }

    function computeReachablePositions(startPos, steps) {
        // Grid limits hard-coded to 10x10 (0..9)
        const maxY = 9;
        const maxX = 9;
        let x = Number(startPos[0]);
        let y = Number(startPos[1]);
        const results = [];

        for (let s = 0; s < steps; s++) {
            const rowNumber = y + 1; // bottom row is 1
            const dir = (rowNumber % 2 === 1) ? 1 : -1; // odd -> right, even -> left
            let nextX = x + dir;
            let nextY = y;

            // If horizontal move would go out of bounds, move up one row instead (stay same x)
            if (nextX < 0 || nextX > maxX) {
                nextY = y + 1;
                // If we've moved off the top of the grid, stop further movement
                if (nextY > maxY) break;
                // x stays the same when moving up as per the rule
                x = x; // no-op for clarity
                y = nextY;
                results.push([x, y]);
                continue;
            }

            // Normal horizontal step
            x = nextX;
            y = nextY;
            results.push([x, y]);
        }

        return results;
    }

    function clearHighlights() {
        highlightedSet.clear();
        const cells = board.querySelectorAll('.cell');
        cells.forEach(c => c.classList.remove('highlight'));
    }

    function highlightPositions(list) {
        clearHighlights();
        if (!Array.isArray(list)) return;
        list.forEach(p => {
            const x = p[0];
            const y = p[1];
            // convert logical y->domRow
            const domRow = 9 - y;
            const selector = `.cell[data-row="${domRow}"][data-col="${x}"]`;
            const cell = board.querySelector(selector);
            if (!cell) return;
            cell.classList.add('highlight');
            highlightedSet.add(positionKey(x, y));
        });
    }

    // add highlight style
    const extraStyle = document.createElement('style');
    extraStyle.textContent = `.cell.highlight{outline:3px solid rgba(255,200,30,0.9);box-shadow:0 0 6px rgba(255,200,30,0.6) inset}`;
    document.head.appendChild(extraStyle);

});
