document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('drawingCanvas');
    const ctx = canvas.getContext('2d');
    const drawingWrapper = document.querySelector('.drawing-wrapper');
    const drawingBoard = document.querySelector('.drawing-board-bg');
    const gameTitle = document.getElementById('gameTitle');
    const timerDisplay = document.getElementById('timerDisplay');
    const taskDisplay = document.getElementById('taskDisplay');
    const clearBtn = document.getElementById('clearBtn');
    const sendBtn = document.getElementById('sendBtn');
    const popupModal = document.getElementById('popupModal');
    const popupChecking = document.getElementById('popupChecking');
    const popupResults = document.getElementById('popupResults');
    const scoreDisplay = document.getElementById('scoreDisplay');
    const taskResult = document.getElementById('taskResult');
    const playAgainBtn = document.getElementById('playAgainBtn');
    
    let isDrawing = false;
    let currentTask = '';
    let timeLeft = 20;
    let timerInterval = null;
    let gameActive = false;
    const checkingPopup = document.getElementById('checkingPopup');
    
    // Set canvas size to match the drawing board image exactly
    function resizeCanvas() {
        // Wait for image to load
        const setupCanvas = () => {
            // Get the displayed size of the image
            const imgRect = drawingBoard.getBoundingClientRect();
            const displayWidth = imgRect.width;
            const displayHeight = imgRect.height;
            
            // Set canvas to match displayed image size exactly
            canvas.width = displayWidth;
            canvas.height = displayHeight;
            
            // Set canvas display size to match exactly
            canvas.style.width = displayWidth + 'px';
            canvas.style.height = displayHeight + 'px';
            
            // Ensure canvas is centered (CSS handles this with transform)
            // But we also need to ensure it aligns with image position
            const wrapperRect = drawingWrapper.getBoundingClientRect();
            const imgLeft = imgRect.left - wrapperRect.left;
            const imgTop = imgRect.top - wrapperRect.top;
            
            // Reset transform to use CSS centering
            canvas.style.transform = 'translate(-50%, -50%)';
            canvas.style.top = '50%';
            canvas.style.left = '50%';
            
            // Set drawing style
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
        };
        
        // Wait for image to load
        if (drawingBoard.complete) {
            // Small delay to ensure layout is ready
            setTimeout(setupCanvas, 10);
        } else {
            drawingBoard.addEventListener('load', () => {
                setTimeout(setupCanvas, 10);
            });
        }
    }
    
    // Initialize canvas
    resizeCanvas();
    window.addEventListener('resize', () => {
        setTimeout(resizeCanvas, 50);
    });
    
    // Get random task from server
    async function getTask() {
        try {
            const response = await fetch('/drawing_game/task');
            const data = await response.json();
            currentTask = data.task;
            taskDisplay.textContent = currentTask;
            return currentTask;
        } catch (error) {
            console.error('Error fetching task:', error);
            // Fallback task
            const fallbackTasks = [
                'Draw a simple robot',
                'Draw a pencil',
                'Draw a cartoon cat head',
                'Draw a paper airplane',
                'Draw a balloon'
            ];
            currentTask = fallbackTasks[Math.floor(Math.random() * fallbackTasks.length)];
            taskDisplay.textContent = currentTask;
            return currentTask;
        }
    }
    
    // Start the game
    async function startGame() {
        // Reset canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Get new task
        await getTask();
        
        // Reset timer
        timeLeft = 20;
        timerDisplay.textContent = timeLeft;
        
        // Disable send button
        sendBtn.disabled = true;
        
        // Hide popup modal
        popupModal.classList.add('hidden');
        
        // Start timer
        gameActive = true;
        startTimer();
    }
    
    // Timer countdown
    function startTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
        }
        
        timerInterval = setInterval(() => {
            timeLeft--;
            timerDisplay.textContent = timeLeft;
            
            // Warning when time is running out
            if (timeLeft <= 3) {
                timerDisplay.style.color = '#ff0000';
                timerDisplay.style.animation = 'pulse 0.5s infinite';
            }
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                timerInterval = null;
                endGame();
            }
        }, 1000);
    }
    
    // End game when time runs out
    function endGame() {
        gameActive = false;
        timerDisplay.textContent = '0';
        timerDisplay.style.animation = 'none';
        
        // Auto-submit if there's a drawing
        if (hasDrawing()) {
            submitDrawing();
        } else {
            // Show timeout message
            showResults(null, 'Time\'s up! No drawing submitted.');
        }
    }
    
    // Check if canvas has any drawing
    function hasDrawing() {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        
        // Check if any pixel is not transparent/white
        for (let i = 3; i < data.length; i += 4) {
            if (data[i] > 10) { // Alpha channel > 10
                return true;
            }
        }
        return false;
    }
    
    // Get mouse/touch position relative to canvas
    function getEventPos(e) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        
        if (e.touches && e.touches.length > 0) {
            return {
                x: (e.touches[0].clientX - rect.left) * scaleX,
                y: (e.touches[0].clientY - rect.top) * scaleY
            };
        }
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    }
    
    // Drawing functions
    function startDraw(e) {
        if (!gameActive) return;
        e.preventDefault();
        isDrawing = true;
        const pos = getEventPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        
        // Enable send button once drawing starts
        if (hasDrawing() || true) {
            sendBtn.disabled = false;
        }
    }
    
    function draw(e) {
        if (!isDrawing || !gameActive) return;
        e.preventDefault();
        const pos = getEventPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        
        // Enable send button
        sendBtn.disabled = false;
    }
    
    function stopDraw(e) {
        if (!isDrawing) return;
        e.preventDefault();
        isDrawing = false;
        ctx.beginPath();
    }
    
    // Mouse events
    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDraw);
    canvas.addEventListener('mouseout', stopDraw);
    
    // Touch events
    canvas.addEventListener('touchstart', startDraw);
    canvas.addEventListener('touchmove', draw);
    canvas.addEventListener('touchend', stopDraw);
    canvas.addEventListener('touchcancel', stopDraw);
    
    // Clear button
    clearBtn.addEventListener('click', () => {
        if (!gameActive) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        sendBtn.disabled = !hasDrawing();
    });
    
    // Submit drawing
    async function submitDrawing() {
        if (!hasDrawing()) {
            alert('Please draw something first!');
            return;
        }
        
        // Stop timer
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        gameActive = false;
        
        // Disable buttons
        sendBtn.disabled = true;
        clearBtn.disabled = true;
        
        // Show checking popup
        popupModal.classList.remove('hidden');
        popupChecking.classList.remove('hidden');
        popupResults.classList.add('hidden');
        
        // Convert canvas to data URL WITHOUT white background (transparent PNG for OpenAI)
        const imageData = canvas.toDataURL('image/png');
        
        // Image will be auto-saved on the server
        
        // Send to server for rating
        try {
            const response = await fetch('/drawing_game/rate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageData,
                    task: currentTask
                })
            });
            
            const result = await response.json();
            
            // Show results in popup
            popupChecking.classList.add('hidden');
            popupResults.classList.remove('hidden');
            
            if (result.success && result.rating !== undefined) {
                showResults(result.rating, currentTask);
            } else {
                showResults(null, currentTask, result.error || 'Could not get rating');
            }
        } catch (error) {
            console.error('Error submitting drawing:', error);
            popupChecking.classList.add('hidden');
            popupResults.classList.remove('hidden');
            showResults(null, currentTask, 'Error submitting drawing. Please try again.');
        }
        
        // Re-enable buttons
        clearBtn.disabled = false;
    }
    
    // Send button
    sendBtn.addEventListener('click', submitDrawing);
    
    // Show results
    function showResults(rating, task, error = null) {
        taskResult.textContent = task;
        
        if (rating !== null) {
            scoreDisplay.textContent = `${rating}/10`;
            scoreDisplay.style.color = rating >= 7 ? '#4CAF50' : rating >= 4 ? '#FF9800' : '#F44336';
        } else {
            scoreDisplay.textContent = error || 'N/A';
            scoreDisplay.style.color = '#F44336';
            scoreDisplay.style.fontSize = 'clamp(1.2rem, 3vw, 1.6rem)';
        }
        
        // Popup is already visible, just showing results now
    }
    
    // Play again button
    playAgainBtn.addEventListener('click', () => {
        // Hide popup
        popupModal.classList.add('hidden');
        
        // Reset timer display
        timerDisplay.style.color = '#ff4444';
        timerDisplay.style.animation = 'pulse 1s infinite';
        
        startGame();
    });
    
    // Start the game on page load
    startGame();
});

