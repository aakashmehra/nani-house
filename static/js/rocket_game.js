// Rocket Game JavaScript

let gameState = {
    isPlaying: false,
    timeLeft: 30,
    taps: 0,
    height: 0,
    timerInterval: null,
    rocketPosition: 0,
    startPosition: 0,
    backgroundOffset: 0,
    gameStarted: false,
    birdSpawnInterval: null,
    activeBirds: []
};

const BIRD_IMAGES = [
    '/static/img/minigame_images/rocket_game_assets/birds/bird-1.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-2.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-3.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-4.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-5.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-6.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-7.webp',
    '/static/img/minigame_images/rocket_game_assets/birds/bird-8.webp'
];

// DOM elements
const rocketWrapper = document.getElementById('rocketWrapper');
const rocketImage = document.getElementById('rocketImage');
const rocketTapButton = document.getElementById('rocketTapButton');
const rocketTimer = document.getElementById('rocketTimer');
const rocketPopupModal = document.getElementById('rocketPopupModal');
const rocketHeightDisplay = document.getElementById('rocketHeightDisplay');
const rocketTapsDisplay = document.getElementById('rocketTapsDisplay');
const rocketPlayAgainBtn = document.getElementById('rocketPlayAgainBtn');
const birdsContainer = document.getElementById('birdsContainer');

// Initialize game
function initGame() {
    // Reset game state
    gameState.isPlaying = false;
    gameState.timeLeft = 15;
    gameState.taps = 0;
    gameState.height = 0;
    gameState.rocketPosition = 0;
    gameState.backgroundOffset = 0;
    gameState.gameStarted = false;
    
    // Reset UI
    rocketTimer.textContent = '15';
    rocketImage.src = '/static/img/minigame_images/rocket_game_assets/rocket_start_pos.webp';
    rocketPopupModal.classList.add('hidden');
    
    // Reset background position
    const backyardElement = document.querySelector('.backyard-bg');
    if (backyardElement) {
        backyardElement.style.transform = 'translateY(0)';
        backyardElement.style.transition = 'none';
        // Re-enable transition after reset
        setTimeout(() => {
            backyardElement.style.transition = 'transform 0.1s linear';
        }, 50);
    }
    
    // Rocket stays locked in center - never moves from center position
    rocketWrapper.style.transform = 'translate(-50%, -50%)';
    rocketWrapper.style.top = '50%';
    rocketWrapper.style.left = '50%';
    gameState.rocketPosition = 0; // Track height for display, but rocket stays centered
    
    // Clear any existing birds and intervals
    if (gameState.birdSpawnInterval) {
        clearInterval(gameState.birdSpawnInterval);
        gameState.birdSpawnInterval = null;
    }
    gameState.activeBirds = [];
    birdsContainer.innerHTML = '';
    
    // Create initial birds
    createBirds();
    
    // Start game on first tap
    rocketTapButton.addEventListener('click', startGame, { once: true });
    rocketTapButton.addEventListener('touchstart', startGame, { once: true, passive: true });
}

// Create initial random birds in the sky
function createBirds() {
    const gameWrapper = document.querySelector('.rocket-game-wrapper');
    const wrapperRect = gameWrapper ? gameWrapper.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
    const numBirds = Math.floor(Math.random() * 3) + 2; // 2-4 initial birds
    
    for (let i = 0; i < numBirds; i++) {
        spawnBird(wrapperRect);
    }
}

// Spawn a single bird at the top
function spawnBird(wrapperRect) {
    if (!wrapperRect || !birdsContainer) return;
    
    const bird = document.createElement('img');
    bird.className = 'bird';
    bird.src = BIRD_IMAGES[Math.floor(Math.random() * BIRD_IMAGES.length)];
    
    // Spawn at top of sky area (above visible area, relative to container)
    const maxLeft = wrapperRect.width - 60;
    const left = Math.random() * maxLeft;
    const top = -100; // Start above container (negative top)
    
    bird.style.left = `${left}px`;
    bird.style.top = `${top}px`;
    bird.style.position = 'absolute';
    bird.style.animationDelay = `${Math.random() * 3}s`;
    
    // Store bird data for moving
    const birdData = {
        element: bird,
        top: top,
        left: left,
        speed: 0.8 // Speed of downward movement
    };
    
    gameState.activeBirds.push(birdData);
    birdsContainer.appendChild(bird);
}

// Update bird positions (called only on tap)
function updateBirds() {
    if (!gameState.isPlaying) return;
    
    const gameWrapper = document.querySelector('.rocket-game-wrapper');
    if (!gameWrapper) return;
    
    const wrapperRect = gameWrapper.getBoundingClientRect();
    
    // Remove birds that have moved off screen (below container)
    for (let i = gameState.activeBirds.length - 1; i >= 0; i--) {
        const birdData = gameState.activeBirds[i];
        if (birdData.top > wrapperRect.height + 100) {
            birdData.element.remove();
            gameState.activeBirds.splice(i, 1);
        }
    }
}

// Start the game
function startGame(e) {
    if (e) {
        e.preventDefault();
    }
    
    if (gameState.isPlaying) return;
    
    gameState.isPlaying = true;
    gameState.gameStarted = true;
    
    // Change rocket to "on" state permanently
    rocketImage.src = '/static/img/minigame_images/rocket_game_assets/rocket_on.webp';
    
    // Start timer
    startTimer();
    
    // Start tapping handler
    rocketTapButton.addEventListener('click', handleTap);
    rocketTapButton.addEventListener('touchstart', handleTap, { passive: true });
    
    // Start continuous bird spawning
    startBirdSpawning();
}

// Start spawning birds continuously
function startBirdSpawning() {
    const gameWrapper = document.querySelector('.rocket-game-wrapper');
    
    // Spawn a bird every 1-2 seconds
    gameState.birdSpawnInterval = setInterval(() => {
        if (gameState.isPlaying && gameWrapper) {
            const wrapperRect = gameWrapper.getBoundingClientRect();
            spawnBird(wrapperRect);
        }
    }, 1000 + Math.random() * 1000); // Random interval between 1-2 seconds
}

// Handle tap
function handleTap(e) {
    if (e) {
        e.preventDefault();
    }
    
    if (!gameState.isPlaying) return;
    
    gameState.taps++;
    
    // Track height for display purposes, but rocket stays locked in center
    const moveAmount = 15; // Increased from 10 to 15 for faster movement
    gameState.height += moveAmount;
    
    // Rocket stays LOCKED in center - never moves from 50%, 50%
    // Keep transform fixed at center
    rocketWrapper.style.transform = 'translate(-50%, -50%)';
    rocketWrapper.style.top = '50%';
    rocketWrapper.style.left = '50%';
    
    // Move backyard DOWN faster to create faster ascending effect
    // This creates the effect of the backyard scrolling down while rocket stays centered
    gameState.backgroundOffset += moveAmount; // Move background at same speed
    
    // Move birds down with background ONLY when tap is pressed
    gameState.activeBirds.forEach(birdData => {
        birdData.top += moveAmount * 0.8; // Birds move down with background
        birdData.element.style.top = `${birdData.top}px`; // Update position immediately
    });
    
    // Clean up birds that have moved off screen
    updateBirds();
    
    const backyardElement = document.querySelector('.backyard-bg');
    if (backyardElement) {
        // Backyard moves down while rocket stays perfectly centered
        backyardElement.style.transform = `translateY(${gameState.backgroundOffset}px)`;
    }
}

// Start timer
function startTimer() {
    gameState.timerInterval = setInterval(() => {
        gameState.timeLeft--;
        rocketTimer.textContent = gameState.timeLeft;
        
        if (gameState.timeLeft <= 0) {
            endGame();
        }
    }, 1000);
}

// End game
function endGame() {
    gameState.isPlaying = false;
    
    // Clear timer
    if (gameState.timerInterval) {
        clearInterval(gameState.timerInterval);
        gameState.timerInterval = null;
    }
    
    // Stop bird spawning
    if (gameState.birdSpawnInterval) {
        clearInterval(gameState.birdSpawnInterval);
        gameState.birdSpawnInterval = null;
    }
    
    // Remove tap handlers
    rocketTapButton.removeEventListener('click', handleTap);
    rocketTapButton.removeEventListener('touchstart', handleTap);
    
    // Show results
    showResults();
}

// Show results
function showResults() {
    // Calculate height in meters (approximate conversion)
    const heightInMeters = Math.round(gameState.height * 0.1); // 1px ≈ 0.1m
    
    rocketHeightDisplay.textContent = `${heightInMeters}m`;
    rocketTapsDisplay.textContent = `${gameState.taps} taps`;
    
    rocketPopupModal.classList.remove('hidden');
}

// Play again
rocketPlayAgainBtn.addEventListener('click', () => {
    initGame();
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initGame();
});

