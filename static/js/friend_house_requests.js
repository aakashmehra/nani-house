(function () {
    const authUserId = window.AUTH_USER_ID;
    const pageContext = window.PAGE_CONTEXT || '';
    if (!authUserId || !pageContext) {
        return;
    }

    const socket = io();
    const isJoinPage = pageContext === 'join_house';
    const isCreatePage = pageContext === 'create_house';
    const isCreator = String(window.IS_HOUSE_CREATOR).toLowerCase() === 'true';

    const joinUI = isJoinPage ? {
        button: document.getElementById('friendOnlineButton'),
        badge: document.getElementById('friendOnlineBadge'),
        modal: document.getElementById('friendOnlineModal'),
        overlay: document.getElementById('friendOnlineOverlay'),
        close: document.getElementById('friendOnlineClose'),
        list: document.getElementById('friendOnlineList'),
        empty: document.getElementById('friendOnlineEmpty'),
        feedback: document.getElementById('friendOnlineFeedback')
    } : null;

    const createUI = (isCreatePage && isCreator) ? {
        button: document.getElementById('friendRequestButton'),
        badge: document.getElementById('friendRequestBadge'),
        modal: document.getElementById('friendRequestModal'),
        overlay: document.getElementById('friendRequestOverlay'),
        close: document.getElementById('friendRequestClose'),
        list: document.getElementById('friendRequestList'),
        empty: document.getElementById('friendRequestEmpty')
    } : null;

    const friendRequestState = new Map();

    function openModal(ui) {
        if (!ui || !ui.modal) return;
        ui.modal.classList.remove('hidden');
    }

    function closeModal(ui) {
        if (!ui || !ui.modal) return;
        ui.modal.classList.add('hidden');
    }

    function bindModal(ui, onOpen) {
        if (!ui) return;
        if (ui.button) {
            ui.button.addEventListener('click', () => {
                openModal(ui);
                if (typeof onOpen === 'function') {
                    onOpen();
                }
            });
        }
        [ui.close, ui.overlay].forEach((el) => {
            if (el) el.addEventListener('click', () => closeModal(ui));
        });
    }

    function setJoinFeedback(message, type = 'info') {
        if (!joinUI || !joinUI.feedback) return;
        joinUI.feedback.textContent = message || '';
        joinUI.feedback.dataset.status = type;
        joinUI.feedback.classList.toggle('hidden', !message);
    }

    function updateOnlineBadge(count) {
        if (!joinUI || !joinUI.badge) return;
        if (count > 0) {
            joinUI.badge.textContent = `(${count})`;
            joinUI.badge.classList.remove('hidden');
        } else {
            joinUI.badge.classList.add('hidden');
        }
    }

    function setJoinEmptyState(hasItems) {
        if (!joinUI || !joinUI.empty) return;
        joinUI.empty.classList.toggle('hidden', hasItems);
    }

    function renderFriendHouses(houses) {
        if (!joinUI || !joinUI.list) return;
        joinUI.list.innerHTML = '';
        houses.forEach((house) => {
            const card = document.createElement('div');
            card.className = 'friend-online-card';

            const info = document.createElement('div');
            info.className = 'friend-online-info';
            info.innerHTML = `
                <div class="friend-online-name">${house.friend_username}</div>
                <div class="friend-online-meta">Code: ${house.house_code}</div>
                <div class="friend-online-meta">${house.current_players}/${house.max_players} players</div>
            `;

            const actionBtn = document.createElement('button');
            actionBtn.type = 'button';
            actionBtn.className = 'friend-online-send';
            actionBtn.dataset.targetUserId = house.friend_user_id;
            actionBtn.dataset.houseCode = house.house_code;
            actionBtn.innerHTML = `
                <img src="/static/img/buttons/button_primary.webp" alt="Request" class="friend-online-send-bg">
                <span class="friend-online-send-text">Request</span>
            `;

            card.appendChild(info);
            card.appendChild(actionBtn);
            joinUI.list.appendChild(card);
        });

        updateOnlineBadge(houses.length);
        setJoinEmptyState(houses.length > 0);
    }

    function loadFriendHouses() {
        fetch('/api/friend-houses')
            .then((resp) => resp.json())
            .then((data) => {
                if (!data.success) {
                    setJoinFeedback(data.error || 'Unable to load friends.', 'error');
                    updateOnlineBadge(0);
                    setJoinEmptyState(false);
                    return;
                }
                renderFriendHouses(data.houses || []);
                setJoinFeedback('');
            })
            .catch((err) => {
                console.error('[friend houses] fetch error', err);
                setJoinFeedback('Unable to load friend houses right now.', 'error');
                updateOnlineBadge(0);
            });
    }

    function updateRequestBadge() {
        if (!createUI || !createUI.badge || !createUI.list) return;
        const count = createUI.list.children.length;
        createUI.badge.textContent = `(${count})`;
        createUI.badge.classList.toggle('hidden', count <= 0);
    }

    function setRequestEmptyState(hasItems) {
        if (!createUI || !createUI.empty) return;
        createUI.empty.classList.toggle('hidden', hasItems);
    }

    function addRequestItem(data) {
        if (!createUI || !createUI.list) return;
        const li = document.createElement('li');
        li.className = 'friend-request-item';
        li.dataset.requesterUserId = data.requester_user_id;
        li.innerHTML = `
            <div class="friend-request-text">
                <strong>${data.requester_username}</strong> wants to join your room.
            </div>
            <div class="friend-request-actions">
                <button type="button" data-action="accept">Accept</button>
                <button type="button" data-action="reject">Reject</button>
            </div>
        `;
        friendRequestState.set(String(data.requester_user_id), li);
        createUI.list.appendChild(li);
        updateRequestBadge();
        setRequestEmptyState(createUI.list.children.length > 0);
    }

    function removeRequestItem(requesterUserId) {
        if (!createUI || !createUI.list) return;
        const key = String(requesterUserId);
        const node = friendRequestState.get(key);
        if (node) {
            node.remove();
            friendRequestState.delete(key);
        }
        updateRequestBadge();
        setRequestEmptyState(createUI.list.children.length > 0);
    }

    function respondToRequest(requesterUserId, decision) {
        socket.emit('house_friend_request_response', {
            requester_user_id: requesterUserId,
            decision
        });
    }

    socket.on('connect', () => {
        socket.emit('register_user', { user_id: authUserId });
        if (joinUI) {
            loadFriendHouses();
        }
    });

    socket.on('register_user_ack', (data) => {
        if (!data.success) {
            console.warn('[friend houses] register failed', data.error);
        }
    });

    bindModal(joinUI, loadFriendHouses);
    bindModal(createUI);

    if (joinUI && joinUI.list) {
        joinUI.list.addEventListener('click', (event) => {
            const button = event.target.closest('.friend-online-send');
            if (!button) return;
            const targetUserId = button.dataset.targetUserId;
            const houseCode = button.dataset.houseCode;
            button.disabled = true;
            socket.emit('house_friend_request_send', {
                target_user_id: targetUserId,
                house_code: houseCode
            });
            setJoinFeedback('Sending request...', 'info');
        });
    }

    if (createUI && createUI.list) {
        createUI.list.addEventListener('click', (event) => {
            const actionBtn = event.target.closest('button[data-action]');
            if (!actionBtn) return;
            const item = actionBtn.closest('.friend-request-item');
            if (!item) return;
            const requesterUserId = item.dataset.requesterUserId;
            actionBtn.disabled = true;
            respondToRequest(requesterUserId, actionBtn.dataset.action);
        });
    }

    socket.on('house_friend_request_status', (payload) => {
        if (!joinUI) return;
        if (!payload.success) {
            setJoinFeedback(payload.error || 'Unable to send request.', 'error');
            loadFriendHouses();
            return;
        }
        setJoinFeedback('Request sent! Waiting for your friend to respond.', 'success');
        loadFriendHouses();
    });

    socket.on('house_friend_request_result', (payload) => {
        if (!joinUI) return;
        if (payload.status === 'accepted') {
            setJoinFeedback('Request accepted! Redirecting...', 'success');
            const redirectUrl = payload.redirect_url || '/create_house';
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 800);
        } else if (payload.status === 'rejected') {
            setJoinFeedback('Request was declined.', 'error');
            loadFriendHouses();
        } else if (payload.status === 'cancelled') {
            setJoinFeedback('Request could not be processed.', 'error');
            loadFriendHouses();
        }
    });

    socket.on('house_friend_request_received', (payload) => {
        if (!createUI) return;
        addRequestItem(payload);
    });

    socket.on('house_friend_request_update', (payload) => {
        if (!createUI) return;
        if (!payload.success) {
            console.warn('[friend houses] response error', payload.error);
            removeRequestItem(payload.requester_user_id);
            return;
        }
        removeRequestItem(payload.requester_user_id);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        if (joinUI && joinUI.modal && !joinUI.modal.classList.contains('hidden')) {
            closeModal(joinUI);
        }
        if (createUI && createUI.modal && !createUI.modal.classList.contains('hidden')) {
            closeModal(createUI);
        }
    });
})();

