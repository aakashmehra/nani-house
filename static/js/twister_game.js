document.addEventListener('DOMContentLoaded', () => {
    const tapToSpeakBtn = document.getElementById('tapToSpeakBtn');
    const tapToSpeakBtnText = document.getElementById('tapToSpeakBtnText');
    const sendBtn = document.getElementById('sendBtn');
    const twistDisplay = document.getElementById('twistDisplay');
    const timerDisplay = document.getElementById('timerDisplay');
    const micImage = document.getElementById('micImage');
    const recordingIndicator = document.getElementById('recordingIndicator');
    const audioPlayback = document.getElementById('audioPlayback');
    const playback = document.getElementById('playback');
    const popupModal = document.getElementById('popupModal');
    const popupChecking = document.getElementById('popupChecking');
    const popupResults = document.getElementById('popupResults');
    const scoreDisplay = document.getElementById('scoreDisplay');
    const twistResult = document.getElementById('twistResult');
    const similarityDisplay = document.getElementById('similarityDisplay');
    const repetitionsDisplay = document.getElementById('repetitionsDisplay');
    const playAgainBtn = document.getElementById('playAgainBtn');
    
    let currentId = null;
    let currentTwist = "";
    let mediaRecorder = null;
    let audioChunks = [];
    let timer = null;
    let stream = null;
    let recordedBlob = null;
    let timeLeft = 30;
    let gameActive = false;
    let isRecording = false;
    
    // Combined function: Get twister + start recording OR stop recording
    async function tapToSpeakHandler() {
        if (!isRecording) {
            // First click: Get twister and start recording
            if (!currentId) {
                // Get twister first
                try {
                    const response = await fetch('/twister_game/task');
                    const data = await response.json();
                    currentId = data.id;
                    currentTwist = data.twist;
                    twistDisplay.textContent = `"${currentTwist}"`;
                    timerDisplay.textContent = '30';
                    timeLeft = 30;
                    recordedBlob = null;
                    audioPlayback.classList.add('hidden');
                } catch (error) {
                    console.error('Error fetching twister:', error);
                    twistDisplay.textContent = 'Error loading twister. Please try again.';
                    return;
                }
            }
            
            // Start recording
            audioChunks = [];
            
            try {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) {
                        audioChunks.push(e.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    playback.src = URL.createObjectURL(recordedBlob);
                    audioPlayback.classList.remove('hidden');
                    
                    // Stop stream
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                        stream = null;
                    }
                    
                    // Update UI
                    isRecording = false;
                    tapToSpeakBtnText.textContent = 'Send';
                    sendBtn.style.display = 'none'; // Hide separate Send button since main button becomes Send
                    sendBtn.disabled = true;
                    micImage.classList.remove('recording');
                    recordingIndicator.classList.add('hidden');
                    gameActive = false;
                    
                    if (timer) {
                        clearInterval(timer);
                        timer = null;
                    }
                    
                    timerDisplay.textContent = '30';
                    timerDisplay.style.animation = 'pulse 1s infinite';
                    timerDisplay.style.color = '#ff4444';
                };
                
                mediaRecorder.start();
                gameActive = true;
                isRecording = true;
                
                // Update UI
                tapToSpeakBtnText.textContent = 'Stop';
                sendBtn.style.display = 'none';
                sendBtn.disabled = true;
                micImage.classList.add('recording');
                recordingIndicator.classList.remove('hidden');
                
                // Start timer
                timeLeft = 30;
                timerDisplay.textContent = timeLeft;
                timerDisplay.style.color = '#ff4444';
                
                timer = setInterval(() => {
                    timeLeft--;
                    timerDisplay.textContent = timeLeft;
                    
                    if (timeLeft <= 3) {
                        timerDisplay.style.color = '#ff0000';
                    }
                    
                    if (timeLeft <= 0) {
                        clearInterval(timer);
                        timer = null;
                        mediaRecorder.stop();
                    }
                }, 1000);
                
            } catch (error) {
                console.error('Error accessing microphone:', error);
                alert('Microphone permission denied or error occurred.');
                isRecording = false;
                tapToSpeakBtnText.textContent = 'Tap to Speak';
            }
        } else {
            // Second click: Stop recording
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
            if (timer) {
                clearInterval(timer);
                timer = null;
            }
        }
    }
    
    // Submit recording (called when Send button is clicked)
    async function submitRecording() {
        if (!recordedBlob || !currentId) {
            alert('No recording available to send.');
            return;
        }
        
        // Show checking popup
        popupModal.classList.remove('hidden');
        popupChecking.classList.remove('hidden');
        popupResults.classList.add('hidden');
        tapToSpeakBtn.disabled = true;
        sendBtn.disabled = true;
        
        try {
            const formData = new FormData();
            formData.append('twist_id', currentId);
            formData.append('file', recordedBlob, 'recording.webm');
            
            const response = await fetch('/twister_game/submit', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            // Hide checking, show results
            popupChecking.classList.add('hidden');
            popupResults.classList.remove('hidden');
            
            // Get score from server response (already calculated)
            const score = result.score || 0;
            const similarity = result.similarity || 0;
            const reps = result.repetitions_detected || 0;
            const verdict = result.verdict || '';
            
            // Display results
            scoreDisplay.textContent = `${score}/10`;
            scoreDisplay.style.color = score >= 7 ? '#4CAF50' : score >= 4 ? '#FF9800' : '#F44336';
            twistResult.textContent = `"${result.target || currentTwist}"`;
            similarityDisplay.textContent = `Similarity: ${(similarity * 100).toFixed(1)}%`;
            repetitionsDisplay.textContent = `Repetitions: ${reps}/3`;
            
            // Re-enable button after showing results
            tapToSpeakBtn.disabled = false;
            
        } catch (error) {
            console.error('Error submitting recording:', error);
            popupChecking.classList.add('hidden');
            popupResults.classList.remove('hidden');
            scoreDisplay.textContent = 'Error';
            scoreDisplay.style.color = '#F44336';
            twistResult.textContent = 'Error submitting recording. Please try again.';
            tapToSpeakBtn.disabled = false;
        }
    }
    
    // Play again
    function playAgain() {
        popupModal.classList.add('hidden');
        timerDisplay.style.color = '#ff4444';
        timerDisplay.style.animation = 'pulse 1s infinite';
        currentId = null;
        currentTwist = "";
        recordedBlob = null;
        isRecording = false;
        tapToSpeakBtnText.textContent = 'Tap to Speak';
        tapToSpeakBtn.disabled = false;
        twistDisplay.textContent = '';
        audioPlayback.classList.add('hidden');
        sendBtn.style.display = 'none';
        sendBtn.disabled = true;
        micImage.classList.remove('recording');
        recordingIndicator.classList.add('hidden');
    }
    
    // Unified button handler - handles Tap to Speak, Stop, and Send
    async function handleMainButtonClick() {
        if (isRecording) {
            // Currently recording - stop it
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
            if (timer) {
                clearInterval(timer);
                timer = null;
            }
        } else if (recordedBlob && currentId) {
            // Have a recording - send it
            await submitRecording();
        } else {
            // Start recording
            await tapToSpeakHandler();
        }
    }
    
    // Event listeners
    tapToSpeakBtn.addEventListener('click', handleMainButtonClick);
    sendBtn.addEventListener('click', submitRecording);
    playAgainBtn.addEventListener('click', playAgain);
});

