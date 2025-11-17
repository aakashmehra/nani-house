/**
 * Zoom and Text Selection Prevention Script
 * Prevents zoom gestures and text selection across all devices
 */

(function() {
    'use strict';

    // Prevent zoom on various gestures
    function preventZoom() {
        // Prevent pinch zoom
        document.addEventListener('gesturestart', function(e) {
            e.preventDefault();
        });

        document.addEventListener('gesturechange', function(e) {
            e.preventDefault();
        });

        document.addEventListener('gestureend', function(e) {
            e.preventDefault();
        });

        // Prevent double-tap zoom (but allow interactions with form elements)
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(e) {
            const now = (new Date()).getTime();
            
            // Don't prevent double-tap on interactive elements
            const target = e.target;
            const isInteractive = target.tagName === 'INPUT' || 
                                 target.tagName === 'BUTTON' || 
                                 target.tagName === 'SELECT' || 
                                 target.tagName === 'TEXTAREA' ||
                                 target.tagName === 'A' ||
                                 target.closest('button') ||
                                 target.closest('input') ||
                                 target.closest('select') ||
                                 target.closest('textarea') ||
                                 target.closest('a') ||
                                 target.closest('label') ||
                                 target.closest('.delivery-option') ||
                                 target.closest('.timing-option') ||
                                 target.closest('.payment-option') ||
                                 target.closest('.time-slot') ||
                                 target.closest('.cutlery-toggle');
            
            if (now - lastTouchEnd <= 300 && !isInteractive) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);

        // Prevent wheel zoom (Ctrl + scroll)
        document.addEventListener('wheel', function(e) {
            if (e.ctrlKey) {
                e.preventDefault();
            }
        }, { passive: false });

        // Prevent keyboard zoom (Ctrl + Plus/Minus/0)
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && (e.key === '+' || e.key === '-' || e.key === '0' || e.key === '=')) {
                e.preventDefault();
            }
        });

        // Prevent context menu (right-click)
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
        });

        // Prevent text selection (but allow on form elements)
        document.addEventListener('selectstart', function(e) {
            const target = e.target;
            const isFormElement = target.tagName === 'INPUT' || 
                                 target.tagName === 'TEXTAREA' ||
                                 target.closest('input') ||
                                 target.closest('textarea');
            
            if (!isFormElement) {
                e.preventDefault();
            }
        });

        // Prevent drag
        document.addEventListener('dragstart', function(e) {
            e.preventDefault();
        });

        // Additional touch event prevention (only for multi-touch gestures)
        document.addEventListener('touchstart', function(e) {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });

        document.addEventListener('touchmove', function(e) {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // Add touch-action CSS to prevent zoom on interactive elements
        const style = document.createElement('style');
        style.textContent = `
            /* Ensure proper touch handling for interactive elements */
            input, button, select, textarea, label, 
            .delivery-option, .timing-option, .payment-option, 
            .time-slot, .cutlery-toggle, .proceed-payment-btn {
                touch-action: manipulation;
                -webkit-touch-callout: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }
            
            /* Allow text selection for input fields */
            input[type="text"], input[type="email"], input[type="tel"], 
            input[type="password"], textarea {
                -webkit-user-select: text;
                -moz-user-select: text;
                -ms-user-select: text;
                user-select: text;
            }
        `;
        document.head.appendChild(style);
    }

    // Allow text selection for specific elements
    function allowTextSelection() {
        const selectableElements = document.querySelectorAll('input, textarea, [contenteditable], .selectable');
        
        selectableElements.forEach(function(element) {
            element.addEventListener('selectstart', function(e) {
                e.stopPropagation();
            });
            
            element.addEventListener('touchstart', function(e) {
                e.stopPropagation();
            }, { passive: true });
        });
    }

    // Initialize when DOM is ready
    function init() {
        // Set viewport meta tag dynamically
        let viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no');
        }

        // Apply CSS styles
        const style = document.createElement('style');
        style.textContent = `
            * {
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                -ms-user-select: none !important;
                user-select: none !important;
                -webkit-touch-callout: none !important;
                -webkit-tap-highlight-color: transparent !important;
                touch-action: manipulation !important;
            }
            
            input, textarea, [contenteditable], .selectable {
                -webkit-user-select: text !important;
                -moz-user-select: text !important;
                -ms-user-select: text !important;
                user-select: text !important;
                -webkit-touch-callout: default !important;
            }
            
            /* Prevent zoom on focus for iOS */
            input, textarea, select {
                font-size: 16px !important;
            }
            
            /* Prevent zoom on double tap for iOS */
            * {
                -webkit-text-size-adjust: 100% !important;
                -ms-text-size-adjust: 100% !important;
                text-size-adjust: 100% !important;
            }
        `;
        document.head.appendChild(style);

        // Apply event listeners
        preventZoom();
        allowTextSelection();
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Re-apply on dynamic content changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                allowTextSelection();
            }
        });
    });

    // Only observe if document.body exists
    if (document.body) {
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

})();
